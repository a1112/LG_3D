use axum::Json;
use axum::body::Body;
use axum::http::{Request, StatusCode, header};
use axum::response::Response;
use futures_util::{SinkExt, StreamExt};
use http_body_util::BodyExt;
use image::{GenericImageView, GrayImage, ImageFormat, Luma, Rgb, RgbImage};
use ndarray::arr2;
use ndarray_npy::{NpzReader, NpzWriter, write_npy};
use rust_api_service::{
    AlarmFlatRollDataRow, AlarmFlatRollRow, AlarmInfoSummaryRow, AlarmLooseCoilRow,
    AlarmTaperShapeRow, ApiState, CapTrueLogItemRow, CapTrueLogRow, CoilAlarmStatusRow,
    CoilCheckRow, CoilDefectRow, CoilRow, CoilStateRow, CoilSummaryRow, DATABASE_URL_ENV,
    DataEllipseRow, DataRuntimeConfig, DeepPointRow, DefectCheckRow, DefectClassDictRow,
    DefectStatisticsRow, DetectionSpeedRow, ImageJoinLogRow, InMemoryCoilRepository, LineDataRow,
    ManualDefectRow, NextCodeDictRow, PlcDataRow, PointDataRow, SecondaryCoilRow,
    ServerDetectionErrorRow, TaperShapePointRow, TestModeConfig, build_app, normalize_database_url,
};
use serde_json::{Value, json};
use std::ffi::{OsStr, OsString};
use std::fs;
use std::fs::File;
use std::io::{Cursor, Read};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tokio::net::TcpListener;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tower::ServiceExt;
use zip::ZipArchive;

static TEMP_DIR_COUNTER: AtomicU64 = AtomicU64::new(0);
static SETTINGS_ENV_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

struct EnvVarGuard {
    name: &'static str,
    previous: Option<OsString>,
}

impl Drop for EnvVarGuard {
    fn drop(&mut self) {
        match &self.previous {
            Some(value) => unsafe {
                std::env::set_var(self.name, value);
            },
            None => unsafe {
                std::env::remove_var(self.name);
            },
        }
    }
}

fn set_env_var_guard<V>(name: &'static str, value: V) -> EnvVarGuard
where
    V: AsRef<OsStr>,
{
    let previous = std::env::var_os(name);
    unsafe {
        std::env::set_var(name, value);
    }
    EnvVarGuard { name, previous }
}

fn remove_env_var_guard(name: &'static str) -> EnvVarGuard {
    let previous = std::env::var_os(name);
    unsafe {
        std::env::remove_var(name);
    }
    EnvVarGuard { name, previous }
}

fn lock_test_env() -> std::sync::MutexGuard<'static, ()> {
    SETTINGS_ENV_LOCK
        .get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

fn sorted_value_keys(value: &Value) -> Vec<&str> {
    let mut keys: Vec<&str> = value
        .as_object()
        .expect("value should be an object")
        .keys()
        .map(String::as_str)
        .collect();
    keys.sort_unstable();
    keys
}

async fn request_json(app: axum::Router, method: &str, uri: &str) -> (StatusCode, Value) {
    let response = app
        .oneshot(
            Request::builder()
                .method(method)
                .uri(uri)
                .body(Body::empty())
                .expect("request"),
        )
        .await
        .expect("response");
    let status = response.status();
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("body")
        .to_bytes();
    let json: Value = serde_json::from_slice(&bytes).expect("json body");
    (status, json)
}

async fn request_response(app: axum::Router, method: &str, uri: &str) -> Response {
    app.oneshot(
        Request::builder()
            .method(method)
            .uri(uri)
            .body(Body::empty())
            .expect("request"),
    )
    .await
    .expect("response")
}

async fn request_json_body(app: axum::Router, method: &str, uri: &str, body: Value) -> Response {
    app.oneshot(
        Request::builder()
            .method(method)
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .expect("request"),
    )
    .await
    .expect("response")
}

async fn response_bytes(response: Response) -> bytes::Bytes {
    response
        .into_body()
        .collect()
        .await
        .expect("body")
        .to_bytes()
}

fn jpeg_sof_component_count(bytes: &[u8]) -> Option<u8> {
    if bytes.len() < 4 || bytes[0] != 0xff || bytes[1] != 0xd8 {
        return None;
    }
    let mut offset = 2;
    while offset + 4 <= bytes.len() {
        if bytes[offset] != 0xff {
            offset += 1;
            continue;
        }
        while offset < bytes.len() && bytes[offset] == 0xff {
            offset += 1;
        }
        if offset >= bytes.len() {
            return None;
        }
        let marker = bytes[offset];
        offset += 1;
        if marker == 0xd8 || marker == 0xd9 || (0xd0..=0xd7).contains(&marker) {
            continue;
        }
        if offset + 2 > bytes.len() {
            return None;
        }
        let length = u16::from_be_bytes([bytes[offset], bytes[offset + 1]]) as usize;
        if length < 2 || offset + length > bytes.len() {
            return None;
        }
        if matches!(
            marker,
            0xc0 | 0xc1
                | 0xc2
                | 0xc3
                | 0xc5
                | 0xc6
                | 0xc7
                | 0xc9
                | 0xca
                | 0xcb
                | 0xcd
                | 0xce
                | 0xcf
        ) {
            return bytes.get(offset + 7).copied();
        }
        offset += length;
    }
    None
}

async fn response_json(response: Response) -> Value {
    let bytes = response_bytes(response).await;
    serde_json::from_slice(&bytes).expect("json body")
}

fn sorted_object_keys(value: &Value) -> Vec<String> {
    let mut keys = value
        .as_object()
        .expect("json object")
        .keys()
        .cloned()
        .collect::<Vec<_>>();
    keys.sort();
    keys
}

fn assert_re_detection_python_status_shape(value: &Value) {
    assert_eq!(
        sorted_object_keys(value),
        vec![
            "done".to_string(),
            "error".to_string(),
            "messages".to_string(),
            "pending".to_string(),
            "progress".to_string(),
            "queue".to_string(),
            "running".to_string(),
            "total".to_string(),
        ]
    );
}

async fn assert_xlsx_export_response(response: Response, filename_prefix: &str) -> bytes::Bytes {
    assert_eq!(response.status(), StatusCode::OK);
    let headers = response.headers().clone();
    assert_eq!(
        headers
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    );
    let disposition = headers
        .get(header::CONTENT_DISPOSITION)
        .and_then(|value| value.to_str().ok())
        .expect("content disposition");
    assert!(disposition.starts_with(&format!("attachment; filename={filename_prefix}")));
    assert!(disposition.ends_with(".xlsx"));
    let bytes = response_bytes(response).await;
    assert!(bytes.len() > 100);
    assert_eq!(&bytes[..2], b"PK");
    bytes
}

fn xlsx_entry_text(bytes: &[u8], entry_name: &str) -> String {
    let cursor = Cursor::new(bytes);
    let mut zip = ZipArchive::new(cursor).expect("xlsx zip archive");
    let mut entry = zip.by_name(entry_name).expect("xlsx entry");
    let mut text = String::new();
    entry.read_to_string(&mut text).expect("xlsx xml text");
    text
}

fn seed_repository_with_defect(
    defect_source: f64,
    defect_data: Option<Value>,
    thickness: f64,
) -> InMemoryCoilRepository {
    InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 42,
            coil_no: "LG-20260627-0042".to_string(),
            create_time: Some("2026-06-27 12:34:56".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(thickness),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 2,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 2,
            s_flat_roll_grad: 2,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("A".to_string()),
            s_next_name: Some("下一工序".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: true,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 3,
            defect_count_l: 1,
            detection_time: Some("2026-06-27 12:35:10".to_string()),
            check_status: 2,
            status_l: 1,
            status_s: 2,
            grade: 2,
            max_defect_name: Some("压痕".to_string()),
            max_defect_level: 2,
            max_defect_surface: Some("S".to_string()),
            has_coil: true,
            has_alarm_info: true,
        }])
        .with_defects(vec![CoilDefectRow {
            id: 7,
            secondary_coil_id: 42,
            surface: "S".to_string(),
            defect_class: 1,
            defect_name: "压痕".to_string(),
            defect_status: 0,
            defect_time: Some("2026-06-27 12:35:12".to_string()),
            defect_x: 11,
            defect_y: 22,
            defect_w: 33,
            defect_h: 44,
            defect_source,
            defect_data,
        }])
        .with_defect_classes(vec![DefectClassDictRow {
            id: 100,
            defect_class: 1,
            defect_name: "压痕".to_string(),
            defect_type: Some("surface".to_string()),
            defect_color: Some("#FF0000".to_string()),
            defect_level: Some(2),
            visible: Some(1),
            defect_desc: Some("表面压痕".to_string()),
        }])
        .with_coil_checks(vec![CoilCheckRow {
            id: 61,
            secondary_coil_id: 42,
            status: 1,
            msg: "初检通过".to_string(),
        }])
}

fn app_with_seed_data() -> axum::Router {
    let repository = seed_repository_with_defect(0.95, Some(json!({"source":"test"})), 2.4);

    build_app(ApiState::new(Arc::new(repository)))
}

fn redetection_coil_summary(id: i64) -> CoilSummaryRow {
    CoilSummaryRow {
        id,
        coil_no: format!("LG-RED-{id:04}"),
        create_time: Some("2026-06-27 12:34:56".to_string()),
        coil_type: Some("Q235".to_string()),
        coil_inside: Some(610.0),
        coil_dia: Some(1320.0),
        thickness: Some(2.4),
        width: Some(1250.0),
        weight: Some(65.0),
        act_width: Some(1248.5),
        next_code: Some("A".to_string()),
        next_info: Some("下一工序".to_string()),
        s_defect_grad: 2,
        s_taper_shape_grad: 2,
        s_loose_coil_grad: 2,
        s_flat_roll_grad: 2,
        s_grad: 2,
        s_has_alarm: true,
        s_next_code: Some("A".to_string()),
        s_next_name: Some("下一工序".to_string()),
        l_defect_grad: 1,
        l_taper_shape_grad: 1,
        l_loose_coil_grad: 1,
        l_flat_roll_grad: 1,
        l_grad: 1,
        l_has_alarm: true,
        l_next_code: None,
        l_next_name: None,
        defect_count_s: 3,
        defect_count_l: 1,
        detection_time: Some("2026-06-27 12:35:10".to_string()),
        check_status: 2,
        status_l: 1,
        status_s: 2,
        grade: 2,
        max_defect_name: Some("压痕".to_string()),
        max_defect_level: 2,
        max_defect_surface: Some("S".to_string()),
        has_coil: true,
        has_alarm_info: true,
    }
}

fn app_with_redetection_seed_data() -> axum::Router {
    let repository = seed_repository_with_defect(0.95, Some(json!({"source":"test"})), 2.4)
        .with_coils(vec![
            redetection_coil_summary(42),
            redetection_coil_summary(43),
            redetection_coil_summary(44),
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_save_to_sql_seed_data() -> axum::Router {
    let repository = seed_repository_with_defect(0.95, Some(json!({"source":"test"})), 2.4)
        .with_secondary_coils(vec![
            SecondaryCoilRow {
                id: 42,
                coil_no: "REAL-SECONDARY-0042".to_string(),
                coil_type: Some("REAL-Q235".to_string()),
                coil_inside: Some(620.0),
                coil_dia: Some(1330.0),
                thickness: Some(2.6),
                width: Some(1260.0),
                weight: Some(66.0),
                act_width: Some(1258.5),
                create_time: Some("2026-06-27 12:34:50".to_string()),
            },
            SecondaryCoilRow {
                id: 77,
                coil_no: "SECONDARY-NO-SUMMARY-0077".to_string(),
                coil_type: Some("REAL-SPHC".to_string()),
                coil_inside: Some(762.0),
                coil_dia: Some(1724.0),
                thickness: Some(2.3),
                width: Some(1059.0),
                weight: Some(55.0),
                act_width: Some(1073.0),
                create_time: Some("2026-06-28 08:01:02".to_string()),
            },
        ])
        .with_defects(vec![
            CoilDefectRow {
                id: 7,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                defect_class: 1,
                defect_name: "压痕".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 12:35:12".to_string()),
                defect_x: 11,
                defect_y: 22,
                defect_w: 33,
                defect_h: 44,
                defect_source: 0.95,
                defect_data: Some(json!({"source":"test"})),
            },
            CoilDefectRow {
                id: 8,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                defect_class: 2,
                defect_name: "孤立缺陷".to_string(),
                defect_status: 1,
                defect_time: Some("2026-06-27 12:36:12".to_string()),
                defect_x: 55,
                defect_y: 66,
                defect_w: 77,
                defect_h: 88,
                defect_source: 0.88,
                defect_data: Some(json!({"orphan":true})),
            },
        ])
        .with_coil_rows(vec![
            CoilRow {
                id: 902,
                secondary_coil_id: 42,
                detection_time: Some("2026-06-27 12:35:10".to_string()),
                defect_count_s: Some(8),
                defect_count_l: Some(9),
                check_status: Some(6),
                status_l: Some(5),
                status_s: Some(4),
                grade: Some(3),
                msg: Some("真实检测备注".to_string()),
            },
            CoilRow {
                id: 903,
                secondary_coil_id: 999,
                detection_time: Some("2026-06-27 12:36:10".to_string()),
                defect_count_s: Some(1),
                defect_count_l: Some(2),
                check_status: Some(3),
                status_l: Some(4),
                status_s: Some(5),
                grade: Some(6),
                msg: Some("孤立检测备注".to_string()),
            },
        ])
        .with_next_code_dict(vec![NextCodeDictRow {
            id: 93,
            code: Some("Z".to_string()),
            info: Some("真实字典工序".to_string()),
        }])
        .with_alarm_infos(vec![
            AlarmInfoSummaryRow {
                id: 82,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                next_code: Some("B".to_string()),
                next_name: Some("真实工序".to_string()),
                taper_shape_msg: Some("真实塔形报警".to_string()),
                loose_coil_msg: Some("真实松卷报警".to_string()),
                flat_roll_msg: Some("真实扁卷报警".to_string()),
                defect_msg: Some("真实缺陷报警".to_string()),
                defect_grad: 4,
                taper_shape_grad: 3,
                loose_coil_grad: 2,
                flat_roll_grad: 5,
                grad: 5,
                create_time: Some("2026-06-27 12:35:12".to_string()),
                data: Some("{\"alarmInfo\":true}".to_string()),
            },
            AlarmInfoSummaryRow {
                id: 83,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                next_code: Some("C".to_string()),
                next_name: Some("孤立工序".to_string()),
                taper_shape_msg: Some("孤立塔形报警".to_string()),
                loose_coil_msg: Some("孤立松卷报警".to_string()),
                flat_roll_msg: Some("孤立扁卷报警".to_string()),
                defect_msg: Some("孤立缺陷报警".to_string()),
                defect_grad: 1,
                taper_shape_grad: 2,
                loose_coil_grad: 3,
                flat_roll_grad: 4,
                grad: 4,
                create_time: Some("2026-06-27 12:36:12".to_string()),
                data: Some("{\"orphanAlarm\":true}".to_string()),
            },
        ])
        .with_coil_states(vec![
            coil_state_json_row(101, 42, "S", json!({"history": 1})),
            coil_state_json_row(102, 42, "S", json!({"history": 2})),
            coil_state_json_row(103, 42, "S", json!({"history": 3})),
        ])
        .with_plc_data(vec![
            PlcDataRow {
                id: 201,
                secondary_coil_id: 42,
                location_s: Some(11.25),
                location_l: Some(21.25),
                location_laser: Some(31.25),
                start_time: Some("2026-06-27 12:35:13".to_string()),
                pcl_data: Some("{\"frame\":1}".to_string()),
            },
            PlcDataRow {
                id: 202,
                secondary_coil_id: 42,
                location_s: Some(12.25),
                location_l: Some(22.25),
                location_laser: Some(32.25),
                start_time: Some("2026-06-27 12:35:14".to_string()),
                pcl_data: Some("{\"frame\":2}".to_string()),
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_detail_defect_serialization_data() -> axum::Router {
    let repository = seed_repository_with_defect(0.9138365983963013, None, 3.9000000953674316);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_2d_xlsx_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new().with_coils(vec![CoilSummaryRow {
        id: 43,
        coil_no: "LG-20260627-0043".to_string(),
        create_time: Some("2026-06-27 12:44:56".to_string()),
        coil_type: Some("Q355".to_string()),
        coil_inside: Some(610.0),
        coil_dia: Some(1325.0),
        thickness: Some(2.6),
        width: Some(1260.0),
        weight: Some(66.0),
        act_width: Some(1258.5),
        next_code: Some("B".to_string()),
        next_info: Some("二次检测".to_string()),
        s_defect_grad: 1,
        s_taper_shape_grad: 1,
        s_loose_coil_grad: 1,
        s_flat_roll_grad: 1,
        s_grad: 1,
        s_has_alarm: false,
        s_next_code: None,
        s_next_name: None,
        l_defect_grad: 2,
        l_taper_shape_grad: 1,
        l_loose_coil_grad: 1,
        l_flat_roll_grad: 1,
        l_grad: 2,
        l_has_alarm: true,
        l_next_code: Some("B".to_string()),
        l_next_name: Some("二次检测".to_string()),
        defect_count_s: 0,
        defect_count_l: 2,
        detection_time: Some("2026-06-27 12:45:10".to_string()),
        check_status: 1,
        status_l: 2,
        status_s: 0,
        grade: 2,
        max_defect_name: Some("2D边裂".to_string()),
        max_defect_level: 2,
        max_defect_surface: Some("L".to_string()),
        has_coil: true,
        has_alarm_info: true,
    }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_defect_category_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 44,
            coil_no: "LG-20260627-0044".to_string(),
            create_time: Some("2026-06-27 12:54:56".to_string()),
            coil_type: Some("Q355".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1325.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            next_code: Some("B".to_string()),
            next_info: Some("二次检测".to_string()),
            s_defect_grad: 2,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("B".to_string()),
            s_next_name: Some("二次检测".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 1,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 12:55:10".to_string()),
            check_status: 1,
            status_l: 0,
            status_s: 2,
            grade: 2,
            max_defect_name: Some("折叠".to_string()),
            max_defect_level: 2,
            max_defect_surface: Some("S".to_string()),
            has_coil: true,
            has_alarm_info: true,
        }])
        .with_defects(vec![CoilDefectRow {
            id: 44,
            secondary_coil_id: 44,
            surface: "S".to_string(),
            defect_class: 4,
            defect_name: "折叠".to_string(),
            defect_status: 0,
            defect_time: Some("2026-06-27 12:55:12".to_string()),
            defect_x: 101,
            defect_y: 202,
            defect_w: 33,
            defect_h: 44,
            defect_source: 0.91,
            defect_data: None,
        }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_actual_defect_row_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 46,
            coil_no: "LG-20260627-0046".to_string(),
            create_time: Some("2026-06-27 13:14:56".to_string()),
            coil_type: Some("Q355".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1325.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            next_code: Some("B".to_string()),
            next_info: Some("二次检测".to_string()),
            s_defect_grad: 0,
            s_taper_shape_grad: 0,
            s_loose_coil_grad: 0,
            s_flat_roll_grad: 0,
            s_grad: 0,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 0,
            l_taper_shape_grad: 0,
            l_loose_coil_grad: 0,
            l_flat_roll_grad: 0,
            l_grad: 0,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 1,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 13:15:10".to_string()),
            check_status: 1,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_defects(vec![CoilDefectRow {
            id: 46,
            secondary_coil_id: 46,
            surface: "S".to_string(),
            defect_class: 8,
            defect_name: "真实缺陷行".to_string(),
            defect_status: 0,
            defect_time: Some("2026-06-27 13:15:12".to_string()),
            defect_x: 11,
            defect_y: 22,
            defect_w: 33,
            defect_h: 44,
            defect_source: 0.88,
            defect_data: None,
        }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_visible_and_hidden_defects_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 47,
            coil_no: "LG-20260627-0047".to_string(),
            create_time: Some("2026-06-27 13:24:56".to_string()),
            coil_type: Some("Q355".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1325.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            next_code: Some("B".to_string()),
            next_info: Some("二次检测".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 0,
            s_loose_coil_grad: 0,
            s_flat_roll_grad: 0,
            s_grad: 1,
            s_has_alarm: true,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 0,
            l_loose_coil_grad: 0,
            l_flat_roll_grad: 0,
            l_grad: 1,
            l_has_alarm: true,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 1,
            defect_count_l: 1,
            detection_time: Some("2026-06-27 13:25:10".to_string()),
            check_status: 1,
            status_l: 0,
            status_s: 0,
            grade: 1,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_defects(vec![
            CoilDefectRow {
                id: 47,
                secondary_coil_id: 47,
                surface: "S".to_string(),
                defect_class: 1,
                defect_name: "显示缺陷".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 13:25:12".to_string()),
                defect_x: 11,
                defect_y: 22,
                defect_w: 33,
                defect_h: 44,
                defect_source: 0.88,
                defect_data: None,
            },
            CoilDefectRow {
                id: 48,
                secondary_coil_id: 47,
                surface: "L".to_string(),
                defect_class: 2,
                defect_name: "屏蔽缺陷".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 13:25:13".to_string()),
                defect_x: 55,
                defect_y: 66,
                defect_w: 77,
                defect_h: 88,
                defect_source: 0.77,
                defect_data: None,
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_name_mapped_defect_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 48,
            coil_no: "LG-20260627-0048".to_string(),
            create_time: Some("2026-06-27 13:34:56".to_string()),
            coil_type: Some("Q355".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1325.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            next_code: Some("B".to_string()),
            next_info: Some("二次检测".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 0,
            s_loose_coil_grad: 0,
            s_flat_roll_grad: 0,
            s_grad: 1,
            s_has_alarm: true,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 0,
            l_taper_shape_grad: 0,
            l_loose_coil_grad: 0,
            l_flat_roll_grad: 0,
            l_grad: 0,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 1,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 13:35:10".to_string()),
            check_status: 1,
            status_l: 0,
            status_s: 0,
            grade: 1,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_defects(vec![CoilDefectRow {
            id: 49,
            secondary_coil_id: 48,
            surface: "S".to_string(),
            defect_class: 3,
            defect_name: "原始别名缺陷".to_string(),
            defect_status: 0,
            defect_time: Some("2026-06-27 13:35:12".to_string()),
            defect_x: 12,
            defect_y: 23,
            defect_w: 34,
            defect_h: 45,
            defect_source: 0.66,
            defect_data: None,
        }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_plc_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 45,
            coil_no: "LG-20260627-0045".to_string(),
            create_time: Some("2026-06-27 13:04:56".to_string()),
            coil_type: Some("Q355".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1325.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            next_code: Some("B".to_string()),
            next_info: Some("二次检测".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 13:05:10".to_string()),
            check_status: 1,
            status_l: 0,
            status_s: 0,
            grade: 1,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_plc_data(vec![PlcDataRow {
            id: 71,
            secondary_coil_id: 45,
            location_s: Some(9.75),
            location_l: Some(8.5),
            location_laser: Some(7.25),
            start_time: Some("2026-06-27 13:05:12".to_string()),
            pcl_data: None,
        }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_secondary_only_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 77,
            coil_no: "SECONDARY-ONLY-0077".to_string(),
            create_time: Some("2026-06-28 08:01:02".to_string()),
            coil_type: Some("SPHC".to_string()),
            coil_inside: Some(762.0),
            coil_dia: Some(1724.0),
            thickness: Some(2.3),
            width: Some(1059.0),
            weight: Some(55.0),
            act_width: Some(1073.0),
            next_code: None,
            next_info: None,
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 0,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 0,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: None,
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: false,
            has_alarm_info: false,
        }])
        .with_defects(vec![
            CoilDefectRow {
                id: 701,
                secondary_coil_id: 77,
                surface: "S".to_string(),
                defect_class: 6,
                defect_name: "数据脏污".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-28 08:02:03".to_string()),
                defect_x: 10,
                defect_y: 20,
                defect_w: 30,
                defect_h: 40,
                defect_source: 0.91,
                defect_data: None,
            },
            CoilDefectRow {
                id: 702,
                secondary_coil_id: 77,
                surface: "L".to_string(),
                defect_class: 9,
                defect_name: "隐藏背景".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-28 08:02:04".to_string()),
                defect_x: 11,
                defect_y: 21,
                defect_w: 31,
                defect_h: 41,
                defect_source: 0.92,
                defect_data: None,
            },
        ])
        .with_defect_classes(vec![
            DefectClassDictRow {
                id: 1,
                defect_class: 6,
                defect_name: "数据脏污".to_string(),
                defect_type: Some("surface".to_string()),
                defect_color: Some("#00FF00".to_string()),
                defect_level: Some(3),
                visible: Some(1),
                defect_desc: None,
            },
            DefectClassDictRow {
                id: 2,
                defect_class: 9,
                defect_name: "隐藏背景".to_string(),
                defect_type: Some("surface".to_string()),
                defect_color: Some("#000000".to_string()),
                defect_level: Some(5),
                visible: Some(0),
                defect_desc: None,
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_defect_query_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_defects(vec![
            CoilDefectRow {
                id: 9,
                secondary_coil_id: 41,
                surface: "L".to_string(),
                defect_class: 2,
                defect_name: "划伤".to_string(),
                defect_status: 1,
                defect_time: Some("2026-06-27 12:30:00".to_string()),
                defect_x: 101,
                defect_y: 102,
                defect_w: 103,
                defect_h: 104,
                defect_source: 0.77,
                defect_data: Some(json!({"range":"first"})),
            },
            CoilDefectRow {
                id: 8,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                defect_class: 3,
                defect_name: "氧化".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 12:36:00".to_string()),
                defect_x: 51,
                defect_y: 52,
                defect_w: 53,
                defect_h: 54,
                defect_source: 0.61,
                defect_data: None,
            },
            CoilDefectRow {
                id: 7,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                defect_class: 1,
                defect_name: "压痕".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 12:35:12".to_string()),
                defect_x: 11,
                defect_y: 22,
                defect_w: 33,
                defect_h: 44,
                defect_source: 0.95,
                defect_data: Some(json!({"source":"auto"})),
            },
            CoilDefectRow {
                id: 10,
                secondary_coil_id: 43,
                surface: "S".to_string(),
                defect_class: 4,
                defect_name: "范围外".to_string(),
                defect_status: 0,
                defect_time: Some("2026-06-27 12:37:00".to_string()),
                defect_x: 1,
                defect_y: 2,
                defect_w: 3,
                defect_h: 4,
                defect_source: 0.42,
                defect_data: None,
            },
        ])
        .with_manual_defects(vec![
            ManualDefectRow {
                id: 51,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                defect_class: 6,
                defect_name: "手动压痕".to_string(),
                defect_status: 1,
                defect_time: Some("2026-06-27 12:40:00".to_string()),
                defect_x: 201,
                defect_y: 202,
                defect_w: 203,
                defect_h: 204,
                defect_source: 0.0,
                defect_data: Some(json!({"manual":true})),
                remark: Some("人工复核".to_string()),
                annotator: Some("系统用户".to_string()),
            },
            ManualDefectRow {
                id: 52,
                secondary_coil_id: 42,
                surface: "L".to_string(),
                defect_class: 7,
                defect_name: "背面标注".to_string(),
                defect_status: 1,
                defect_time: Some("2026-06-27 12:41:00".to_string()),
                defect_x: 301,
                defect_y: 302,
                defect_w: 303,
                defect_h: 304,
                defect_source: 0.0,
                defect_data: None,
                remark: None,
                annotator: None,
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn unique_temp_dir() -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time")
        .as_nanos();
    let counter = TEMP_DIR_COUNTER.fetch_add(1, Ordering::Relaxed);
    std::env::temp_dir().join(format!("lg3d_rust_api_service_test_{suffix}_{counter}"))
}

fn test_state(testdata_dir: PathBuf) -> ApiState {
    ApiState::new(Arc::new(InMemoryCoilRepository::new())).with_test_mode(TestModeConfig {
        enabled: true,
        coil_id: 193113,
        project_root: testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("project root")
            .to_path_buf(),
        data_dir: testdata_dir,
    })
}

fn app_with_data_config(config: DataRuntimeConfig) -> axum::Router {
    build_app(ApiState::new(Arc::new(InMemoryCoilRepository::new())).with_data_config(config))
}

fn coil_state_json_row(
    id: i64,
    secondary_coil_id: i64,
    surface: &str,
    json_data: Value,
) -> CoilStateRow {
    CoilStateRow {
        id,
        secondary_coil_id,
        surface: surface.to_string(),
        start_time: Some("2026-06-27 12:35:11".to_string()),
        scan3d_coordinate_scale_x: None,
        scan3d_coordinate_scale_y: None,
        scan3d_coordinate_scale_z: None,
        rotate: None,
        x_rotate: None,
        median_3d: None,
        median_3d_mm: None,
        color_from_value_mm: None,
        color_to_value_mm: None,
        start: None,
        step: None,
        upper_limit: None,
        lower_limit: None,
        lower_area: None,
        upper_area: None,
        lower_area_percent: None,
        upper_area_percent: None,
        mask_area: None,
        width: None,
        height: None,
        json_data: Some(json_data.to_string()),
    }
}

fn app_with_defect_query_rows_and_data_config(config: DataRuntimeConfig) -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_defects(vec![CoilDefectRow {
            id: 7,
            secondary_coil_id: 42,
            surface: "S".to_string(),
            defect_class: 1,
            defect_name: "压痕".to_string(),
            defect_status: 0,
            defect_time: Some("2026-06-27 12:35:12".to_string()),
            defect_x: 11,
            defect_y: 22,
            defect_w: 33,
            defect_h: 44,
            defect_source: 0.95,
            defect_data: Some(json!({"source":"auto"})),
        }])
        .with_manual_defects(vec![ManualDefectRow {
            id: 51,
            secondary_coil_id: 42,
            surface: "S".to_string(),
            defect_class: 6,
            defect_name: "手动压痕".to_string(),
            defect_status: 1,
            defect_time: Some("2026-06-27 12:40:00".to_string()),
            defect_x: 201,
            defect_y: 202,
            defect_w: 203,
            defect_h: 204,
            defect_source: 0.0,
            defect_data: Some(json!({"manual":true})),
            remark: Some("人工复核".to_string()),
            annotator: Some("系统用户".to_string()),
        }]);

    build_app(ApiState::new(Arc::new(repository)).with_data_config(config))
}

fn app_with_process_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 42,
            coil_no: "LG-20260627-0042".to_string(),
            create_time: Some("2026-06-27 12:34:56".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 2,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 2,
            s_flat_roll_grad: 2,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("A".to_string()),
            s_next_name: Some("下一工序".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: true,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 3,
            defect_count_l: 1,
            detection_time: Some("2026-06-27 12:35:10".to_string()),
            check_status: 2,
            status_l: 1,
            status_s: 2,
            grade: 2,
            max_defect_name: Some("压痕".to_string()),
            max_defect_level: 2,
            max_defect_surface: Some("S".to_string()),
            has_coil: true,
            has_alarm_info: true,
        }])
        .with_alarm_infos(vec![AlarmInfoSummaryRow {
            id: 82,
            secondary_coil_id: 42,
            surface: "S".to_string(),
            next_code: Some("B".to_string()),
            next_name: Some("真实工序".to_string()),
            taper_shape_msg: Some("真实塔形报警".to_string()),
            loose_coil_msg: Some("真实松卷报警".to_string()),
            flat_roll_msg: Some("真实扁卷报警".to_string()),
            defect_msg: Some("真实缺陷报警".to_string()),
            defect_grad: 4,
            taper_shape_grad: 3,
            loose_coil_grad: 2,
            flat_roll_grad: 5,
            grad: 5,
            create_time: Some("2026-06-27 12:35:12".to_string()),
            data: Some("{\"alarmInfo\":true}".to_string()),
        }])
        .with_coil_states(vec![
            CoilStateRow {
                id: 9,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                start_time: Some("2026-06-27 12:35:11".to_string()),
                scan3d_coordinate_scale_x: Some(0.3369000256061554),
                scan3d_coordinate_scale_y: Some(1.0),
                scan3d_coordinate_scale_z: Some(0.0162),
                rotate: Some(90),
                x_rotate: Some(17),
                median_3d: Some(57745.0),
                median_3d_mm: Some(936.9),
                color_from_value_mm: Some(-30.0),
                color_to_value_mm: Some(30.0),
                start: Some(46917.71484375),
                step: Some(2483.0),
                upper_limit: Some(6205.0),
                lower_limit: Some(-3102.0),
                lower_area: Some(178691),
                upper_area: Some(925),
                lower_area_percent: Some(0.00699999975040555),
                upper_area_percent: Some(0.0003),
                mask_area: Some(25_249_781),
                width: Some(6995),
                height: Some(5180),
                json_data: Some("{'coilId':'42'}".to_string()),
            },
            CoilStateRow {
                id: 8,
                secondary_coil_id: 42,
                surface: "L".to_string(),
                start_time: Some("2026-06-27 12:35:10".to_string()),
                scan3d_coordinate_scale_x: Some(0.3369),
                scan3d_coordinate_scale_y: Some(1.0),
                scan3d_coordinate_scale_z: Some(0.0162),
                rotate: Some(-90),
                x_rotate: Some(10),
                median_3d: Some(55453.0),
                median_3d_mm: Some(899.5),
                color_from_value_mm: Some(-30.0),
                color_to_value_mm: Some(30.0),
                start: Some(54211.0),
                step: Some(2483.0),
                upper_limit: Some(6205.0),
                lower_limit: Some(-3102.0),
                lower_area: Some(208955),
                upper_area: Some(4219),
                lower_area_percent: Some(0.008),
                upper_area_percent: Some(0.0004),
                mask_area: Some(25_715_871),
                width: Some(7024),
                height: Some(5336),
                json_data: Some("{'coilId':'42','surface':'L'}".to_string()),
            },
        ])
        .with_plc_data(vec![PlcDataRow {
            id: 12,
            secondary_coil_id: 42,
            location_s: Some(123.4000015258789),
            location_l: Some(456.7),
            location_laser: Some(89.1),
            start_time: Some("2026-06-27 12:36:00".to_string()),
            pcl_data: Some("{\"source\":\"unit-test\"}".to_string()),
        }])
        .with_manual_defects(vec![
            ManualDefectRow {
                id: 51,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                defect_class: 6,
                defect_name: "手动压痕".to_string(),
                defect_status: 1,
                defect_time: Some("2026-06-27 12:40:00".to_string()),
                defect_x: 201,
                defect_y: 202,
                defect_w: 203,
                defect_h: 204,
                defect_source: 0.0,
                defect_data: Some(json!({"manual":true})),
                remark: Some("人工复核".to_string()),
                annotator: Some("系统用户".to_string()),
            },
            ManualDefectRow {
                id: 52,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                defect_class: 7,
                defect_name: "孤立手动缺陷".to_string(),
                defect_status: 2,
                defect_time: Some("2026-06-27 12:40:30".to_string()),
                defect_x: 301,
                defect_y: 302,
                defect_w: 303,
                defect_h: 304,
                defect_source: 0.0,
                defect_data: Some(json!({"orphanManual":true})),
                remark: Some("孤立复核".to_string()),
                annotator: Some("测试用户".to_string()),
            },
        ])
        .with_coil_checks(vec![CoilCheckRow {
            id: 62,
            secondary_coil_id: 999,
            status: 4,
            msg: "孤立检查记录".to_string(),
        }])
        .with_point_data(vec![
            PointDataRow {
                id: 2,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                point_type: Some("inner".to_string()),
                x: Some(101.5),
                y: Some(202.25),
                z: Some(303.0),
                z_mm: Some(16.5),
                data: Some("{\"label\":\"A\"}".to_string()),
                crate_time: Some("2026-06-27 12:40:00".to_string()),
            },
            PointDataRow {
                id: 5,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                point_type: Some("orphan-point".to_string()),
                x: Some(9.5),
                y: Some(8.25),
                z: Some(7.0),
                z_mm: Some(99.5),
                data: Some("{\"orphanPoint\":true}".to_string()),
                crate_time: Some("2026-06-27 12:40:30".to_string()),
            },
        ])
        .with_line_data(vec![
            LineDataRow {
                id: 4,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                line_type: Some("diameter".to_string()),
                center_x: Some(100.0),
                center_y: Some(200.0),
                width: Some(300.0),
                height: Some(20.0),
                rotation_angle: Some(1.5),
                x1: Some(10.0),
                y1: Some(20.0),
                x2: Some(110.0),
                y2: Some(120.0),
                data: Some("[1,2,3]".to_string()),
                inner_min_value: Some(12.0),
                inner_min_value_mm: Some(1.2),
                inner_max_value: Some(22.0),
                inner_max_value_mm: Some(2.2),
                outer_min_value: Some(32.0),
                outer_min_value_mm: Some(3.2),
                outer_max_value: Some(42.0),
                outer_max_value_mm: Some(4.2),
                crate_time: Some("2026-06-27 12:41:00".to_string()),
            },
            LineDataRow {
                id: 6,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                line_type: Some("orphan-line".to_string()),
                center_x: Some(10.0),
                center_y: Some(20.0),
                width: Some(30.0),
                height: Some(40.0),
                rotation_angle: Some(2.5),
                x1: Some(1.0),
                y1: Some(2.0),
                x2: Some(3.0),
                y2: Some(4.0),
                data: Some("{\"orphanLine\":true}".to_string()),
                inner_min_value: Some(5.0),
                inner_min_value_mm: Some(0.5),
                inner_max_value: Some(6.0),
                inner_max_value_mm: Some(0.6),
                outer_min_value: Some(7.0),
                outer_min_value_mm: Some(0.7),
                outer_max_value: Some(8.0),
                outer_max_value_mm: Some(0.8),
                crate_time: Some("2026-06-27 12:41:30".to_string()),
            },
        ])
        .with_server_detection_errors(vec![
            ServerDetectionErrorRow {
                id: 71,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                error_type: Some("ImageMosaic".to_string()),
                time: Some("2026-06-27 12:42:00".to_string()),
                msg: Some("拼接失败".to_string()),
            },
            ServerDetectionErrorRow {
                id: 171,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                error_type: Some("OrphanPipeline".to_string()),
                time: Some("2026-06-27 12:42:30".to_string()),
                msg: Some("孤立服务错误".to_string()),
            },
        ])
        .with_defect_checks(vec![
            DefectCheckRow {
                id: 72,
                secondary_coil_id: 42,
                defect_id: Some(7),
                key: Some("S".to_string()),
                status: Some(2),
                old_defect_id: Some(10),
                old_defect_name: Some("压痕".to_string()),
                new_defect_id: Some(11),
                new_defect_name: Some("划伤".to_string()),
                add_time: Some("2026-06-27 12:43:00".to_string()),
                msg: Some("人工复核改判".to_string()),
            },
            DefectCheckRow {
                id: 172,
                secondary_coil_id: 999,
                defect_id: Some(8),
                key: Some("L".to_string()),
                status: Some(5),
                old_defect_id: Some(20),
                old_defect_name: Some("孤立旧缺陷".to_string()),
                new_defect_id: Some(21),
                new_defect_name: Some("孤立新缺陷".to_string()),
                add_time: Some("2026-06-27 12:43:30".to_string()),
                msg: Some("孤立缺陷复核".to_string()),
            },
        ])
        .with_data_ellipses(vec![
            DataEllipseRow {
                id: 73,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                ellipse_type: Some("inner".to_string()),
                center_x: Some(320.5),
                center_y: Some(240.25),
                width: Some(120.0),
                height: Some(80.0),
                rotation_angle: Some(1.25),
                level: Some(2),
                err_msg: Some("椭圆偏移".to_string()),
                crate_time: Some("2026-06-27 12:44:00".to_string()),
                data: Some("{\"ellipse\":true}".to_string()),
            },
            DataEllipseRow {
                id: 173,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                ellipse_type: Some("orphan-ellipse".to_string()),
                center_x: Some(420.5),
                center_y: Some(340.25),
                width: Some(220.0),
                height: Some(180.0),
                rotation_angle: Some(2.25),
                level: Some(4),
                err_msg: Some("孤立椭圆偏移".to_string()),
                crate_time: Some("2026-06-27 12:44:30".to_string()),
                data: Some("{\"orphanEllipse\":true}".to_string()),
            },
        ])
        .with_deep_points(vec![
            DeepPointRow {
                id: 74,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                x: Some(101),
                y: Some(202),
                x_mm: Some(10.1),
                y_mm: Some(20.2),
                value: Some(-3.5),
                value_int: Some(-35),
                by_user: Some(1),
                draw: Some(1),
                level: Some(3),
                err_msg: Some("深度异常".to_string()),
                crate_time: Some("2026-06-27 12:45:00".to_string()),
                data: Some("{\"deep\":true}".to_string()),
            },
            DeepPointRow {
                id: 174,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                x: Some(301),
                y: Some(402),
                x_mm: Some(30.1),
                y_mm: Some(40.2),
                value: Some(-9.5),
                value_int: Some(-95),
                by_user: Some(0),
                draw: Some(1),
                level: Some(5),
                err_msg: Some("孤立深度异常".to_string()),
                crate_time: Some("2026-06-27 12:45:30".to_string()),
                data: Some("{\"orphanDeep\":true}".to_string()),
            },
        ])
        .with_detection_speeds(vec![
            DetectionSpeedRow {
                id: 75,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                start_time: Some("2026-06-27 12:45:01".to_string()),
                end_time: Some("2026-06-27 12:45:09".to_string()),
                all_time: Some(8.25),
            },
            DetectionSpeedRow {
                id: 175,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                start_time: Some("2026-06-27 12:45:31".to_string()),
                end_time: Some("2026-06-27 12:45:49".to_string()),
                all_time: Some(18.75),
            },
        ])
        .with_coil_alarm_statuses(vec![
            CoilAlarmStatusRow {
                id: 76,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                level: Some(3),
                alarm_status: Some(1),
                alarm_flat_roll: Some(1),
                alarm_taper: Some(0),
                alarm_folding: Some(1),
                alarm_defect: Some(1),
                crate_time: Some("2026-06-27 12:46:00".to_string()),
                data: Some("{\"alarm\":true}".to_string()),
            },
            CoilAlarmStatusRow {
                id: 176,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                level: Some(5),
                alarm_status: Some(1),
                alarm_flat_roll: Some(0),
                alarm_taper: Some(1),
                alarm_folding: Some(0),
                alarm_defect: Some(1),
                crate_time: Some("2026-06-27 12:46:30".to_string()),
                data: Some("{\"orphanAlarmStatus\":true}".to_string()),
            },
        ])
        .with_image_join_logs(vec![
            ImageJoinLogRow {
                id: 77,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                image_count: Some(3),
                rotate: Some(1.5),
                flip_h: Some(1),
                flip_v: Some(0),
                clip1_l: Some(10),
                clip1_r: Some(20),
                clip2_l: Some(30),
                clip2_r: Some(40),
                clip3_l: Some(50),
                clip3_r: Some(60),
                data: Some("{\"join\":true}".to_string()),
                create_time: Some("2026-06-27 12:47:00".to_string()),
            },
            ImageJoinLogRow {
                id: 177,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                image_count: Some(5),
                rotate: Some(2.5),
                flip_h: Some(0),
                flip_v: Some(1),
                clip1_l: Some(11),
                clip1_r: Some(21),
                clip2_l: Some(31),
                clip2_r: Some(41),
                clip3_l: Some(51),
                clip3_r: Some(61),
                data: Some("{\"orphanJoin\":true}".to_string()),
                create_time: Some("2026-06-27 12:47:30".to_string()),
            },
        ])
        .with_defect_statistics(vec![
            DefectStatisticsRow {
                id: 78,
                secondary_coil_id: 42,
                surface: Some("L".to_string()),
            },
            DefectStatisticsRow {
                id: 178,
                secondary_coil_id: 999,
                surface: Some("S".to_string()),
            },
        ])
        .with_alarm_flat_roll_data(vec![
            AlarmFlatRollDataRow {
                id: 79,
                secondary_coil_id: 42,
                surface: Some("S".to_string()),
                level: Some(4),
                err_msg: Some("扁卷明细报警".to_string()),
                crate_time: Some("2026-06-27 12:48:00".to_string()),
                data: Some("{\"flatRollData\":true}".to_string()),
            },
            AlarmFlatRollDataRow {
                id: 179,
                secondary_coil_id: 999,
                surface: Some("L".to_string()),
                level: Some(5),
                err_msg: Some("孤立扁卷明细报警".to_string()),
                crate_time: Some("2026-06-27 12:48:30".to_string()),
                data: Some("{\"orphanFlatRollData\":true}".to_string()),
            },
        ])
        .with_cap_true_logs(vec![
            CapTrueLogRow {
                id: 80,
                secondary_coil_id: 42,
                camera_id: Some(3),
                camera_name: Some("S端深度".to_string()),
                cap_true_start_time: Some("2026-06-27 12:49:00".to_string()),
                cap_true_end_time: Some("2026-06-27 12:49:05".to_string()),
            },
            CapTrueLogRow {
                id: 180,
                secondary_coil_id: 999,
                camera_id: Some(4),
                camera_name: Some("孤立相机".to_string()),
                cap_true_start_time: Some("2026-06-27 12:49:30".to_string()),
                cap_true_end_time: Some("2026-06-27 12:49:35".to_string()),
            },
        ])
        .with_cap_true_log_items(vec![
            CapTrueLogItemRow {
                id: 81,
                secondary_coil_id: 42,
                camera_id: Some(3),
                camera_name: Some("S端深度".to_string()),
                cap_true_time: Some("2026-06-27 12:49:01".to_string()),
                image_index: Some(7),
            },
            CapTrueLogItemRow {
                id: 181,
                secondary_coil_id: 999,
                camera_id: Some(4),
                camera_name: Some("孤立相机".to_string()),
                cap_true_time: Some("2026-06-27 12:49:31".to_string()),
                image_index: Some(17),
            },
        ]);
    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_point_line_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_point_data(vec![
            PointDataRow {
                id: 3,
                secondary_coil_id: 42,
                surface: "L".to_string(),
                point_type: Some("outer".to_string()),
                x: Some(9.0),
                y: Some(10.0),
                z: Some(11.0),
                z_mm: Some(12.0),
                data: Some("{\"ignored\":\"surface\"}".to_string()),
                crate_time: Some("2026-06-27 12:42:00".to_string()),
            },
            PointDataRow {
                id: 2,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                point_type: Some("inner".to_string()),
                x: Some(101.5),
                y: Some(202.25),
                z: Some(303.0),
                z_mm: Some(16.5),
                data: Some("{\"label\":\"A\"}".to_string()),
                crate_time: Some("2026-06-27 12:40:00".to_string()),
            },
            PointDataRow {
                id: 1,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                point_type: Some("outer".to_string()),
                x: Some(11.0),
                y: Some(22.0),
                z: Some(33.0),
                z_mm: Some(-6.6994476318359375),
                data: None,
                crate_time: Some("2026-06-27 12:39:00".to_string()),
            },
        ])
        .with_line_data(vec![
            LineDataRow {
                id: 5,
                secondary_coil_id: 42,
                surface: "L".to_string(),
                line_type: Some("skip".to_string()),
                center_x: Some(1.0),
                center_y: Some(2.0),
                width: Some(3.0),
                height: Some(4.0),
                rotation_angle: Some(5.0),
                x1: Some(6.0),
                y1: Some(7.0),
                x2: Some(8.0),
                y2: Some(9.0),
                data: None,
                inner_min_value: None,
                inner_min_value_mm: None,
                inner_max_value: None,
                inner_max_value_mm: None,
                outer_min_value: None,
                outer_min_value_mm: None,
                outer_max_value: None,
                outer_max_value_mm: None,
                crate_time: None,
            },
            LineDataRow {
                id: 4,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                line_type: Some("diameter".to_string()),
                center_x: Some(100.0),
                center_y: Some(200.0),
                width: Some(300.0),
                height: Some(20.0),
                rotation_angle: Some(1.5),
                x1: Some(10.0),
                y1: Some(20.0),
                x2: Some(110.0),
                y2: Some(120.0),
                data: Some("[1,2,3]".to_string()),
                inner_min_value: Some(12.0),
                inner_min_value_mm: Some(1.2),
                inner_max_value: Some(22.0),
                inner_max_value_mm: Some(2.2),
                outer_min_value: Some(32.0),
                outer_min_value_mm: Some(3.2),
                outer_max_value: Some(42.0),
                outer_max_value_mm: Some(1.4066627025604248),
                crate_time: Some("2026-06-27 12:41:00".to_string()),
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_plc_curve_range_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new().with_plc_data(vec![
        PlcDataRow {
            id: 10,
            secondary_coil_id: 10,
            location_s: Some(10.1),
            location_l: Some(10.2),
            location_laser: Some(10.3),
            start_time: Some("2026-06-27 10:00:00".to_string()),
            pcl_data: None,
        },
        PlcDataRow {
            id: 11,
            secondary_coil_id: 20,
            location_s: Some(20.1),
            location_l: Some(20.2),
            location_laser: Some(20.3),
            start_time: Some("2026-06-27 11:00:00".to_string()),
            pcl_data: None,
        },
        PlcDataRow {
            id: 12,
            secondary_coil_id: 30,
            location_s: Some(30.1),
            location_l: Some(30.2),
            location_laser: Some(30.3),
            start_time: Some("2026-06-27 12:00:00".to_string()),
            pcl_data: None,
        },
    ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_grader_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new().with_coils(vec![
        CoilSummaryRow {
            id: 42,
            coil_no: "LG-20260627-0042".to_string(),
            create_time: Some("2026-06-27 12:34:56".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(55.0),
            act_width: Some(1248.5),
            next_code: None,
            next_info: None,
            s_defect_grad: 2,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 2,
            s_flat_roll_grad: 2,
            s_grad: 2,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: None,
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        },
        CoilSummaryRow {
            id: 41,
            coil_no: "LG-20260627-0041".to_string(),
            create_time: Some("2026-06-27 12:00:00".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1300.0),
            thickness: Some(2.299999952316284),
            width: Some(1240.0),
            weight: Some(65.0),
            act_width: Some(1238.5),
            next_code: None,
            next_info: None,
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: None,
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        },
    ]);
    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_alarm_rows() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 42,
            coil_no: "LG-20260627-0042".to_string(),
            create_time: Some("2026-06-27 12:34:56".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 2,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 2,
            s_flat_roll_grad: 2,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("A".to_string()),
            s_next_name: Some("下一工序".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: true,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 12:35:10".to_string()),
            check_status: 2,
            status_l: 1,
            status_s: 2,
            grade: 2,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: true,
        }])
        .with_coil_states(vec![CoilStateRow {
            id: 31,
            secondary_coil_id: 42,
            surface: "S".to_string(),
            start_time: Some("2026-06-27 12:35:11".to_string()),
            scan3d_coordinate_scale_x: Some(0.1),
            scan3d_coordinate_scale_y: Some(1.0),
            scan3d_coordinate_scale_z: Some(0.0162),
            rotate: Some(90),
            x_rotate: Some(17),
            median_3d: Some(57745.0),
            median_3d_mm: Some(936.9),
            color_from_value_mm: Some(-30.0),
            color_to_value_mm: Some(30.0),
            start: Some(56000.0),
            step: Some(2483.0),
            upper_limit: Some(6205.0),
            lower_limit: Some(-3102.0),
            lower_area: Some(178691),
            upper_area: Some(925),
            lower_area_percent: Some(0.007),
            upper_area_percent: Some(0.0003),
            mask_area: Some(25_249_781),
            width: Some(6995),
            height: Some(5180),
            json_data: None,
        }])
        .with_alarm_flat_rolls(vec![
            AlarmFlatRollRow {
                id: 81,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                out_circle_width: Some(401.0),
                out_circle_height: Some(402.0),
                out_circle_center_x: Some(11.0),
                out_circle_center_y: Some(12.0),
                out_circle_radius: Some(13.0),
                inner_circle_width: Some(301.0),
                inner_circle_height: Some(302.0),
                inner_circle_center_x: Some(21.0),
                inner_circle_center_y: Some(22.0),
                inner_circle_radius: Some(23.0),
                accuracy_x: Some(0.1),
                accuracy_y: Some(0.2),
                level: Some(2),
                err_msg: Some("扁卷报警".to_string()),
                crate_time: Some("2026-06-27 12:41:00".to_string()),
                data: Some("{\"flat\":true}".to_string()),
            },
            AlarmFlatRollRow {
                id: 82,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                out_circle_width: Some(411.0),
                out_circle_height: Some(412.0),
                out_circle_center_x: Some(31.0),
                out_circle_center_y: Some(32.0),
                out_circle_radius: Some(33.0),
                inner_circle_width: Some(311.0),
                inner_circle_height: Some(312.0),
                inner_circle_center_x: Some(41.0),
                inner_circle_center_y: Some(42.0),
                inner_circle_radius: Some(43.0),
                accuracy_x: Some(0.3),
                accuracy_y: Some(0.4),
                level: Some(3),
                err_msg: Some("扁卷历史报警".to_string()),
                crate_time: Some("2026-06-27 12:41:30".to_string()),
                data: Some("{\"flat\":2}".to_string()),
            },
            AlarmFlatRollRow {
                id: 83,
                secondary_coil_id: 42,
                surface: "L".to_string(),
                out_circle_width: Some(421.0),
                out_circle_height: Some(422.0),
                out_circle_center_x: Some(51.0),
                out_circle_center_y: Some(52.0),
                out_circle_radius: Some(53.0),
                inner_circle_width: Some(321.0),
                inner_circle_height: Some(322.0),
                inner_circle_center_x: Some(61.0),
                inner_circle_center_y: Some(62.0),
                inner_circle_radius: Some(63.0),
                accuracy_x: Some(0.5),
                accuracy_y: Some(0.6),
                level: Some(4),
                err_msg: Some("扁卷第三条报警".to_string()),
                crate_time: Some("2026-06-27 12:42:30".to_string()),
                data: Some("{\"flat\":3}".to_string()),
            },
        ])
        .with_alarm_taper_shapes(vec![
            AlarmTaperShapeRow {
                id: 91,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                out_taper_max_x: Some(101),
                out_taper_max_y: Some(102),
                out_taper_max_value: Some(3.4),
                out_taper_min_x: Some(103),
                out_taper_min_y: Some(104),
                out_taper_min_value: Some(-1.2),
                in_taper_max_x: Some(105),
                in_taper_max_y: Some(106),
                in_taper_max_value: Some(2.2),
                in_taper_min_x: Some(107),
                in_taper_min_y: Some(108),
                in_taper_min_value: Some(-0.8),
                rotation_angle: Some(1.5),
                level: Some(3),
                err_msg: Some("塔形报警".to_string()),
                crate_time: Some("2026-06-27 12:42:00".to_string()),
                data: Some("{\"taper\":true}".to_string()),
            },
            AlarmTaperShapeRow {
                id: 92,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                out_taper_max_x: Some(201),
                out_taper_max_y: Some(202),
                out_taper_max_value: Some(9.9),
                out_taper_min_x: Some(203),
                out_taper_min_y: Some(204),
                out_taper_min_value: Some(-9.1),
                in_taper_max_x: Some(205),
                in_taper_max_y: Some(206),
                in_taper_max_value: Some(8.2),
                in_taper_min_x: Some(207),
                in_taper_min_y: Some(208),
                in_taper_min_value: Some(-8.8),
                rotation_angle: Some(3.5),
                level: Some(4),
                err_msg: Some("孤立塔形报警".to_string()),
                crate_time: Some("2026-06-27 12:42:30".to_string()),
                data: Some("{\"orphanTaper\":true}".to_string()),
            },
        ])
        .with_alarm_loose_coils(vec![
            AlarmLooseCoilRow {
                id: 101,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                max_width: Some(200.0),
                rotation_angle: Some(2.5),
                level: Some(1),
                err_msg: Some("松卷报警".to_string()),
                crate_time: Some("2026-06-27 12:43:00".to_string()),
                data: Some("{\"max_width_unit\":\"px\",\"max_width_px\":200}".to_string()),
            },
            AlarmLooseCoilRow {
                id: 102,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                max_width: Some(299.0),
                rotation_angle: Some(4.5),
                level: Some(2),
                err_msg: Some("孤立松卷报警".to_string()),
                crate_time: Some("2026-06-27 12:43:30".to_string()),
                data: Some("{\"orphanLoose\":true}".to_string()),
            },
        ])
        .with_taper_shape_points(vec![
            TaperShapePointRow {
                id: 111,
                secondary_coil_id: 42,
                surface: "S".to_string(),
                x: Some(501),
                y: Some(502),
                value: Some(12.5),
                level: Some(2),
                err_msg: Some("塔形点报警".to_string()),
                crate_time: Some("2026-06-27 12:44:00".to_string()),
                data: Some("{\"point\":true}".to_string()),
            },
            TaperShapePointRow {
                id: 112,
                secondary_coil_id: 999,
                surface: "L".to_string(),
                x: Some(601),
                y: Some(602),
                value: Some(22.5),
                level: Some(3),
                err_msg: Some("孤立塔形点报警".to_string()),
                crate_time: Some("2026-06-27 12:44:30".to_string()),
                data: Some("{\"orphanPoint\":true}".to_string()),
            },
        ]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn app_with_xlsx_taper_detail_seed_data() -> axum::Router {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 47,
            coil_no: "LG-20260627-0047".to_string(),
            create_time: Some("2026-06-27 12:47:56".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("A".to_string()),
            s_next_name: Some("下一工序".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 12:48:10".to_string()),
            check_status: 2,
            status_l: 1,
            status_s: 2,
            grade: 2,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: true,
        }])
        .with_alarm_taper_shapes(vec![AlarmTaperShapeRow {
            id: 471,
            secondary_coil_id: 47,
            surface: "S".to_string(),
            out_taper_max_x: Some(101),
            out_taper_max_y: Some(102),
            out_taper_max_value: Some(3.4),
            out_taper_min_x: Some(103),
            out_taper_min_y: Some(104),
            out_taper_min_value: Some(-1.2),
            in_taper_max_x: Some(105),
            in_taper_max_y: Some(106),
            in_taper_max_value: Some(2.2),
            in_taper_min_x: Some(107),
            in_taper_min_y: Some(108),
            in_taper_min_value: Some(-0.8),
            rotation_angle: Some(12.5),
            level: Some(3),
            err_msg: Some("塔形详细报警".to_string()),
            crate_time: Some("2026-06-27 12:48:00".to_string()),
            data: Some(
                json!({
                    "worst_label": "边部突出",
                    "worst_mm": -4.25,
                    "worst_abs_mm": 4.25,
                    "worst_point_type": "outer",
                    "worst_x": 123,
                    "worst_y": 456,
                    "worst_z": 7.5,
                    "angle_filter": ["1.0", 2.5, "raw"],
                    "angle_tolerance": 0.2,
                    "valid_angle_coverage_ratio": 0.75,
                    "valid_line_count": 9,
                    "covered_angle_count": 11,
                    "taper_attempt_count": 13,
                    "raw_taper_attempt_count": 15,
                    "detection_error_count": 2,
                    "raw_detection_error_count": 3,
                    "warning_count": 4,
                    "grading_error_count": 5
                })
                .to_string(),
            ),
        }]);

    build_app(ApiState::new(Arc::new(repository)))
}

fn write_camera_config(root: &PathBuf) -> PathBuf {
    write_camera_config_with_endpoint(root, "0.0.0.0", 6100)
}

fn write_camera_config_with_endpoint(
    root: &PathBuf,
    api_server_ip: &str,
    api_server_port: u16,
) -> PathBuf {
    let config_path = root.join("CapTure.json");
    fs::write(
        &config_path,
        serde_json::to_vec_pretty(&json!({
            "signalUrl": "http://127.0.0.1:6005/currentCoil",
            "apiServerIp": api_server_ip,
            "apiServerPort": api_server_port,
            "camera": [
                {
                    "sn": "SN-SD",
                    "name": "S_D",
                    "saveFolder": "G:\\",
                    "key": "Cap_S_D",
                    "serverIp": "0.0.0.0",
                    "serverPort": 6104,
                    "yaml_config": "Area_S_D.yaml"
                },
                {
                    "sn": "SN-LD",
                    "name": "L_D",
                    "saveFolder": "F:\\",
                    "key": "Cap_L_D",
                    "serverIp": "192.168.1.9",
                    "serverPort": 6101,
                    "yaml_config": "Area_L_D.yaml"
                }
            ]
        }))
        .expect("camera config"),
    )
    .expect("write camera config");
    config_path
}

fn write_camera_server_config(root: &PathBuf) -> PathBuf {
    let config_path = root.join("Server3D.json");
    fs::write(
        &config_path,
        serde_json::to_vec_pretty(&json!({
            "surface": [
                {
                    "key": "S",
                    "saveFolder": "D:\\Save_S",
                    "rotate": 90,
                    "x_rotate": 17,
                    "direction": "L",
                    "save3D_data": true,
                    "folderList": [
                        {"source": "G:\\Cap_S_D", "cropLeft": 100, "cropRight": 100, "cameraKey": "Cap_S_D"}
                    ]
                },
                {
                    "key": "L",
                    "saveFolder": "E:\\Save_L",
                    "rotate": -90,
                    "x_rotate": 10,
                    "direction": "R",
                    "save3D_data": true,
                    "folderList": [
                        {"source": "F:\\Cap_L_D", "cropLeft": 80, "cropRight": 80, "cameraKey": "Cap_L_D"}
                    ]
                }
            ]
        }))
        .expect("server config"),
    )
    .expect("write server config");
    config_path
}

fn write_local_placeholder_camera_config(root: &PathBuf) -> PathBuf {
    let config_path = root.join("CapTureLoc.json");
    fs::write(
        &config_path,
        serde_json::to_vec_pretty(&json!({
            "signalUrl": "http://127.0.0.1:6005/currentCoil",
            "camera": [
                {
                    "sn": "LOCAL-1",
                    "name": "Camera 1",
                    "saveFolder": "E:\\",
                    "key": "camera1"
                }
            ]
        }))
        .expect("local placeholder camera config"),
    )
    .expect("write local placeholder camera config");
    config_path
}

fn write_testdata_surface(testdata_dir: &PathBuf, surface: &str, height: u32, width: u32) {
    let surface_dir = testdata_dir.join(surface);
    fs::create_dir_all(surface_dir.join("jpg")).expect("jpg dir");
    fs::create_dir_all(surface_dir.join("meshes")).expect("mesh dir");
    fs::write(surface_dir.join("3D.npz"), b"placeholder").expect("3d marker");
    fs::write(
        surface_dir.join("meshes").join("defaultobject_mesh.mesh"),
        b"o test",
    )
    .expect("mesh marker");
    fs::write(surface_dir.join("jpg").join("GRAY.jpg"), b"gray").expect("gray marker");
    fs::write(surface_dir.join("jpg").join("AREA.jpg"), b"area").expect("area marker");
    fs::write(
        surface_dir.join("data.json"),
        serde_json::to_vec(&json!({
            "coilId": "193113",
            "surface": surface,
            "shape": [height, width],
            "source": "unit-test"
        }))
        .expect("json"),
    )
    .expect("data json");
}

fn write_render_testdata_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 12, 34);
    let surface_dir = testdata_dir.join(surface);
    fs::create_dir_all(surface_dir.join("preview")).expect("preview dir");
    fs::write(
        surface_dir.join("jpg").join("JET.jpg"),
        b"\xff\xd8jet-full\xff\xd9",
    )
    .expect("jet render marker");
    fs::write(
        surface_dir.join("jpg").join("GRAY.jpg"),
        b"\xff\xd8gray-full\xff\xd9",
    )
    .expect("gray render marker");
    fs::write(
        surface_dir.join("preview").join("GRAY.jpg"),
        b"\xff\xd8gray-preview\xff\xd9",
    )
    .expect("gray preview marker");
}

fn write_dynamic_render_surface(testdata_dir: &PathBuf, surface: &str) {
    let surface_dir = testdata_dir.join(surface);
    fs::create_dir_all(surface_dir.join("mask")).expect("mask dir");
    fs::write(
        surface_dir.join("data.json"),
        serde_json::to_vec(&json!({
            "coilId": "193113",
            "surface": surface,
            "shape": [2, 4],
            "source": "dynamic-render-test"
        }))
        .expect("json"),
    )
    .expect("data json");
    let array = arr2(&[[0.0, 50.0, 100.0, 150.0], [200.0, 250.0, 300.0, 350.0]]);
    write_npy(surface_dir.join("3D.npy"), &array).expect("write render npy");

    let mut mask = GrayImage::from_pixel(4, 2, Luma([255]));
    mask.put_pixel(3, 1, Luma([0]));
    mask.save_with_format(surface_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write mask");
}

fn write_runtime_config(path: &PathBuf, save_s: &PathBuf, save_l: &PathBuf) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        path,
        serde_json::to_vec(&json!({
            "surface": [
                {"key": "S", "saveFolder": save_s.to_string_lossy()},
                {"key": "L", "saveFolder": save_l.to_string_lossy()}
            ]
        }))
        .expect("config json"),
    )
    .expect("write runtime config");
}

fn write_backup_runtime_config(
    path: &PathBuf,
    save_s: &PathBuf,
    save_l: &PathBuf,
    source_s: &PathBuf,
    source_l: &PathBuf,
) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        path,
        serde_json::to_vec(&json!({
            "surface": [
                {
                    "key": "S",
                    "saveFolder": save_s.to_string_lossy(),
                    "folderList": [
                        {"cameraKey": "S_D", "source": source_s.to_string_lossy()}
                    ]
                },
                {
                    "key": "L",
                    "saveFolder": save_l.to_string_lossy(),
                    "folderList": [
                        {"cameraKey": "L_U", "source": source_l.to_string_lossy()}
                    ]
                }
            ]
        }))
        .expect("config json"),
    )
    .expect("write backup runtime config");
}

fn write_area_join_config(path: &PathBuf) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("area join config parent");
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&json!({
            "surfaces": {
                "S": {
                    "cameras": [
                        {"folder": "G:\\Cap_S_D", "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": "D:\\Save_S",
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 200,
                        "a": 3,
                        "b": 220,
                        "c": 2600,
                        "offset": 77
                    }
                },
                "L": {
                    "cameras": [
                        {"folder": "F:\\Cap_L_U", "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": "E:\\Save_L",
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 200,
                        "a": 3,
                        "b": 220,
                        "c": 4000,
                        "offset": 40
                    }
                }
            }
        }))
        .expect("area join config json"),
    )
    .expect("write area join config");
}

fn write_scan_area_join_config(
    path: &PathBuf,
    source_s: &PathBuf,
    source_l: &PathBuf,
    save_s: &PathBuf,
    save_l: &PathBuf,
) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("area scan config parent");
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&json!({
            "surfaces": {
                "S": {
                    "cameras": [
                        {"folder": source_s.to_string_lossy(), "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": save_s.to_string_lossy(),
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 200,
                        "a": 3,
                        "b": 220,
                        "c": 2600,
                        "offset": 40
                    }
                },
                "L": {
                    "cameras": [
                        {"folder": source_l.to_string_lossy(), "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": save_l.to_string_lossy(),
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 200,
                        "a": 3,
                        "b": 220,
                        "c": 4000,
                        "offset": 40
                    }
                }
            }
        }))
        .expect("area scan config json"),
    )
    .expect("write area scan config");
}

fn write_rejoin_area_join_config(
    path: &PathBuf,
    source_u: &PathBuf,
    source_m: &PathBuf,
    source_d: &PathBuf,
    save_s: &PathBuf,
) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("area rejoin config parent");
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&json!({
            "surfaces": {
                "S": {
                    "cameras": [
                        {"folder": source_u.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_m.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_d.to_string_lossy(), "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": save_s.to_string_lossy(),
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 1,
                        "a": 3,
                        "b": 220,
                        "c": 2600,
                        "offset": 40
                    }
                }
            }
        }))
        .expect("area rejoin config json"),
    )
    .expect("write area rejoin config");
}

fn write_dynamic_rejoin_area_join_config(
    path: &PathBuf,
    source_u: &PathBuf,
    source_m: &PathBuf,
    source_d: &PathBuf,
    save_s: &PathBuf,
) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("dynamic area rejoin config parent");
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&json!({
            "surfaces": {
                "S": {
                    "cameras": [
                        {"folder": source_u.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_m.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_d.to_string_lossy(), "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": save_s.to_string_lossy(),
                    "clip_config": {
                        "mode": "dynamic",
                        "fixed": 1,
                        "a": 2,
                        "b": 4,
                        "c": 933.9,
                        "offset": 2
                    }
                }
            }
        }))
        .expect("dynamic area rejoin config json"),
    )
    .expect("write dynamic area rejoin config");
}

fn write_unordered_rejoin_area_join_config(
    path: &PathBuf,
    source_u: &PathBuf,
    source_m: &PathBuf,
    source_d: &PathBuf,
    save_s: &PathBuf,
) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("unordered area rejoin config parent");
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&json!({
            "surfaces": {
                "S": {
                    "cameras": [
                        {"folder": source_d.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_u.to_string_lossy(), "loss_num": 0, "max_len": 10},
                        {"folder": source_m.to_string_lossy(), "loss_num": 0, "max_len": 10}
                    ],
                    "save_folder": save_s.to_string_lossy(),
                    "clip_config": {
                        "mode": "fixed",
                        "fixed": 0,
                        "a": 3,
                        "b": 220,
                        "c": 2600,
                        "offset": 40
                    }
                }
            }
        }))
        .expect("unordered area rejoin config json"),
    )
    .expect("write unordered area rejoin config");
}

fn write_area_camera_jpgs(source_root: &PathBuf, coil_id: i64, count: usize) {
    let coil_dir = source_root.join(coil_id.to_string()).join("area");
    fs::create_dir_all(&coil_dir).expect("area camera coil dir");
    for index in 0..count {
        fs::write(coil_dir.join(format!("{index}.jpg")), b"jpg").expect("area camera jpg");
    }
}

fn write_area_camera_rgb_jpgs(
    source_root: &PathBuf,
    coil_id: i64,
    width: u32,
    height: u32,
    color_seed: u8,
) {
    let coil_dir = source_root.join(coil_id.to_string()).join("area");
    fs::create_dir_all(&coil_dir).expect("area camera rgb dir");
    for index in 0..2 {
        let mut image = RgbImage::new(width, height);
        for y in 0..height {
            for x in 0..width {
                image.put_pixel(
                    x,
                    y,
                    Rgb([
                        color_seed.wrapping_add(index as u8 * 20),
                        (x * 17 + y * 3) as u8,
                        (y * 19 + index as u32 * 7) as u8,
                    ]),
                );
            }
        }
        image
            .save_with_format(coil_dir.join(format!("{index}.jpg")), ImageFormat::Jpeg)
            .expect("write area camera rgb jpg");
    }
}

fn write_area_camera_solid_jpgs(source_root: &PathBuf, coil_id: i64, color: [u8; 3]) {
    let coil_dir = source_root.join(coil_id.to_string()).join("area");
    fs::create_dir_all(&coil_dir).expect("area camera solid dir");
    for index in 0..2 {
        let image = RgbImage::from_pixel(3, 6, Rgb(color));
        image
            .save_with_format(coil_dir.join(format!("{index}.jpg")), ImageFormat::Jpeg)
            .expect("write area camera solid jpg");
    }
}

fn write_area_camera_overlap_jpgs(source_root: &PathBuf, coil_id: i64, color: [u8; 3]) {
    let coil_dir = source_root.join(coil_id.to_string()).join("area");
    fs::create_dir_all(&coil_dir).expect("area camera overlap dir");
    for (index, (left, right)) in [(4, 25), (16, 37)].iter().enumerate() {
        let mut image = RgbImage::from_pixel(40, 20, Rgb([0, 0, 0]));
        for y in 4..16 {
            for x in *left..=*right {
                image.put_pixel(x, y, Rgb(color));
            }
        }
        image
            .save_with_format(coil_dir.join(format!("{index}.jpg")), ImageFormat::Jpeg)
            .expect("write area camera overlap jpg");
    }
}

fn write_capture_source_coil(source_root: &PathBuf, coil_id: i64, marker: &str) {
    let coil_dir = source_root.join(coil_id.to_string()).join("2D");
    fs::create_dir_all(&coil_dir).expect("capture coil dir");
    fs::write(coil_dir.join("frame.txt"), marker).expect("capture marker");
}

fn write_capture_source_coil_with_compressible_data(source_root: &PathBuf, coil_id: i64) {
    let coil_dir = source_root.join(coil_id.to_string());
    let image_dir = coil_dir.join("2D");
    let depth_dir = coil_dir.join("3D");
    fs::create_dir_all(&image_dir).expect("capture image dir");
    fs::create_dir_all(&depth_dir).expect("capture depth dir");
    fs::write(image_dir.join("frame.bmp"), minimal_2x2_bmp()).expect("write capture bmp");
    write_npy(
        depth_dir.join("depth.npy"),
        &arr2(&[[1.0_f64, 2.0], [3.0, 4.0]]),
    )
    .expect("write capture npy");
}

fn minimal_2x2_bmp() -> Vec<u8> {
    vec![
        0x42, 0x4d, 70, 0, 0, 0, 0, 0, 0, 0, 54, 0, 0, 0, 40, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 1,
        0, 24, 0, 0, 0, 0, 0, 16, 0, 0, 0, 19, 11, 0, 0, 19, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255,
        0, 0, 0, 255, 0, 0, 0, 0, 0, 255, 255, 255, 0, 0, 0,
    ]
}

fn write_full_info_runtime_config(path: &PathBuf, save_s: &PathBuf, save_l: &PathBuf) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        path,
        serde_json::to_vec(&json!({
            "surface": [
                {
                    "key": "S",
                    "saveFolder": save_s.to_string_lossy(),
                    "rotate": 90,
                    "x_rotate": 17,
                    "direction": "L",
                    "save3D_data": true,
                    "folderList": [
                        {"cameraKey": "S_D", "source": "G:\\Cap_S_D", "cropLeft": 100, "cropRight": 100}
                    ]
                },
                {
                    "key": "L",
                    "saveFolder": save_l.to_string_lossy(),
                    "rotate": -90,
                    "x_rotate": 10,
                    "direction": "R",
                    "save3D_data": false,
                    "folderList": [
                        {"cameraKey": "L_U", "source": "F:\\Cap_L_U", "cropLeft": 80, "cropRight": 80}
                    ]
                }
            ],
            "colorFromValue_mm": -100,
            "colorToValue_mm": 100
        }))
        .expect("config json"),
    )
    .expect("write full runtime config");
}

fn write_real_npy_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 1, 1);
    let surface_dir = testdata_dir.join(surface);
    let array = arr2(&[[0.0, 10.0, 20.0], [30.0, 40.0, 2600.8]]);
    let _ = fs::remove_file(surface_dir.join("3D.npz"));
    write_npy(surface_dir.join("3D.npy"), &array).expect("write npy");
}

fn write_real_npz_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 2, 3);
    let surface_dir = testdata_dir.join(surface);
    let array = arr2(&[[0.0, 101.0, 102.0], [103.0, 104.0, 3050.9]]);
    let file = File::create(surface_dir.join("3D.npz")).expect("create npz");
    let mut npz = NpzWriter::new(file);
    npz.add_array("array", &array).expect("add npz array");
    npz.finish().expect("finish npz");
}

fn write_long_line_npy_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 1, 105);
    let surface_dir = testdata_dir.join(surface);
    let mut array = ndarray::Array2::<f64>::zeros((1, 105));
    for x in 0..105 {
        array[(0, x)] = 500.0 + x as f64;
    }
    let _ = fs::remove_file(surface_dir.join("3D.npz"));
    write_npy(surface_dir.join("3D.npy"), &array).expect("write long line npy");
}

fn write_masked_edge_line_npy_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 1, 250);
    let surface_dir = testdata_dir.join(surface);
    fs::create_dir_all(surface_dir.join("mask")).expect("mask dir");

    let mut array = ndarray::Array2::<f64>::zeros((1, 250));
    for x in 0..250 {
        array[(0, x)] = 500.0 + x as f64;
    }
    let _ = fs::remove_file(surface_dir.join("3D.npz"));
    write_npy(surface_dir.join("3D.npy"), &array).expect("write masked line npy");

    let mut mask = GrayImage::from_pixel(250, 1, Luma([0]));
    for x in 0..=104 {
        mask.put_pixel(x, 0, Luma([255]));
    }
    for x in 125..250 {
        mask.put_pixel(x, 0, Luma([255]));
    }
    mask.save_with_format(surface_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write masked line mask");
}

fn write_masked_diagonal_line_npy_surface(testdata_dir: &PathBuf, surface: &str) {
    write_testdata_surface(testdata_dir, surface, 120, 240);
    let surface_dir = testdata_dir.join(surface);
    fs::create_dir_all(surface_dir.join("mask")).expect("mask dir");

    let mut array = ndarray::Array2::<f64>::zeros((120, 240));
    for y in 0..120 {
        for x in 0..240 {
            array[(y, x)] = 1000.0 + (x as f64 * 10.0) + y as f64;
        }
    }
    let _ = fs::remove_file(surface_dir.join("3D.npz"));
    write_npy(surface_dir.join("3D.npy"), &array).expect("write diagonal line npy");

    let mut mask = GrayImage::from_pixel(240, 120, Luma([0]));
    for y in 0..120 {
        for x in 0..=109 {
            mask.put_pixel(x, y, Luma([255]));
        }
        for x in 130..=239 {
            mask.put_pixel(x, y, Luma([255]));
        }
    }
    mask.save_with_format(surface_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write diagonal line mask");
}

fn write_runtime_real_npy_coil(save_root: &PathBuf, coil_id: i64) -> PathBuf {
    let coil_dir = save_root.join(coil_id.to_string());
    fs::create_dir_all(&coil_dir).expect("runtime coil dir");
    fs::write(
        coil_dir.join("data.json"),
        serde_json::to_vec(&json!({
            "coilId": coil_id.to_string(),
            "surface": "stale",
            "shape": [1, 1],
            "source": "runtime-config-test"
        }))
        .expect("json"),
    )
    .expect("runtime data json");
    let array = arr2(&[[0.0, 10.0, 20.0], [30.0, 40.0, 2600.8]]);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write runtime npy");
    coil_dir
}

fn write_runtime_long_line_npy_coil(save_root: &PathBuf, coil_id: i64) -> PathBuf {
    let coil_dir = save_root.join(coil_id.to_string());
    fs::create_dir_all(&coil_dir).expect("runtime line coil dir");
    fs::write(
        coil_dir.join("data.json"),
        serde_json::to_vec(&json!({
            "coilId": coil_id.to_string(),
            "surface": "S",
            "shape": [1, 105],
            "source": "runtime-config-line-test"
        }))
        .expect("json"),
    )
    .expect("runtime line data json");
    let mut array = ndarray::Array2::<f64>::zeros((1, 105));
    for x in 0..105 {
        array[(0, x)] = 500.0 + x as f64;
    }
    write_npy(coil_dir.join("3D.npy"), &array).expect("write runtime line npy");
    coil_dir
}

fn write_runtime_render_cached_coil(save_root: &PathBuf, coil_id: i64) -> PathBuf {
    let coil_dir = save_root.join(coil_id.to_string());
    fs::create_dir_all(coil_dir.join("jpg")).expect("runtime render jpg dir");
    fs::create_dir_all(coil_dir.join("preview")).expect("runtime render preview dir");
    fs::write(
        coil_dir.join("jpg").join("JET.jpg"),
        b"\xff\xd8runtime-jet-full\xff\xd9",
    )
    .expect("runtime jet render marker");
    fs::write(
        coil_dir.join("preview").join("GRAY.jpg"),
        b"\xff\xd8runtime-gray-preview\xff\xd9",
    )
    .expect("runtime gray preview marker");
    coil_dir
}

fn write_runtime_gray_image_coil(
    save_root: &PathBuf,
    coil_id: i64,
    width: u32,
    height: u32,
) -> PathBuf {
    let coil_dir = save_root.join(coil_id.to_string());
    fs::create_dir_all(coil_dir.join("jpg")).expect("runtime gray jpg dir");
    let mut image = GrayImage::new(width, height);
    for y in 0..height {
        for x in 0..width {
            image.put_pixel(x, y, Luma([((x + y) % 255) as u8]));
        }
    }
    image
        .save_with_format(coil_dir.join("jpg").join("GRAY.jpg"), ImageFormat::Jpeg)
        .expect("write runtime gray image");
    coil_dir
}

fn write_runtime_named_gray_image(
    coil_dir: &PathBuf,
    folder: &str,
    name: &str,
    width: u32,
    height: u32,
) {
    fs::create_dir_all(coil_dir.join(folder)).expect("runtime named image dir");
    let mut image = GrayImage::new(width, height);
    for y in 0..height {
        for x in 0..width {
            image.put_pixel(x, y, Luma([((x * 3 + y * 5) % 255) as u8]));
        }
    }
    image
        .save_with_format(
            coil_dir.join(folder).join(format!("{name}.jpg")),
            ImageFormat::Jpeg,
        )
        .expect("write runtime named image");
}

fn write_runtime_named_gray_png_image(
    coil_dir: &PathBuf,
    folder: &str,
    name: &str,
    width: u32,
    height: u32,
) {
    fs::create_dir_all(coil_dir.join(folder)).expect("runtime named png dir");
    let mut image = GrayImage::new(width, height);
    for y in 0..height {
        for x in 0..width {
            image.put_pixel(x, y, Luma([((x * 7 + y * 11) % 255) as u8]));
        }
    }
    image
        .save_with_format(
            coil_dir.join(folder).join(format!("{name}.png")),
            ImageFormat::Png,
        )
        .expect("write runtime named png image");
}

fn write_runtime_dynamic_render_coil(save_root: &PathBuf, coil_id: i64) -> PathBuf {
    let coil_dir = save_root.join(coil_id.to_string());
    fs::create_dir_all(coil_dir.join("mask")).expect("runtime render mask dir");
    let array = arr2(&[[0.0, 50.0, 100.0, 150.0], [200.0, 250.0, 300.0, 350.0]]);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write runtime render npy");

    let mut mask = GrayImage::from_pixel(4, 2, Luma([255]));
    mask.put_pixel(3, 1, Luma([0]));
    mask.save_with_format(coil_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write runtime render mask");
    coil_dir
}

async fn spawn_test_server(app: axum::Router) -> String {
    spawn_ws_server(app, "/ws/coilData/heightPoint").await
}

async fn spawn_ws_server(app: axum::Router, path: &str) -> String {
    let base_url = spawn_http_server(app).await;
    format!("{}{}", base_url.replace("http://", "ws://"), path)
}

async fn spawn_http_server(app: axum::Router) -> String {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind ephemeral server port");
    let addr = listener.local_addr().expect("server addr");
    tokio::spawn(async move {
        axum::serve(listener, app).await.expect("test server");
    });
    format!("http://{addr}")
}

#[tokio::test]
async fn health_matches_service_contract() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/health").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"status":"ok","service":"rust_api_service"}));
}

fn app_with_empty_data() -> axum::Router {
    build_app(ApiState::new(Arc::new(InMemoryCoilRepository::new())))
}

#[tokio::test]
async fn current_coil_matches_python_startup_contract() {
    let response = request_response(app_with_empty_data(), "GET", "/currentCoil").await;
    assert_eq!(response.status(), StatusCode::OK);

    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("currentCoil json");
    assert_eq!(body, json!({}));
}

#[tokio::test]
async fn current_coil_returns_latest_row_from_repository_when_present() {
    let response = request_response(app_with_seed_data(), "GET", "/currentCoil").await;
    assert_eq!(response.status(), StatusCode::OK);

    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("currentCoil json");
    assert_eq!(body["SecondaryCoilId"], 42);
    assert_eq!(body["DetectionTime"], "2026-06-27 12:35:10");
    assert_eq!(body["DefectCountL"], 1);
    assert_eq!(body["Status_L"], 1);
    assert_eq!(body["Grade"], 2);
    assert_eq!(body["DefectCountS"], 3);
    assert_eq!(body["Id"], 42);
    assert_eq!(body["CheckStatus"], 2);
    assert_eq!(body["Status_S"], 2);
    assert_eq!(body["Msg"], "");
    assert_eq!(body["Coil_ID"], "LG-20260627-0042");
    assert_eq!(body["ActWidth"], 1248.5);
    assert_eq!(body["act_w"], 1248.5);
    assert_eq!(body["ACT_W"], 1248.5);
    assert_eq!(body["width"], 1248.5);
}

#[tokio::test]
async fn current_coil_includes_plc_compat_fields_when_secondary_coil_present() {
    let repository = seed_repository_with_defect(0.95, Some(json!({"source":"test"})), 2.4).with_secondary_coils(
        vec![SecondaryCoilRow {
            id: 42,
            coil_no: "REAL-SECONDARY-0042".to_string(),
            coil_type: Some("REAL-Q235".to_string()),
            coil_inside: Some(620.0),
            coil_dia: Some(1330.0),
            thickness: Some(2.6),
            width: Some(1260.0),
            weight: Some(66.0),
            act_width: Some(1258.5),
            create_time: Some("2026-06-27 12:34:50".to_string()),
        }],
    );
    let app = build_app(ApiState::new(Arc::new(repository)));

    let response = request_response(app, "GET", "/currentCoil").await;
    assert_eq!(response.status(), StatusCode::OK);

    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("currentCoil json");
    assert_eq!(body["Coil_ID"], "REAL-SECONDARY-0042");
    assert_eq!(body["ActWidth"], 1258.5);
    assert_eq!(body["act_w"], 1258.5);
    assert_eq!(body["width"], 1258.5);
    assert_eq!(body["Id"], 42);
}

#[tokio::test]
async fn plc_info_matches_python_plc_adapter_startup_contract() {
    let response = request_response(app_with_seed_data(), "GET", "/plc/info/").await;
    assert_eq!(response.status(), StatusCode::OK);

    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("plc info json");
    assert_eq!(
        body,
        json!({
            "typeList": ["int", "real", "dword", "string", "bytes", "word", "bool"],
            "plc_ip": "192.168.0.1",
            "rack": 0,
            "slot": 0,
        })
    );

    let response_without_slash = request_response(app_with_seed_data(), "GET", "/plc/info").await;
    assert_eq!(response_without_slash.status(), StatusCode::OK);
    assert_eq!(
        serde_json::from_slice::<Value>(&response_bytes(response_without_slash).await).expect(
            "plc info no slash json"
        ),
        json!({
            "typeList": ["int", "real", "dword", "string", "bytes", "word", "bool"],
            "plc_ip": "192.168.0.1",
            "rack": 0,
            "slot": 0,
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_plc_adapter_info_contract() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/plc/info/"]["get"]["summary"],
        json!("Info Plc")
    );
    assert_eq!(
        body["paths"]["/plc/info/"]["get"]["operationId"],
        json!("info_plc_plc_info__get")
    );
    assert_eq!(
        body["paths"]["/plc/info"]["get"]["summary"],
        json!("Info Plc")
    );
    assert_eq!(
        body["paths"]["/plc/info"]["get"]["operationId"],
        json!("info_plc_info_get")
    );
    assert_eq!(
        body["paths"]["/plc/info/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/PlcInfoResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["PlcInfoResponse"]["properties"]["typeList"],
        json!({
            "items": {"type": "string"},
            "type": "array",
            "title": "Typelist",
        })
    );
}

#[tokio::test]
async fn plc_connect_endpoint_updates_runtime_state() {
    let app = app_with_seed_data();

    let (_, body) = request_json(app.clone(), "GET", "/plc/connect/10.1.2.3/7/9").await;
    assert_eq!(body, json!(true));

    let (_, info_body) = request_json(app.clone(), "GET", "/plc/info").await;
    assert_eq!(info_body["plc_ip"], json!("10.1.2.3"));
    assert_eq!(info_body["rack"], json!(7));
    assert_eq!(info_body["slot"], json!(9));
}

#[tokio::test]
async fn plc_get_endpoint_supports_type_conversions() {
    let app = app_with_seed_data();

    let (_, int_value) = request_json(app.clone(), "GET", "/plc/get/DB1/int/2").await;
    assert!(
        int_value.is_i64() || int_value.is_u64(),
        "int response should be integer"
    );

    let (_, real_value) = request_json(app.clone(), "GET", "/plc/get/DB1/real/4").await;
    assert!(real_value.is_number(), "real response should be number");

    let (_, string_value) = request_json(app.clone(), "GET", "/plc/get/DB1/string/3").await;
    assert!(string_value.is_string(), "string response should be string");

    let (_, bool_value) = request_json(app.clone(), "GET", "/plc/get/DB1/bool/1").await;
    assert!(bool_value.is_boolean(), "bool response should be boolean");
}

#[tokio::test]
async fn plc_get_endpoint_rejects_invalid_inputs() {
    let app = app_with_seed_data();

    let bad_type_response = request_response(app.clone(), "GET", "/plc/get/DB1/unknown/2").await;
    assert_eq!(bad_type_response.status(), StatusCode::INTERNAL_SERVER_ERROR);

    let bad_length_response = request_response(app, "GET", "/plc/get/DB1/int/-1").await;
    assert_eq!(bad_length_response.status(), StatusCode::INTERNAL_SERVER_ERROR);
}

#[tokio::test]
async fn openapi_json_describes_plc_connect_and_get_contract() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/plc/connect/{plc_ip}/{rack}/{slot}"]["get"]["summary"],
        json!("Connect Plc")
    );
    assert_eq!(
        body["paths"]["/plc/connect/{plc_ip}/{rack}/{slot}"]["get"]["operationId"],
        json!("connect_plc_plc_connect__plc_ip__rack__slot_get")
    );
    assert_eq!(
        body["paths"]["/plc/connect/{plc_ip}/{rack}/{slot}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"type": "boolean", "title": "PlcConnectionResponse"})
    );

    assert_eq!(
        body["paths"]["/plc/get/{addr}/{type_str}/{length}"]["get"]["summary"],
        json!("Get Plc Value")
    );
    assert_eq!(
        body["paths"]["/plc/get/{addr}/{type_str}/{length}"]["get"]["operationId"],
        json!("forward_request_plc_get__addr___type_str___length__get")
    );
    assert_eq!(
        body["paths"]["/plc/get/{addr}/{type_str}/{length}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/PlcGetValueResponse"})
    );
}

#[tokio::test]
async fn root_version_and_delay_match_python_startup_contract() {
    let (root_status, root_body) = request_json(app_with_seed_data(), "GET", "/").await;
    assert_eq!(root_status, StatusCode::OK);
    assert_eq!(root_body, json!({"/docs": "请访问 /docs 查看文档"}));

    let version_response = request_response(app_with_seed_data(), "GET", "/version").await;
    assert_eq!(version_response.status(), StatusCode::OK);
    let version_bytes = response_bytes(version_response).await;
    assert_eq!(
        serde_json::from_slice::<Value>(&version_bytes).expect("version json"),
        json!("0.1.1")
    );

    let (delay_status, delay_body) = request_json(app_with_seed_data(), "GET", "/delay").await;
    assert_eq!(delay_status, StatusCode::OK);
    assert_eq!(delay_body, json!(0));
}

#[tokio::test]
async fn software_update_manifest_returns_qml_compatible_fields() {
    let _env_lock = lock_test_env();
    let _version = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_VERSION", "0.2.4");
    let _download_url = set_env_var_guard(
        "RUST_API_SOFTWARE_UPDATE_URL",
        "/updates/MotionStudio_0.2.4.exe",
    );
    let _file_name = set_env_var_guard(
        "RUST_API_SOFTWARE_UPDATE_FILE_NAME",
        "MotionStudio_0.2.4.exe",
    );
    let _notes = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_NOTES", "修复渲染与导出");

    let (status, body) =
        request_json(app_with_seed_data(), "GET", "/software_update/manifest").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["version"], "0.2.4");
    assert_eq!(body["latest_version"], "0.2.4");
    assert_eq!(body["download_url"], "/updates/MotionStudio_0.2.4.exe");
    assert_eq!(body["package_url"], "/updates/MotionStudio_0.2.4.exe");
    assert_eq!(body["file_name"], "MotionStudio_0.2.4.exe");
    assert_eq!(body["release_notes"], "修复渲染与导出");
    assert_eq!(body["current_version"], "0.1.1");
}

#[tokio::test]
async fn software_update_manifest_derives_package_url_from_configured_file() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("create temp root");
    let package_path = root.join("MotionStudio_0.3.0.exe");
    fs::write(&package_path, b"installer-bytes").expect("write package");
    let _package_guard = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE", &package_path);
    let _download_url = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_URL", "");
    let _file_name = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_FILE_NAME", "");

    let (status, body) =
        request_json(app_with_seed_data(), "GET", "/software_update/manifest").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["download_url"], "/updates/MotionStudio_0.3.0.exe");
    assert_eq!(body["package_url"], "/updates/MotionStudio_0.3.0.exe");
    assert_eq!(body["downloadUrl"], "/updates/MotionStudio_0.3.0.exe");
    assert_eq!(body["packageUrl"], "/updates/MotionStudio_0.3.0.exe");
    assert_eq!(body["file_name"], "MotionStudio_0.3.0.exe");
    assert_eq!(body["fileName"], "MotionStudio_0.3.0.exe");
}

#[tokio::test]
async fn software_update_package_download_serves_configured_installer_file() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("create temp root");
    let package_path = root.join("MotionStudio_0.2.4.exe");
    fs::write(&package_path, b"installer-bytes").expect("write package");
    let _package_guard = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE", &package_path);

    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/updates/MotionStudio_0.2.4.exe",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        response
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/octet-stream")
    );
    assert_eq!(
        response
            .headers()
            .get(header::CONTENT_DISPOSITION)
            .and_then(|value| value.to_str().ok()),
        Some("attachment; filename=\"MotionStudio_0.2.4.exe\"")
    );
    assert_eq!(
        response
            .headers()
            .get(header::CONTENT_LENGTH)
            .and_then(|value| value.to_str().ok()),
        Some("15")
    );
    assert_eq!(response_bytes(response).await.as_ref(), b"installer-bytes");
}

#[tokio::test]
async fn software_update_package_download_rejects_path_like_file_name() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("create temp root");
    let package_path = root.join("MotionStudio_0.2.4.exe");
    fs::write(&package_path, b"installer-bytes").expect("write package");
    let _package_guard = set_env_var_guard("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE", &package_path);

    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/updates/..%5CMotionStudio_0.2.4.exe",
    )
    .await;

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn runtime_info_returns_python_compatible_environment_shape() {
    let _env_lock = lock_test_env();
    let _developer_mode = set_env_var_guard("API_DEVELOPER_MODE", "true");
    let _offline_mode = set_env_var_guard("API_OFFLINE_MODE", "true");
    let _cache_mode = set_env_var_guard("RUST_API_CACHE_MODE", "redis");
    let _python_version = set_env_var_guard("RUST_API_PYTHON_VERSION", "3.12.10 test");
    let _gpu_models = set_env_var_guard("RUST_API_GPU_MODELS", "NVIDIA RTX A4000;NVIDIA RTX 4090");

    let (status, value) = request_json(app_with_seed_data(), "GET", "/runtime_info").await;

    assert_eq!(status, StatusCode::OK);
    let object = value.as_object().expect("runtime_info object");
    let mut keys = object.keys().map(String::as_str).collect::<Vec<_>>();
    keys.sort_unstable();
    assert_eq!(
        keys,
        vec![
            "cache_mode",
            "cpu_model",
            "developer_mode",
            "gpus",
            "is_local",
            "offline_mode",
            "python_version",
        ]
    );
    assert_eq!(value["python_version"], "3.12.10 test");
    assert_eq!(value["cache_mode"], "redis");
    assert!(value["cpu_model"].is_string());
    assert_eq!(
        value["gpus"],
        json!(["NVIDIA RTX A4000", "NVIDIA RTX 4090"])
    );
    assert_eq!(value["is_local"], true);
    assert_eq!(value["developer_mode"], true);
    assert_eq!(value["offline_mode"], true);
}

#[tokio::test]
async fn runtime_info_defaults_to_python_empty_gpu_list_without_explicit_models() {
    let _env_lock = lock_test_env();
    let _gpu_models = remove_env_var_guard("RUST_API_GPU_MODELS");

    let (status, value) = request_json(app_with_seed_data(), "GET", "/runtime_info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["gpus"], json!([]));
}

#[tokio::test]
async fn runtime_info_defaults_cache_mode_to_python_reference_memory() {
    let _env_lock = lock_test_env();
    let _cache_mode = remove_env_var_guard("RUST_API_CACHE_MODE");
    let _image_cache = remove_env_var_guard("IMAGE_CACHE_BACKEND");
    let _cache_backend = remove_env_var_guard("CACHE_BACKEND");

    let (status, value) = request_json(app_with_seed_data(), "GET", "/runtime_info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["cache_mode"], "memory");
}

#[tokio::test]
async fn runtime_info_matches_python_local_host_developer_mode_default() {
    let _env_lock = lock_test_env();
    let _developer_mode = remove_env_var_guard("API_DEVELOPER_MODE");
    let _computername = set_env_var_guard("COMPUTERNAME", "DESKTOP-94ADH1G");
    let _hostname = set_env_var_guard("HOSTNAME", "production-host");

    let (status, value) = request_json(app_with_seed_data(), "GET", "/runtime_info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["developer_mode"], true);
    assert_eq!(value["is_local"], true);
}

#[tokio::test]
async fn docs_routes_return_python_compatible_html_shells() {
    let docs_response = request_response(app_with_seed_data(), "GET", "/docs").await;
    let docs_status = docs_response.status();
    let docs_headers = docs_response.headers().clone();
    let docs_body =
        String::from_utf8(response_bytes(docs_response).await.to_vec()).expect("docs html text");

    assert_eq!(docs_status, StatusCode::OK);
    assert_eq!(docs_headers["content-type"], "text/html; charset=utf-8");
    assert!(docs_body.contains("Swagger UI"));
    assert!(docs_body.contains("/openapi.json"));
    assert!(docs_body.contains("/static/swagger-ui-bundle.js"));
    assert!(docs_body.contains("/static/swagger-ui.css"));

    let redirect_response =
        request_response(app_with_seed_data(), "GET", "/docs/oauth2-redirect").await;
    let redirect_status = redirect_response.status();
    let redirect_headers = redirect_response.headers().clone();
    let redirect_body = String::from_utf8(response_bytes(redirect_response).await.to_vec())
        .expect("oauth redirect html text");

    assert_eq!(redirect_status, StatusCode::OK);
    assert_eq!(redirect_headers["content-type"], "text/html; charset=utf-8");
    assert!(redirect_body.contains("oauth2RedirectUrl"));

    let redoc_response = request_response(app_with_seed_data(), "GET", "/redoc").await;
    let redoc_status = redoc_response.status();
    let redoc_headers = redoc_response.headers().clone();
    let redoc_body =
        String::from_utf8(response_bytes(redoc_response).await.to_vec()).expect("redoc html text");

    assert_eq!(redoc_status, StatusCode::OK);
    assert_eq!(redoc_headers["content-type"], "text/html; charset=utf-8");
    assert!(redoc_body.contains("ReDoc"));
    assert!(redoc_body.contains("/openapi.json"));
    assert!(redoc_body.contains("/static/redoc.standalone.js"));
}

#[tokio::test]
async fn docs_static_assets_return_local_browser_resources() {
    let swagger_js_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let swagger_js_status = swagger_js_response.status();
    let swagger_js_headers = swagger_js_response.headers().clone();
    let swagger_js_body = String::from_utf8(response_bytes(swagger_js_response).await.to_vec())
        .expect("swagger js text");

    assert_eq!(swagger_js_status, StatusCode::OK);
    assert_eq!(
        swagger_js_headers["content-type"],
        "application/javascript; charset=utf-8"
    );
    assert!(swagger_js_body.contains("SwaggerUIBundle"));
    assert!(swagger_js_body.contains("/openapi.json"));

    let swagger_css_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let swagger_css_status = swagger_css_response.status();
    let swagger_css_headers = swagger_css_response.headers().clone();
    let swagger_css_body = String::from_utf8(response_bytes(swagger_css_response).await.to_vec())
        .expect("swagger css text");

    assert_eq!(swagger_css_status, StatusCode::OK);
    assert_eq!(
        swagger_css_headers["content-type"],
        "text/css; charset=utf-8"
    );
    assert!(swagger_css_body.contains("#swagger-ui"));

    let redoc_js_response =
        request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let redoc_js_status = redoc_js_response.status();
    let redoc_js_headers = redoc_js_response.headers().clone();
    let redoc_js_body =
        String::from_utf8(response_bytes(redoc_js_response).await.to_vec()).expect("redoc js text");

    assert_eq!(redoc_js_status, StatusCode::OK);
    assert_eq!(
        redoc_js_headers["content-type"],
        "application/javascript; charset=utf-8"
    );
    assert!(redoc_js_body.contains("redoc"));
    assert!(redoc_js_body.contains("/openapi.json"));
}

#[tokio::test]
async fn docs_static_assets_render_operation_summaries_and_tags_like_swagger_redoc() {
    let swagger_js_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let swagger_js_body = String::from_utf8(response_bytes(swagger_js_response).await.to_vec())
        .expect("swagger js text");

    assert!(swagger_js_body.contains("operation.summary"));
    assert!(swagger_js_body.contains("operation.tags"));
    assert!(swagger_js_body.contains("swagger-operation-summary"));
    assert!(swagger_js_body.contains("swagger-operation-tag"));

    let swagger_css_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let swagger_css_body = String::from_utf8(response_bytes(swagger_css_response).await.to_vec())
        .expect("swagger css text");

    assert!(swagger_css_body.contains("swagger-operation-summary"));
    assert!(swagger_css_body.contains("swagger-operation-tag"));
    assert!(swagger_css_body.contains("redoc-operation-summary"));
    assert!(swagger_css_body.contains("redoc-operation-tag"));

    let redoc_js_response =
        request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let redoc_js_body =
        String::from_utf8(response_bytes(redoc_js_response).await.to_vec()).expect("redoc js text");

    assert!(redoc_js_body.contains("operation.summary"));
    assert!(redoc_js_body.contains("operation.tags"));
    assert!(redoc_js_body.contains("redoc-operation-summary"));
    assert!(redoc_js_body.contains("redoc-operation-tag"));
}

#[tokio::test]
async fn docs_static_assets_render_operation_descriptions_like_swagger_redoc() {
    let swagger_js_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let swagger_js_body = String::from_utf8(response_bytes(swagger_js_response).await.to_vec())
        .expect("swagger js text");

    assert!(swagger_js_body.contains("operation.description"));
    assert!(swagger_js_body.contains("swagger-operation-description"));

    let swagger_css_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let swagger_css_body = String::from_utf8(response_bytes(swagger_css_response).await.to_vec())
        .expect("swagger css text");

    assert!(swagger_css_body.contains("swagger-operation-description"));
    assert!(swagger_css_body.contains("redoc-operation-description"));

    let redoc_js_response =
        request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let redoc_js_body =
        String::from_utf8(response_bytes(redoc_js_response).await.to_vec()).expect("redoc js text");

    assert!(redoc_js_body.contains("operation.description"));
    assert!(redoc_js_body.contains("redoc-operation-description"));
}

#[tokio::test]
async fn docs_static_assets_render_operation_details_like_swagger_redoc() {
    let swagger_js_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let swagger_js_body = String::from_utf8(response_bytes(swagger_js_response).await.to_vec())
        .expect("swagger js text");

    assert!(swagger_js_body.contains("renderOperationDetails"));
    assert!(swagger_js_body.contains("operation.parameters"));
    assert!(swagger_js_body.contains("operation.requestBody"));
    assert!(swagger_js_body.contains("operation.responses"));
    assert!(swagger_js_body.contains("swagger-operation-parameters"));
    assert!(swagger_js_body.contains("swagger-operation-request-body"));
    assert!(swagger_js_body.contains("swagger-operation-responses"));

    let swagger_css_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let swagger_css_body = String::from_utf8(response_bytes(swagger_css_response).await.to_vec())
        .expect("swagger css text");

    assert!(swagger_css_body.contains("swagger-operation-details"));
    assert!(swagger_css_body.contains("swagger-operation-parameters"));
    assert!(swagger_css_body.contains("swagger-operation-request-body"));
    assert!(swagger_css_body.contains("swagger-operation-responses"));
    assert!(swagger_css_body.contains("redoc-operation-details"));
    assert!(swagger_css_body.contains("redoc-operation-parameters"));
    assert!(swagger_css_body.contains("redoc-operation-request-body"));
    assert!(swagger_css_body.contains("redoc-operation-responses"));

    let redoc_js_response =
        request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let redoc_js_body =
        String::from_utf8(response_bytes(redoc_js_response).await.to_vec()).expect("redoc js text");

    assert!(redoc_js_body.contains("renderOperationDetails"));
    assert!(redoc_js_body.contains("operation.parameters"));
    assert!(redoc_js_body.contains("operation.requestBody"));
    assert!(redoc_js_body.contains("operation.responses"));
    assert!(redoc_js_body.contains("redoc-operation-parameters"));
    assert!(redoc_js_body.contains("redoc-operation-request-body"));
    assert!(redoc_js_body.contains("redoc-operation-responses"));
}

#[tokio::test]
async fn docs_static_assets_filter_operations_like_swagger_redoc() {
    let swagger_js_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let swagger_js_body = String::from_utf8(response_bytes(swagger_js_response).await.to_vec())
        .expect("swagger js text");

    assert!(swagger_js_body.contains("filterOperations"));
    assert!(swagger_js_body.contains("docs-operation-filter"));
    assert!(swagger_js_body.contains("data-docs-search-text"));
    assert!(swagger_js_body.contains("No matching operations"));

    let swagger_css_response =
        request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let swagger_css_body = String::from_utf8(response_bytes(swagger_css_response).await.to_vec())
        .expect("swagger css text");

    assert!(swagger_css_body.contains("docs-operation-filter"));
    assert!(swagger_css_body.contains("docs-empty-message"));

    let redoc_js_response =
        request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let redoc_js_body =
        String::from_utf8(response_bytes(redoc_js_response).await.to_vec()).expect("redoc js text");

    assert!(redoc_js_body.contains("filterOperations"));
    assert!(redoc_js_body.contains("docs-operation-filter"));
    assert!(redoc_js_body.contains("data-docs-search-text"));
    assert!(redoc_js_body.contains("No matching operations"));
}

#[tokio::test]
async fn openapi_json_exposes_python_compatible_route_map() {
    let response = request_response(app_with_seed_data(), "GET", "/openapi.json").await;
    let status = response.status();
    let headers = response.headers().clone();
    let body = response_json(response).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "application/json");
    assert_eq!(body["openapi"], "3.1.0");
    assert_eq!(body["info"]["title"], "FastAPI");
    assert_eq!(body["info"]["version"], "0.1.0");

    let paths = body["paths"].as_object().expect("openapi paths object");
    for expected_path in [
        "/info",
        "/database_info",
        "/coilData/heightData/{surface_key}/{coil_id}",
        "/coilData/heightPoint/{surface_key}/{coil_id}",
        "/manual_defect/add",
        "/manual_defect/update/{defect_id}",
        "/manual_defect/delete/{defect_id}",
        "/sync_summaries",
        "/sync_summaries_range",
        "/coilAlarm/get_info",
        "/plc/info",
        "/plc/info/",
        "/plc/connect/{plc_ip}/{rack}/{slot}",
        "/plc/get/{addr}/{type_str}/{length}",
    ] {
        assert!(
            paths.contains_key(expected_path),
            "missing OpenAPI path {expected_path}"
        );
    }
    assert!(paths["/info"].get("get").is_some());
    assert!(paths["/manual_defect/add"].get("post").is_some());
    assert!(
        paths["/manual_defect/update/{defect_id}"]
            .get("put")
            .is_some()
    );
    assert!(
        paths["/manual_defect/delete/{defect_id}"]
            .get("delete")
            .is_some()
    );
    assert!(paths["/sync_summaries"].get("post").is_some());
    assert!(paths["/sync_summaries_range"].get("post").is_some());
    assert!(paths["/coilAlarm/get_info"].get("get").is_some());
}

#[tokio::test]
async fn openapi_json_describes_health_route_for_tauri_system_diagnostics() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(body["paths"]["/health"]["get"]["summary"], json!("Health"));
    assert_eq!(
        body["paths"]["/health"]["get"]["operationId"],
        json!("health_health_get")
    );
    assert_eq!(
        body["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/HealthResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["HealthResponse"],
        json!({
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "service": {"type": "string", "title": "Service"}
            },
            "type": "object",
            "required": ["status", "service"],
            "title": "HealthResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_preserves_python_basic_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(body["paths"]["/delay"]["get"]["summary"], "Get Delay");
    assert_eq!(
        body["paths"]["/database_info"]["get"],
        json!({
            "tags": ["参数服务"],
            "summary": "Database Info",
            "description": "获取数据库信息。",
            "operationId": "database_info_database_info_get",
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DatabaseInfoResponse"}
                        }
                    }
                }
            }
        })
    );
    assert_eq!(
        body["paths"]["/hardware"]["get"]["tags"],
        json!(["数据库服务"])
    );
    assert_eq!(body["paths"]["/hardware"]["get"]["summary"], "Get Hardware");
}

#[tokio::test]
async fn openapi_json_preserves_python_settings_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    for (path, method, tag, summary, description, operation_id) in [
        (
            "/control/config",
            "get",
            "参数控制服务",
            "Get Config",
            "控制配置获取",
            "get_config_control_config_get",
        ),
        (
            "/control/set_config",
            "post",
            "参数控制服务",
            "Set Config",
            "控制配置设置",
            "set_config_control_set_config_post",
        ),
        (
            "/control/set_property",
            "get",
            "参数控制服务",
            "Set Property",
            "控制配置设置",
            "set_property_control_set_property_get",
        ),
        (
            "/setDefectDict",
            "post",
            "参数设置",
            "Set Defect Dict",
            "设置缺陷字典",
            "set_defect_dict_setDefectDict_post",
        ),
        (
            "/settings/test_mode",
            "get",
            "参数设置",
            "Get Test Mode",
            "获取测试模式状态",
            "get_test_mode_settings_test_mode_get",
        ),
        (
            "/settings/test_mode",
            "post",
            "参数设置",
            "Set Test Mode",
            "设置测试模式状态",
            "set_test_mode_settings_test_mode_post",
        ),
        (
            "/settings/test_mode_status",
            "get",
            "参数设置",
            "Get Test Mode Status",
            "获取详细的测试模式状态信息",
            "get_test_mode_status_settings_test_mode_status_get",
        ),
    ] {
        let operation = &body["paths"][path][method];
        assert_eq!(operation["tags"], json!([tag]), "{method} {path} tags");
        assert_eq!(operation["summary"], summary, "{method} {path} summary");
        assert_eq!(
            operation["description"], description,
            "{method} {path} description"
        );
        assert_eq!(
            operation["operationId"], operation_id,
            "{method} {path} operationId"
        );
    }
}

#[tokio::test]
async fn openapi_json_preserves_python_core_data_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    for (path, tag, summary, description, operation_id) in [
        (
            "/coilList/{number}",
            "数据库服务",
            "Get Coil",
            Some(
                "获取 n 条数据（优先查询摘要表，快速返回）\n\n摘要表由算法检测结束时自动更新，确保数据一致性",
            ),
            "get_coil_coilList__number__get",
        ),
        (
            "/flush/{coil_id}",
            "数据库服务",
            "Get Flush",
            Some("向上刷新（仅查询摘要表，快速返回）"),
            "get_flush_flush__coil_id__get",
        ),
        (
            "/detail/{coil_id}",
            "数据库服务",
            "Get Coil Detail Api",
            Some(
                "获取卷材详情（完整数据）\n包括：基本信息、报警详情、缺陷列表、塔形点数据、松卷/扁卷报警等\n用于点击查看详情时调用",
            ),
            "get_coil_detail_api_detail__coil_id__get",
        ),
        (
            "/defectDict",
            "数据库服务",
            "Get Defect Dict",
            None,
            "get_defect_dict_defectDict_get",
        ),
        (
            "/defectDictAll",
            "数据库服务",
            "Get Defect Dict All",
            Some("获取全部的表面缺陷数据字段"),
            "get_defect_dict_all_defectDictAll_get",
        ),
        (
            "/data_has/{coil_id}",
            "参数服务",
            "Get Daa Has",
            None,
            "get_daa_has_data_has__coil_id__get",
        ),
        (
            "/coilInfo/{coil_id}/{surface_key}",
            "数据库服务",
            "Get Info",
            None,
            "get_info_coilInfo__coil_id___surface_key__get",
        ),
    ] {
        let operation = &body["paths"][path]["get"];
        assert_eq!(operation["tags"], json!([tag]), "GET {path} tags");
        assert_eq!(operation["summary"], summary, "GET {path} summary");
        match description {
            Some(description) => assert_eq!(
                operation["description"], description,
                "GET {path} description"
            ),
            None => assert!(
                operation.get("description").is_none(),
                "GET {path} description should be absent"
            ),
        }
        assert_eq!(
            operation["operationId"], operation_id,
            "GET {path} operationId"
        );
    }
}

#[tokio::test]
async fn openapi_json_preserves_python_search_measurement_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    for (path, summary, description, operation_id) in [
        (
            "/search/coilNo/{coil_no}",
            "Search By Coil No",
            None,
            "search_by_coil_no_search_coilNo__coil_no__get",
        ),
        (
            "/search/coilId/{coil_id}",
            "Search By Coil Id",
            None,
            "search_by_coil_id_search_coilId__coil_id__get",
        ),
        (
            "/search/DateTime/{start}/{end}",
            "Search By Date Time",
            None,
            "search_by_date_time_search_DateTime__start___end__get",
        ),
        (
            "/search/CoilState/{coil_id}",
            "Get Coil State",
            None,
            "get_coil_state_search_CoilState__coil_id__get",
        ),
        (
            "/search/PlcData/{coil_id}",
            "Get Plc Data",
            None,
            "get_plc_data_search_PlcData__coil_id__get",
        ),
        (
            "/get_point_data/{coil_id}/{surface_key}",
            "Get Point Data",
            Some("获取点数据"),
            "get_point_data_get_point_data__coil_id___surface_key__get",
        ),
        (
            "/get_line_data/{coil_id}/{surface_key}",
            "Get Line Data",
            None,
            "get_line_data_get_line_data__coil_id___surface_key__get",
        ),
        (
            "/plc_curve/{field}",
            "Get Plc Curve",
            None,
            "get_plc_curve_plc_curve__field__get",
        ),
        (
            "/plc_curve_all",
            "Get Plc Curve All",
            None,
            "get_plc_curve_all_plc_curve_all_get",
        ),
        (
            "/check/get_coil_status/{coil_id}",
            "Get Coil Status",
            None,
            "get_coil_status_check_get_coil_status__coil_id__get",
        ),
        (
            "/check/set_coil_status/{coil_id}/{status}",
            "Set Coil Status",
            None,
            "set_coil_status_check_set_coil_status__coil_id___status__get",
        ),
        (
            "/check/set_coil_status/{coil_id}/{status}/{msg}",
            "Set Coil Status",
            None,
            "set_coil_status_check_set_coil_status__coil_id___status___msg__get",
        ),
    ] {
        let operation = &body["paths"][path]["get"];
        assert_eq!(operation["tags"], json!(["数据库服务"]), "GET {path} tags");
        assert_eq!(operation["summary"], summary, "GET {path} summary");
        match description {
            Some(description) => assert_eq!(
                operation["description"], description,
                "GET {path} description"
            ),
            None => assert!(
                operation.get("description").is_none(),
                "GET {path} description should be absent"
            ),
        }
        assert_eq!(
            operation["operationId"], operation_id,
            "GET {path} operationId"
        );
    }
}

#[tokio::test]
async fn openapi_json_preserves_python_image_depth_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    let height_data_description = "Return line segments for curve display.\n\nThe UI expects:\n[\n  {\n    \"pointL\": [x0, y0],\n    \"pointR\": [x1, y1],\n    \"points\": [[x, y, z], ...]\n  },\n  ...\n]";
    let render_description = "获取渲染图像（支持伪彩色 JET 和灰度 GRAY）\n\n参数:\n- thumbnail=true: 返回缓存的缩略图（快速加载）\n- thumbnail=false: 返回完整渲染图像\n- grayscale=true: 返回灰度图像（GRAY.jpg 缓存）\n- grayscale=false: 返回伪彩色图像（JET.jpg 缓存）";
    let error_description = "获取 Error 塔形报警图像\n\n计算方法（与预生成缓存一致）：\n- 蓝色：低于 中位数 - minValue mm（塔形过小，远离侧）\n- 红色：高于 中位数 + maxValue mm（塔形过大，靠近侧）\n\n优先从 AlgServer 预生成的缓存读取 (png/Error.png)\n如果缓存不存在且 force_cache=False，则动态生成";
    let tiled_area_description = "多级瓦片加载接口\n\n参数说明:\n- row=-1: 返回完整图像\n- row=-2: 返回预览图像\n- count=0: 返回图像宽高信息\n- level: 瓦片质量等级 (0=缩略图 1/16, 1=1/8, 2=1/4, 3=1/2, 4=原图)\n\n瓦片等级:\n- Level 0: 340x340, JPEG 60 (~20KB)\n- Level 1: 682x682, JPEG 70 (~50KB)\n- Level 2: 1364x1364, JPEG 80 (~120KB)\n- Level 3: 2728x2728, JPEG 90 (~250KB)\n- Level 4: 5460x5460, JPEG 95 (~500KB)\n\n缓存策略:\n- 优先从缓存读取对应级别的瓦片（直接返回，速度最快）\n- 缓存不存在时，生成所有级别的瓦片并保存";

    for (path, tag, summary, description, operation_id) in [
        (
            "/coilData/heightData/{surface_key}/{coil_id}",
            "深度数据访问服务",
            "Get Height Data",
            Some(height_data_description),
            "get_height_data_coilData_heightData__surface_key___coil_id__get",
        ),
        (
            "/coilData/heightPoint/{surface_key}/{coil_id}",
            "深度数据访问服务",
            "Get Height Point",
            None,
            "get_height_point_coilData_heightPoint__surface_key___coil_id__get",
        ),
        (
            "/coilData/Render/{surfaceKey}/{coil_id}",
            "深度数据访问服务",
            "Getrender",
            Some(render_description),
            "getRender_coilData_Render__surfaceKey___coil_id__get",
        ),
        (
            "/coilData/Area/{surface_key}/{coil_id}",
            "深度数据访问服务",
            "Get Area",
            None,
            "get_area_coilData_Area__surface_key___coil_id__get",
        ),
        (
            "/coilData/Error/{surface_key}/{coil_id}",
            "深度数据访问服务",
            "Get Error",
            Some(error_description),
            "get_error_coilData_Error__surface_key___coil_id__get",
        ),
        (
            "/image/preview/{surface_key}/{coil_id}/{type_}",
            "图像访问服务",
            "Get Preview Image",
            None,
            "get_preview_image_image_preview__surface_key___coil_id___type___get",
        ),
        (
            "/image/source/{surface_key}/{coil_id}/{type_}",
            "图像访问服务",
            "Get Image",
            Some("增加 2D 影像"),
            "get_image_image_source__surface_key___coil_id___type___get",
        ),
        (
            "/image/area/{surface_key}/{coil_id}",
            "图像访问服务",
            "Get Area Tiled",
            Some(tiled_area_description),
            "get_area_tiled_image_area__surface_key___coil_id__get",
        ),
        (
            "/image/area/{surface_key}/{coil_id}/{type_}",
            "图像访问服务",
            "Get Area Tiled",
            Some(tiled_area_description),
            "get_area_tiled_image_area__surface_key___coil_id___type___get",
        ),
        (
            "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
            "深度数据访问服务",
            "Get Classifier Image",
            None,
            "get_classifier_image_classifier_image__coil_id___surface_key___class_name___x___y___w___h__get",
        ),
        (
            "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
            "图像访问服务",
            "Get Defect Image",
            None,
            "get_defect_image_defect_image__surface_key___coil_id___type____x___y___w___h__get",
        ),
    ] {
        let operation = &body["paths"][path]["get"];
        assert_eq!(operation["tags"], json!([tag]), "GET {path} tags");
        assert_eq!(operation["summary"], summary, "GET {path} summary");
        match description {
            Some(description) => assert_eq!(
                operation["description"], description,
                "GET {path} description"
            ),
            None => assert!(
                operation.get("description").is_none(),
                "GET {path} description should be absent"
            ),
        }
        assert_eq!(
            operation["operationId"], operation_id,
            "GET {path} operationId"
        );
    }
}

#[tokio::test]
async fn openapi_json_preserves_python_path_parameter_names() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    let assert_path_params = |path: &str, names: &[&str]| {
        let parameters = body["paths"][path]["get"]["parameters"]
            .as_array()
            .expect("path parameters");
        let path_params: Vec<&str> = parameters
            .iter()
            .filter(|param| param["in"] == "path")
            .map(|param| {
                param["name"]
                    .as_str()
                    .expect("path parameter name")
            })
            .collect();
        assert_eq!(path_params, names, "path parameter names for {path}");
    };

    assert_path_params("/coilInfo/{coil_id}/{surface_key}", &["coil_id", "surface_key"]);
    assert_path_params("/search/defects/{coil_id}/{direction}", &["coil_id", "direction"]);
    assert_path_params(
        "/search/defects_all/{coil_id}/{direction}",
        &["coil_id", "direction"],
    );
    assert_path_params(
        "/manual_defects/{coil_id}/{direction}",
        &["coil_id", "direction"],
    );
    assert_path_params("/get_point_data/{coil_id}/{surface_key}", &["coil_id", "surface_key"]);
    assert_path_params("/get_line_data/{coil_id}/{surface_key}", &["coil_id", "surface_key"]);
    assert_path_params(
        "/coilData/heightData/{surface_key}/{coil_id}",
        &["surface_key", "coil_id"],
    );
    assert_path_params(
        "/coilData/heightPoint/{surface_key}/{coil_id}",
        &["surface_key", "coil_id"],
    );
    assert_path_params("/coilData/Render/{surfaceKey}/{coil_id}", &["surfaceKey", "coil_id"]);
    assert_path_params("/coilData/Area/{surface_key}/{coil_id}", &["surface_key", "coil_id"]);
    assert_path_params("/coilData/Error/{surface_key}/{coil_id}", &["surface_key", "coil_id"]);
    assert_path_params(
        "/image/preview/{surface_key}/{coil_id}/{type_}",
        &["surface_key", "coil_id", "type_"],
    );
    assert_path_params(
        "/image/source/{surface_key}/{coil_id}/{type_}",
        &["surface_key", "coil_id", "type_"],
    );
    assert_path_params("/image/area/{surface_key}/{coil_id}", &["surface_key", "coil_id"]);
    assert_path_params(
        "/image/area/{surface_key}/{coil_id}/{type_}",
        &["surface_key", "coil_id", "type_"],
    );
    assert_path_params(
        "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
        &["coil_id", "surface_key", "class_name", "x", "y", "w", "h"],
    );
    assert_path_params(
        "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
        &["surface_key", "coil_id", "type_", "x", "y", "w", "h"],
    );
    assert_path_params("/clipMaxImage/{coil_id}/{key}", &["coil_id", "key"]);
    assert_path_params(
        "/plc/connect/{plc_ip}/{rack}/{slot}",
        &["plc_ip", "rack", "slot"],
    );
    assert_path_params(
        "/plc/get/{addr}/{type_str}/{length}",
        &["addr", "type_str", "length"],
    );
}

#[tokio::test]
async fn openapi_json_preserves_remaining_python_operation_metadata() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    let runtime_info_description = "运行环境信息：Python 版本、缓存模式、CPU/GPU 型号等，\n以及当前 3D 服务的运行模式（本地 / 开发者模式）。";
    let sync_summaries_description = "手动触发批量同步摘要数据\n用于初始化摘要表";
    let sync_summaries_range_description = "快速同步指定 ID 范围的摘要数据\n只更新已存在的记录，不创建新记录\n主要用于更新 DefectCountS/L 和 MaxDefect 字段";
    let defects_all_description = "获取所有缺陷（包括自动检测和手动标注）\n\nArgs:\n    coil_id: 二级卷ID\n    direction: 表面标识（S/L）\n\nReturns:\n    包含自动检测缺陷和手动标注缺陷的列表";
    let manual_defects_description = "获取手动标注的缺陷列表\n\nArgs:\n    coil_id: 二级卷ID\n    direction: 表面标识（S/L）\n\nReturns:\n    手动标注缺陷列表";
    let manual_add_description = "添加手动标注的缺陷\n\nArgs:\n    request: 缺陷数据字典，包含：\n        - secondaryCoilId: 二级卷ID\n        - surface: 表面标识（S/L）\n        - defectName: 缺陷名称\n        - defectX: X坐标\n        - defectY: Y坐标\n        - defectW: 宽度\n        - defectH: 高度\n        - remark: 备注（可选）\n        - annotator: 标注人（可选）\n\nReturns:\n    创建的缺陷数据";
    let manual_update_description = "更新手动标注的缺陷\n\nArgs:\n    defect_id: 缺陷ID\n    request: 更新的数据字典\n\nReturns:\n    更新后的缺陷数据，如果不存在返回错误";
    let manual_delete_description =
        "删除手动标注的缺陷\n\nArgs:\n    defect_id: 缺陷ID\n\nReturns:\n    删除结果";
    let export_defects_description = "导出当前显示的缺陷图像到本地文件夹\n\nArgs:\n    request: 包含 defects（缺陷列表）和 folder_path（导出路径）的字典\n\nReturns:\n    导出结果统计";

    for (method, path, tag, summary, description, operation_id) in [
        ("get", "/", None, "Read Root", None, "read_root__get"),
        (
            "get",
            "/currentCoil",
            None,
            "Read Root",
            None,
            "read_root_currentCoil_get",
        ),
        (
            "get",
            "/version",
            None,
            "Read Version",
            None,
            "read_version_version_get",
        ),
        (
            "get",
            "/delay",
            None,
            "Get Delay",
            None,
            "get_delay_delay_get",
        ),
        (
            "get",
            "/info",
            Some("参数服务"),
            "Info",
            None,
            "info_info_get",
        ),
        (
            "get",
            "/runtime_info",
            Some("参数服务"),
            "Runtime Info",
            Some(runtime_info_description),
            "runtime_info_runtime_info_get",
        ),
        (
            "get",
            "/grader_list",
            Some("参数服务"),
            "Grader List",
            None,
            "grader_list_grader_list_get",
        ),
        (
            "get",
            "/coil_list_value_change_keys",
            Some("参数服务"),
            "Coil List Value Change Keys",
            None,
            "coil_list_value_change_keys_coil_list_value_change_keys_get",
        ),
        (
            "get",
            "/search/defects/{coil_id}/{direction}",
            Some("数据库服务"),
            "Get Defects",
            None,
            "get_defects_search_defects__coil_id___direction__get",
        ),
        (
            "get",
            "/search/getDefectAll/{start_coil_id}/{end_coil_id}",
            Some("数据库服务"),
            "Get Defect All",
            None,
            "get_defect_all_search_getDefectAll__start_coil_id___end_coil_id__get",
        ),
        (
            "get",
            "/hardware",
            Some("数据库服务"),
            "Get Hardware",
            None,
            "get_hardware_hardware_get",
        ),
        (
            "get",
            "/camera_adjust",
            Some("数据库服务"),
            "Get Camera Adjustments",
            None,
            "get_camera_adjustments_camera_adjust_get",
        ),
        (
            "post",
            "/camera_adjust/{camera_key}",
            Some("数据库服务"),
            "Set Camera Adjustment",
            None,
            "set_camera_adjustment_camera_adjust__camera_key__post",
        ),
        (
            "post",
            "/camera_adjust/{camera_key}/reconnect",
            Some("数据库服务"),
            "Reconnect Camera Adjustment",
            None,
            "reconnect_camera_adjustment_camera_adjust__camera_key__reconnect_post",
        ),
        (
            "get",
            "/capture_status",
            Some("数据库服务"),
            "Get Capture Status",
            None,
            "get_capture_status_capture_status_get",
        ),
        (
            "get",
            "/cameraAlarm",
            Some("数据库服务"),
            "Get Camera Alarm",
            Some("获取相机报警信息\nReturns:"),
            "get_camera_alarm_cameraAlarm_get",
        ),
        (
            "get",
            "/cameraData/{coil_id}/{camera_key}",
            Some("数据库服务"),
            "Get Camera Data",
            None,
            "get_camera_data_cameraData__coil_id___camera_key__get",
        ),
        (
            "get",
            "/backupImageTask/{from_id}/{to_id}/{save_folder}",
            Some("数据库服务"),
            "Backup Image Task",
            None,
            "backup_image_task_backupImageTask__from_id___to_id___save_folder__get",
        ),
        (
            "post",
            "/sync_summaries",
            Some("数据库服务"),
            "Sync Summaries Api",
            Some(sync_summaries_description),
            "sync_summaries_api_sync_summaries_post",
        ),
        (
            "post",
            "/sync_summaries_range",
            Some("数据库服务"),
            "Sync Summaries Range Api",
            Some(sync_summaries_range_description),
            "sync_summaries_range_api_sync_summaries_range_post",
        ),
        (
            "get",
            "/search/defects_all/{coil_id}/{direction}",
            Some("数据库服务"),
            "Get Defects All Including Manual",
            Some(defects_all_description),
            "get_defects_all_including_manual_search_defects_all__coil_id___direction__get",
        ),
        (
            "get",
            "/manual_defects/{coil_id}/{direction}",
            Some("数据库服务"),
            "Get Manual Defects Api",
            Some(manual_defects_description),
            "get_manual_defects_api_manual_defects__coil_id___direction__get",
        ),
        (
            "post",
            "/manual_defect/add",
            Some("数据库服务"),
            "Add Manual Defect Api",
            Some(manual_add_description),
            "add_manual_defect_api_manual_defect_add_post",
        ),
        (
            "put",
            "/manual_defect/update/{defect_id}",
            Some("数据库服务"),
            "Update Manual Defect Api",
            Some(manual_update_description),
            "update_manual_defect_api_manual_defect_update__defect_id__put",
        ),
        (
            "delete",
            "/manual_defect/delete/{defect_id}",
            Some("数据库服务"),
            "Delete Manual Defect Api",
            Some(manual_delete_description),
            "delete_manual_defect_api_manual_defect_delete__defect_id__delete",
        ),
        (
            "post",
            "/export_defects",
            Some("数据库服务"),
            "Export Defects",
            Some(export_defects_description),
            "export_defects_export_defects_post",
        ),
        (
            "get",
            "/save_to_sql/{sql_file}",
            Some("备份服务"),
            "Save To Sql",
            None,
            "save_to_sql_save_to_sql__sql_file__get",
        ),
        (
            "get",
            "/exportXlsxById/{start}/{end}",
            Some("备份服务"),
            "Export Xlsx By Id",
            None,
            "export_xlsx_by_id_exportXlsxById__start___end__get",
        ),
        (
            "get",
            "/exportXlsxByDateTime/{start}/{end}",
            Some("备份服务"),
            "Export Xlsx By Datetime",
            None,
            "export_xlsx_by_datetime_exportXlsxByDateTime__start___end__get",
        ),
        (
            "post",
            "/export_xlsx",
            Some("备份服务"),
            "Export Xlsx Post",
            None,
            "export_xlsx_post_export_xlsx_post",
        ),
        (
            "get",
            "/exportDataSimple",
            Some("备份服务"),
            "Export Data Simple",
            None,
            "export_data_simple_exportDataSimple_get",
        ),
        (
            "get",
            "/export_1h",
            Some("备份服务"),
            "Export Last 1H",
            None,
            "export_last_1h_export_1h_get",
        ),
        (
            "post",
            "/export_1h",
            Some("备份服务"),
            "Export Last 1H Post",
            None,
            "export_last_1h_post_export_1h_post",
        ),
        (
            "get",
            "/export_24h",
            Some("备份服务"),
            "Export Last 24H",
            None,
            "export_last_24h_export_24h_get",
        ),
        (
            "post",
            "/export_24h",
            Some("备份服务"),
            "Export Last 24H Post",
            None,
            "export_last_24h_post_export_24h_post",
        ),
        (
            "get",
            "/export_today",
            Some("备份服务"),
            "Export Today",
            None,
            "export_today_export_today_get",
        ),
        (
            "post",
            "/export_today",
            Some("备份服务"),
            "Export Today Post",
            None,
            "export_today_post_export_today_post",
        ),
        (
            "get",
            "/download_test",
            Some("测试服务"),
            "Download File",
            None,
            "download_file_download_test_get",
        ),
        (
            "get",
            "/speedtest/download",
            Some("测试服务"),
            "Download Test",
            Some("生成一个指定大小的文件流，单位是MB（默认为10MB）\n访问此接口可测试下载速度。"),
            "download_test_speedtest_download_get",
        ),
        (
            "post",
            "/speedtest/upload",
            Some("测试服务"),
            "Upload Test",
            Some("接收文件并记录上传时间。\n访问此接口上传文件可测试上传速度。"),
            "upload_test_speedtest_upload_post",
        ),
        (
            "get",
            "/coilAlarm/get_info",
            Some("报警、判级"),
            "Get Info",
            Some("获取报警信息\nReturns:"),
            "get_info_coilAlarm_get_info_get",
        ),
        (
            "get",
            "/coilAlarm/{coil_id}",
            Some("报警、判级"),
            "Get Coil Alarm",
            Some("返回全部的警告数据\nArgs:\n    coil_id:\n\nReturns:"),
            "get_coil_alarm_coilAlarm__coil_id__get",
        ),
        (
            "get",
            "/alg_2d/models",
            Some("算法测试"),
            "List Alg Models",
            Some("获取可用的算法模型列表"),
            "list_alg_models_alg_2d_models_get",
        ),
        (
            "post",
            "/alg_2d/test/start",
            Some("算法测试"),
            "Start Alg Test",
            None,
            "start_alg_test_alg_2d_test_start_post",
        ),
        (
            "post",
            "/alg_2d/test/stop",
            Some("算法测试"),
            "Stop Alg Test",
            None,
            "stop_alg_test_alg_2d_test_stop_post",
        ),
        (
            "get",
            "/reDetection/start/{from_id}/{to_id}",
            Some("算法服务-与算法同步运行"),
            "Http Re Detection Start",
            Some("通过 HTTP 启动重新识别任务，指定起止 SecondaryCoilId。"),
            "http_re_detection_start_reDetection_start__from_id___to_id__get",
        ),
        (
            "get",
            "/reDetection/status",
            Some("算法服务-与算法同步运行"),
            "Http Re Detection Status",
            Some("获取当前重新识别任务进度。"),
            "http_re_detection_status_reDetection_status_get",
        ),
        (
            "get",
            "/getServerState",
            Some("算法服务-与算法同步运行"),
            "Get Server State",
            None,
            "get_server_state_getServerState_get",
        ),
    ] {
        let operation = &body["paths"][path][method];
        match tag {
            Some(tag) => assert_eq!(operation["tags"], json!([tag]), "{method} {path} tags"),
            None => assert!(
                operation.get("tags").is_none(),
                "{method} {path} tags should be absent"
            ),
        }
        assert_eq!(operation["summary"], summary, "{method} {path} summary");
        match description {
            Some(description) => assert_eq!(
                operation["description"], description,
                "{method} {path} description"
            ),
            None => assert!(
                operation.get("description").is_none(),
                "{method} {path} description should be absent"
            ),
        }
        assert_eq!(
            operation["operationId"], operation_id,
            "{method} {path} operationId"
        );
    }
}

#[tokio::test]
async fn openapi_json_describes_height_routes_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let height_data = &body["paths"]["/coilData/heightData/{surface_key}/{coil_id}"]["get"];
    let height_point = &body["paths"]["/coilData/heightPoint/{surface_key}/{coil_id}"]["get"];

    assert_eq!(
        height_data["parameters"],
        json!([
            {
                "name": "surface_key",
                "in": "path",
                "required": true,
                "schema": {"title": "Surface Key"}
            },
            {
                "name": "coil_id",
                "in": "path",
                "required": true,
                "schema": {"type": "string", "title": "Coil Id"}
            },
            {
                "name": "x1",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "X1"}
            },
            {
                "name": "y1",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "Y1"}
            },
            {
                "name": "x2",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "X2"}
            },
            {
                "name": "y2",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "Y2"}
            }
        ])
    );
    assert_eq!(
        height_point["parameters"],
        json!([
            {
                "name": "surface_key",
                "in": "path",
                "required": true,
                "schema": {"title": "Surface Key"}
            },
            {
                "name": "coil_id",
                "in": "path",
                "required": true,
                "schema": {"type": "string", "title": "Coil Id"}
            },
            {
                "name": "x",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "X"}
            },
            {
                "name": "y",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "Y"}
            }
        ])
    );
    for operation in [height_data, height_point] {
        assert_eq!(
            operation["responses"]["422"],
            json!({
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                    }
                }
            })
        );
    }
    assert_eq!(
        body["components"]["schemas"]["HTTPValidationError"],
        json!({
            "properties": {
                "detail": {
                    "items": {"$ref": "#/components/schemas/ValidationError"},
                    "type": "array",
                    "title": "Detail"
                }
            },
            "type": "object",
            "title": "HTTPValidationError"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["ValidationError"],
        json!({
            "properties": {
                "loc": {
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "integer"}
                        ]
                    },
                    "type": "array",
                    "title": "Location"
                },
                "msg": {"type": "string", "title": "Message"},
                "type": {"type": "string", "title": "Error Type"},
                "input": {"title": "Input"},
                "ctx": {"type": "object", "title": "Context"}
            },
            "type": "object",
            "required": ["loc", "msg", "type"],
            "title": "ValidationError"
        })
    );
}

#[tokio::test]
async fn sync_summary_routes_return_python_compatible_bodies() {
    let app = app_with_seed_data();

    let sync_response = request_response(app.clone(), "POST", "/sync_summaries?limit=100").await;
    assert_eq!(sync_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(sync_response).await,
        json!({"synced": 0, "message": "Synced 0 summaries"})
    );

    let missing_ids_response =
        request_json_body(app.clone(), "POST", "/sync_summaries_range", json!({})).await;
    assert_eq!(missing_ids_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(missing_ids_response).await,
        json!({"error": "coil_ids is required", "synced": 0})
    );

    let range_response = request_json_body(
        app,
        "POST",
        "/sync_summaries_range",
        json!({"coil_ids": [42, 404]}),
    )
    .await;
    assert_eq!(range_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(range_response).await,
        json!({"synced": 1, "message": "Updated 1 summaries"})
    );
}

#[tokio::test]
async fn sync_summaries_range_recalculates_existing_summary_counts_and_max_defect() {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 77,
            coil_no: "LG-20260629-0077".to_string(),
            create_time: Some("2026-06-29 08:00:00".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 0,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 0,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-29 08:01:00".to_string()),
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: Some("旧缺陷".to_string()),
            max_defect_level: 1,
            max_defect_surface: Some("S".to_string()),
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_defects(vec![
            CoilDefectRow {
                id: 701,
                secondary_coil_id: 77,
                surface: "S".to_string(),
                defect_class: 1,
                defect_name: "压痕".to_string(),
                defect_status: 0,
                defect_time: None,
                defect_x: 10,
                defect_y: 20,
                defect_w: 30,
                defect_h: 40,
                defect_source: 0.9,
                defect_data: None,
            },
            CoilDefectRow {
                id: 702,
                secondary_coil_id: 77,
                surface: "L".to_string(),
                defect_class: 2,
                defect_name: "隐藏缺陷".to_string(),
                defect_status: 0,
                defect_time: None,
                defect_x: 11,
                defect_y: 21,
                defect_w: 31,
                defect_h: 41,
                defect_source: 0.8,
                defect_data: None,
            },
            CoilDefectRow {
                id: 703,
                secondary_coil_id: 77,
                surface: "L".to_string(),
                defect_class: 3,
                defect_name: "严重擦伤".to_string(),
                defect_status: 0,
                defect_time: None,
                defect_x: 12,
                defect_y: 22,
                defect_w: 32,
                defect_h: 42,
                defect_source: 0.7,
                defect_data: None,
            },
        ])
        .with_defect_classes(vec![
            DefectClassDictRow {
                id: 1,
                defect_class: 1,
                defect_name: "压痕".to_string(),
                defect_type: Some("surface".to_string()),
                defect_color: None,
                defect_level: Some(2),
                visible: Some(1),
                defect_desc: None,
            },
            DefectClassDictRow {
                id: 2,
                defect_class: 2,
                defect_name: "隐藏缺陷".to_string(),
                defect_type: Some("surface".to_string()),
                defect_color: None,
                defect_level: Some(5),
                visible: Some(0),
                defect_desc: None,
            },
            DefectClassDictRow {
                id: 3,
                defect_class: 3,
                defect_name: "严重擦伤".to_string(),
                defect_type: Some("surface".to_string()),
                defect_color: None,
                defect_level: Some(4),
                visible: Some(1),
                defect_desc: None,
            },
        ]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let response = request_json_body(
        app.clone(),
        "POST",
        "/sync_summaries_range",
        json!({"coil_ids": [77, 404]}),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        response_json(response).await,
        json!({"synced": 1, "message": "Updated 1 summaries"})
    );

    let (status, body) = request_json(app, "GET", "/coilList/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body[0]["DefectCountS"], 1);
    assert_eq!(body[0]["DefectCountL"], 2);
    assert_eq!(body[0]["maxDefectName"], "严重擦伤");
    assert_eq!(body[0]["maxDefectLevel"], 4);
    assert_eq!(body[0]["maxDefectSurface"], "L");
}

#[tokio::test]
async fn sync_summaries_creates_missing_summary_rows_from_detected_coils() {
    let repository = InMemoryCoilRepository::new()
        .with_detected_coils(vec![CoilSummaryRow {
            id: 88,
            coil_no: "LG-20260629-0088".to_string(),
            create_time: Some("2026-06-29 09:00:00".to_string()),
            coil_type: Some("Q345".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1400.0),
            thickness: Some(3.2),
            width: Some(1500.0),
            weight: Some(72.0),
            act_width: Some(1498.0),
            next_code: Some("B".to_string()),
            next_info: Some("后续工序".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 2,
            l_taper_shape_grad: 2,
            l_loose_coil_grad: 2,
            l_flat_roll_grad: 2,
            l_grad: 2,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-29 09:05:00".to_string()),
            check_status: 1,
            status_l: 2,
            status_s: 1,
            grade: 2,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_defects(vec![CoilDefectRow {
            id: 881,
            secondary_coil_id: 88,
            surface: "S".to_string(),
            defect_class: 1,
            defect_name: "压痕".to_string(),
            defect_status: 0,
            defect_time: None,
            defect_x: 10,
            defect_y: 20,
            defect_w: 30,
            defect_h: 40,
            defect_source: 0.9,
            defect_data: None,
        }])
        .with_defect_classes(vec![DefectClassDictRow {
            id: 1,
            defect_class: 1,
            defect_name: "压痕".to_string(),
            defect_type: Some("surface".to_string()),
            defect_color: None,
            defect_level: Some(3),
            visible: Some(1),
            defect_desc: None,
        }]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let sync_response = request_response(app.clone(), "POST", "/sync_summaries?limit=100").await;
    assert_eq!(sync_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(sync_response).await,
        json!({"synced": 1, "message": "Synced 1 summaries"})
    );

    let (status, body) = request_json(app, "GET", "/coilList/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body[0]["Id"], 88);
    assert_eq!(body[0]["CoilNo"], "LG-20260629-0088");
    assert_eq!(body[0]["DefectCountS"], 1);
    assert_eq!(body[0]["DefectCountL"], 0);
    assert_eq!(body[0]["maxDefectName"], "压痕");
    assert_eq!(body[0]["maxDefectLevel"], 3);
    assert_eq!(body[0]["childrenCoil"][0]["SecondaryCoilId"], 88);
}

#[tokio::test]
async fn sync_summaries_creates_missing_summary_rows_with_alarm_grades_and_next_text() {
    let repository = InMemoryCoilRepository::new()
        .with_detected_coils(vec![CoilSummaryRow {
            id: 89,
            coil_no: "LG-20260629-0089".to_string(),
            create_time: Some("2026-06-29 10:00:00".to_string()),
            coil_type: Some("Q345".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1400.0),
            thickness: Some(3.2),
            width: Some(1500.0),
            weight: Some(72.0),
            act_width: Some(1498.0),
            next_code: None,
            next_info: None,
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-29 10:05:00".to_string()),
            check_status: 1,
            status_l: 2,
            status_s: 1,
            grade: 2,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_alarm_infos(vec![
            AlarmInfoSummaryRow {
                id: 201,
                secondary_coil_id: 89,
                surface: "S".to_string(),
                next_code: Some("A".to_string()),
                next_name: Some("酸洗".to_string()),
                taper_shape_msg: Some("S塔形报警".to_string()),
                loose_coil_msg: Some("".to_string()),
                flat_roll_msg: Some("S扁卷报警".to_string()),
                defect_msg: Some("S缺陷报警".to_string()),
                defect_grad: 2,
                taper_shape_grad: 4,
                loose_coil_grad: 1,
                flat_roll_grad: 3,
                grad: 0,
                create_time: Some("2026-06-29 10:06:00".to_string()),
                data: None,
            },
            AlarmInfoSummaryRow {
                id: 202,
                secondary_coil_id: 89,
                surface: "L".to_string(),
                next_code: Some("B".to_string()),
                next_name: Some("冷轧".to_string()),
                taper_shape_msg: Some("".to_string()),
                loose_coil_msg: Some("L松卷报警".to_string()),
                flat_roll_msg: Some("".to_string()),
                defect_msg: Some("".to_string()),
                defect_grad: 1,
                taper_shape_grad: 1,
                loose_coil_grad: 5,
                flat_roll_grad: 1,
                grad: 5,
                create_time: Some("2026-06-29 10:07:00".to_string()),
                data: Some("{\"alarm\":true}".to_string()),
            },
        ]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let sync_response = request_response(app.clone(), "POST", "/sync_summaries?limit=100").await;
    assert_eq!(sync_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(sync_response).await,
        json!({"synced": 1, "message": "Synced 1 summaries"})
    );

    let (status, body) = request_json(app, "GET", "/coilList/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body[0]["hasAlarmInfo"], true);
    assert_eq!(body[0]["NextCode"], "A");
    assert_eq!(body[0]["NextInfo"], "酸洗");
    assert_eq!(body[0]["AlarmInfo"]["S"]["defectGrad"], 2);
    assert_eq!(body[0]["AlarmInfo"]["S"]["taperShapeGrad"], 4);
    assert_eq!(body[0]["AlarmInfo"]["S"]["looseCoilGrad"], 1);
    assert_eq!(body[0]["AlarmInfo"]["S"]["flatRollGrad"], 3);
    assert_eq!(body[0]["AlarmInfo"]["S"]["grad"], 4);
    assert_eq!(body[0]["AlarmInfo"]["S"]["nextCode"], "A");
    assert_eq!(body[0]["AlarmInfo"]["S"]["nextName"], "酸洗");
    assert_eq!(body[0]["AlarmInfo"]["L"]["grad"], 5);
    assert_eq!(body[0]["AlarmInfo"]["L"]["nextCode"], "B");
    assert_eq!(body[0]["AlarmInfo"]["L"]["nextName"], "冷轧");
}

#[tokio::test]
async fn sync_summaries_preserves_per_surface_alarm_flags_in_sqlite_snapshot() {
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("snapshot temp root");
    let db_path = root.join("single_surface_alarm_snapshot.db");
    let db_uri = db_path.to_string_lossy().replace('\\', "/");
    let repository = InMemoryCoilRepository::new()
        .with_detected_coils(vec![CoilSummaryRow {
            id: 90,
            coil_no: "LG-20260629-0090".to_string(),
            create_time: Some("2026-06-29 11:00:00".to_string()),
            coil_type: Some("Q345".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1400.0),
            thickness: Some(3.2),
            width: Some(1500.0),
            weight: Some(72.0),
            act_width: Some(1498.0),
            next_code: None,
            next_info: None,
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-29 11:05:00".to_string()),
            check_status: 1,
            status_l: 2,
            status_s: 1,
            grade: 2,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_alarm_infos(vec![AlarmInfoSummaryRow {
            id: 203,
            secondary_coil_id: 90,
            surface: "S".to_string(),
            next_code: Some("A".to_string()),
            next_name: Some("酸洗".to_string()),
            taper_shape_msg: Some("".to_string()),
            loose_coil_msg: Some("".to_string()),
            flat_roll_msg: Some("".to_string()),
            defect_msg: Some("".to_string()),
            defect_grad: 2,
            taper_shape_grad: 3,
            loose_coil_grad: 1,
            flat_roll_grad: 1,
            grad: 3,
            create_time: Some("2026-06-29 11:06:00".to_string()),
            data: None,
        }]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let sync_response = request_response(app.clone(), "POST", "/sync_summaries?limit=100").await;
    assert_eq!(sync_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(sync_response).await,
        json!({"synced": 1, "message": "Synced 1 summaries"})
    );

    let snapshot_response = request_response(app, "GET", &format!("/save_to_sql/{db_uri}")).await;
    assert_eq!(snapshot_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(snapshot_response).await,
        json!({"state": true})
    );
    let sqlite = rusqlite::Connection::open(&db_path).expect("open sqlite snapshot");
    let (s_has_alarm, l_has_alarm): (i64, i64) = sqlite
        .query_row(
            "SELECT S_HasAlarm, L_HasAlarm FROM coil_summary WHERE Id = 90",
            [],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .expect("summary alarm flags");
    assert_eq!(s_has_alarm, 1);
    assert_eq!(l_has_alarm, 0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn sync_summaries_invalid_limit_returns_fastapi_query_validation_error() {
    let response =
        request_response(app_with_seed_data(), "POST", "/sync_summaries?limit=abc").await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn sync_summaries_negative_limit_returns_python_internal_error() {
    let response = request_response(app_with_seed_data(), "POST", "/sync_summaries?limit=-1").await;

    assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    assert_eq!(
        response_bytes(response).await.as_ref(),
        b"Internal Server Error"
    );
}

#[tokio::test]
async fn control_routes_read_and_update_python_compatible_runtime_config() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("control temp dir");
    let control_path = root.join("Control.json");
    fs::write(
        &control_path,
        r#"{"save_detection":true,"lower_limit":-75,"upper_limit":75}"#,
    )
    .expect("write control config");
    let _control_guard = set_env_var_guard("RUST_API_CONTROL_CONFIG", &control_path);

    let app = app_with_seed_data();
    let initial_response = request_response(app.clone(), "GET", "/control/config").await;
    let status = initial_response.status();

    assert_eq!(status, StatusCode::OK);
    let initial = response_json(initial_response).await;
    assert_eq!(initial["save_detection"], true);
    assert_eq!(initial["lower_limit"], -75);
    assert_eq!(initial["upper_limit"], 75);

    let update_response = request_json_body(
        app.clone(),
        "POST",
        "/control/set_config",
        json!({
            "save_detection": false,
            "upper_limit": 90,
            "runtime_note": "from-test",
        }),
    )
    .await;

    assert_eq!(update_response.status(), StatusCode::OK);
    assert_eq!(response_json(update_response).await, Value::Null);

    let updated_response = request_response(app.clone(), "GET", "/control/config").await;
    let status = updated_response.status();

    assert_eq!(status, StatusCode::OK);
    let updated = response_json(updated_response).await;
    assert_eq!(updated["save_detection"], false);
    assert_eq!(updated["lower_limit"], -75);
    assert_eq!(updated["upper_limit"], 90);
    assert_eq!(updated["runtime_note"], "from-test");

    let property_response = request_response(
        app.clone(),
        "GET",
        "/control/set_property?key=lower_limit&value=-64.5",
    )
    .await;

    assert_eq!(property_response.status(), StatusCode::OK);
    assert_eq!(response_json(property_response).await, Value::Null);

    let final_response = request_response(app, "GET", "/control/config").await;
    let status = final_response.status();

    assert_eq!(status, StatusCode::OK);
    let final_config = response_json(final_response).await;
    assert_eq!(final_config["lower_limit"], "-64.5");

    let persisted =
        serde_json::from_str::<Value>(&fs::read_to_string(&control_path).expect("control config"))
            .expect("persisted control json");
    assert_eq!(persisted["save_detection"], true);
    assert_eq!(persisted["upper_limit"], 75);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn control_set_property_missing_value_returns_python_query_validation() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/control/set_property?key=lower_limit",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "value"],
                    "msg": "Field required",
                    "input": null
                }
            ]
        })
    );
}

#[tokio::test]
async fn control_set_property_missing_key_returns_python_query_validation() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/control/set_property?value=-64.5",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "key"],
                    "msg": "Field required",
                    "input": null
                }
            ]
        })
    );
}

#[tokio::test]
async fn diagnostic_download_test_returns_python_missing_file_json() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("diagnostic temp dir");
    let missing_path = root.join("missing.zip");
    let _download_guard = set_env_var_guard("RUST_API_DOWNLOAD_TEST_FILE", &missing_path);

    let response = request_response(app_with_seed_data(), "GET", "/download_test").await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        response_json(response).await,
        json!({"error": "File not found"})
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn diagnostic_download_test_serves_configured_zip_file() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("diagnostic temp dir");
    let zip_path = root.join("zipdir.zip");
    fs::write(&zip_path, b"zip-bytes").expect("diagnostic zip");
    let _download_guard = set_env_var_guard("RUST_API_DOWNLOAD_TEST_FILE", &zip_path);

    let response = request_response(app_with_seed_data(), "GET", "/download_test").await;
    let headers = response.headers().clone();

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        headers
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/octet-stream")
    );
    assert!(
        headers
            .get(header::CONTENT_DISPOSITION)
            .and_then(|value| value.to_str().ok())
            .unwrap_or_default()
            .contains("downloaded_file.zip")
    );
    assert_eq!(response_bytes(response).await.as_ref(), b"zip-bytes");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn diagnostic_download_test_uses_python_server_cwd_default_zip_path() {
    let _settings_env_guard = lock_test_env();
    let _download_guard = remove_env_var_guard("RUST_API_DOWNLOAD_TEST_FILE");
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("project root")
        .to_path_buf();
    let server_test_dir = project_root.join("app").join("Server").join("test");
    let zip_path = server_test_dir.join("zipdir.zip");
    assert!(
        !zip_path.exists(),
        "refusing to overwrite existing Python download_test fixture"
    );
    fs::create_dir_all(&server_test_dir).expect("python server test dir");
    fs::write(&zip_path, b"python-cwd-zip").expect("python server zipdir fixture");

    let response = request_response(app_with_seed_data(), "GET", "/download_test").await;
    let headers = response.headers().clone();

    let _ = fs::remove_file(&zip_path);
    let _ = fs::remove_dir(&server_test_dir);

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        headers
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/octet-stream")
    );
    assert_eq!(
        headers
            .get(header::CONTENT_DISPOSITION)
            .and_then(|value| value.to_str().ok()),
        Some("attachment; filename=\"downloaded_file.zip\"")
    );
    assert_eq!(response_bytes(response).await.as_ref(), b"python-cwd-zip");
}

#[tokio::test]
async fn speedtest_download_streams_requested_megabytes() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/speedtest/download?size_in_mb=2",
    )
    .await;
    let headers = response.headers().clone();

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        headers
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/octet-stream")
    );

    let bytes = response_bytes(response).await;

    assert_eq!(bytes.len(), 2 * 1024 * 1024);
    assert!(bytes.iter().all(|byte| *byte == b'0'));
}

#[tokio::test]
async fn speedtest_download_returns_empty_stream_for_negative_size_like_python() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/speedtest/download?size_in_mb=-1",
    )
    .await;
    let headers = response.headers().clone();

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        headers
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok()),
        Some("application/octet-stream")
    );
    assert!(response_bytes(response).await.is_empty());
}

#[tokio::test]
async fn speedtest_download_invalid_size_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/speedtest/download?size_in_mb=abc",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "size_in_mb"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn speedtest_upload_reports_python_compatible_file_metrics() {
    let boundary = "----rust-speedtest-boundary";
    let mut body = Vec::new();
    body.extend_from_slice(format!("--{boundary}\r\n").as_bytes());
    body.extend_from_slice(
        b"Content-Disposition: form-data; name=\"file\"; filename=\"sample.bin\"\r\n",
    );
    body.extend_from_slice(b"Content-Type: application/octet-stream\r\n\r\n");
    body.extend(std::iter::repeat(b'a').take(1024 * 1024));
    body.extend_from_slice(format!("\r\n--{boundary}--\r\n").as_bytes());

    let response = app_with_seed_data()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/speedtest/upload")
                .header(
                    header::CONTENT_TYPE,
                    format!("multipart/form-data; boundary={boundary}"),
                )
                .body(Body::from(body))
                .expect("multipart request"),
        )
        .await
        .expect("upload response");

    assert_eq!(response.status(), StatusCode::OK);

    let body = response_json(response).await;

    assert_eq!(body["filename"], "sample.bin");
    assert_eq!(body["file_size_mb"], 1.0);
    assert!(body["upload_time_s"].is_number());
    assert!(body["upload_speed_mb_s"].is_number());
}

#[tokio::test]
async fn speedtest_upload_accepts_python_sized_files_over_default_axum_limit() {
    let boundary = "----rust-speedtest-large-boundary";
    let mut body = Vec::new();
    body.extend_from_slice(format!("--{boundary}\r\n").as_bytes());
    body.extend_from_slice(
        b"Content-Disposition: form-data; name=\"file\"; filename=\"five-megabytes.bin\"\r\n",
    );
    body.extend_from_slice(b"Content-Type: application/octet-stream\r\n\r\n");
    body.extend(std::iter::repeat(b'a').take(5 * 1024 * 1024));
    body.extend_from_slice(format!("\r\n--{boundary}--\r\n").as_bytes());

    let response = app_with_seed_data()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/speedtest/upload")
                .header(
                    header::CONTENT_TYPE,
                    format!("multipart/form-data; boundary={boundary}"),
                )
                .body(Body::from(body))
                .expect("multipart request"),
        )
        .await
        .expect("upload response");

    assert_eq!(response.status(), StatusCode::OK);

    let body = response_json(response).await;

    assert_eq!(body["filename"], "five-megabytes.bin");
    assert_eq!(body["file_size_mb"], 5.0);
    assert!(body["upload_time_s"].is_number());
    assert!(body["upload_speed_mb_s"].is_number());
}

#[tokio::test]
async fn speedtest_upload_missing_file_returns_fastapi_validation_error() {
    let response = request_response(app_with_seed_data(), "POST", "/speedtest/upload").await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "file"],
                    "msg": "Field required",
                    "input": null
                }
            ]
        })
    );
}

#[tokio::test]
async fn speedtest_upload_preserves_unquoted_multipart_filename_like_python_parser() {
    let boundary = "----rust-speedtest-unquoted-boundary";
    let mut body = Vec::new();
    body.extend_from_slice(format!("--{boundary}\r\n").as_bytes());
    body.extend_from_slice(
        b"Content-Disposition: form-data; name=file; filename=browser-upload.bin\r\n",
    );
    body.extend_from_slice(b"Content-Type: application/octet-stream\r\n\r\n");
    body.extend(std::iter::repeat(b'a').take(1024));
    body.extend_from_slice(format!("\r\n--{boundary}--\r\n").as_bytes());

    let response = app_with_seed_data()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/speedtest/upload")
                .header(
                    header::CONTENT_TYPE,
                    format!("multipart/form-data; boundary={boundary}"),
                )
                .body(Body::from(body))
                .expect("multipart request"),
        )
        .await
        .expect("upload response");

    assert_eq!(response.status(), StatusCode::OK);

    let body = response_json(response).await;

    assert_eq!(body["filename"], "browser-upload.bin");
    assert_eq!(body["file_size_mb"], 0.0);
}

#[tokio::test]
async fn settings_test_mode_status_matches_python_contract() {
    let response =
        request_response(app_with_seed_data(), "GET", "/settings/test_mode_status").await;
    let status = response.status();
    let bytes = response_bytes(response).await;

    assert_eq!(status, StatusCode::OK);
    let body: Value = serde_json::from_slice(&bytes).expect("settings status json");
    assert!(body["developer_mode"].is_boolean());
    assert!(body["is_local"].is_boolean());
    assert!(body["config_file_exists"].is_boolean());
    assert!(body["config_file_path"].is_string());
}

#[tokio::test]
async fn redetection_status_start_and_status_return_python_message_fields() {
    let app = app_with_redetection_seed_data();

    let (status, initial) = request_json(app.clone(), "GET", "/reDetection/status").await;

    assert_eq!(status, StatusCode::OK);
    assert_re_detection_python_status_shape(&initial);
    assert_eq!(initial["running"], false);
    assert_eq!(initial["total"], 0);
    assert_eq!(initial["pending"], 0);
    assert_eq!(initial["progress"].as_f64().expect("initial progress"), 0.0);

    let (start_status, started) =
        request_json(app.clone(), "GET", "/reDetection/start/42/44").await;

    assert_eq!(start_status, StatusCode::OK);
    assert_re_detection_python_status_shape(&started);
    assert_eq!(started["running"], false);
    assert_eq!(started["total"], 3);
    assert_eq!(started["pending"], 3);
    assert_eq!(started["progress"].as_f64().expect("started progress"), 0.0);

    let (status, current) = request_json(app, "GET", "/reDetection/status").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(current, started);
}

#[tokio::test]
async fn redetection_start_rejects_non_python_int_converter_paths_like_python() {
    for uri in [
        "/reDetection/start/abc/44",
        "/reDetection/start/-1/44",
        "/reDetection/start/42/abc",
        "/reDetection/start/42/-1",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn redetection_start_normalizes_reverse_range_and_returns_python_status_fields() {
    let app = app_with_redetection_seed_data();

    let (status, body) = request_json(app.clone(), "GET", "/reDetection/start/44/42").await;

    assert_eq!(status, StatusCode::OK);
    assert_re_detection_python_status_shape(&body);
    assert_eq!(body["running"], false);
    assert_eq!(body["total"], 3);
    assert_eq!(body["done"], 0);
    assert_eq!(body["pending"], 3);
    assert_eq!(body["error"], "");
    assert_eq!(body["queue"], json!([44, 43, 42]));
    assert_eq!(body["progress"].as_f64().expect("progress"), 0.0);

    let messages = body["messages"].as_array().expect("messages array");
    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0]["Base"], "ImageMosaicThread");
    assert_eq!(messages[0]["level"], "DEBUG");
    assert!(messages[0]["time"].as_str().expect("message time").len() >= 19);
    assert_eq!(
        messages[0]["msg"],
        "set_re_detection_by_coil_id start=42 end=44 count=3"
    );

    let (current_status, current) = request_json(app, "GET", "/reDetection/status").await;

    assert_eq!(current_status, StatusCode::OK);
    assert_eq!(current, body);
}

#[tokio::test]
async fn redetection_start_preserves_python_message_history_across_restarts() {
    let app = app_with_redetection_seed_data();

    let (first_status, first) = request_json(app.clone(), "GET", "/reDetection/start/42/43").await;

    assert_eq!(first_status, StatusCode::OK);
    assert_eq!(
        first["messages"].as_array().expect("first messages").len(),
        1
    );

    let (second_status, second) =
        request_json(app.clone(), "GET", "/reDetection/start/44/44").await;

    assert_eq!(second_status, StatusCode::OK);
    assert_eq!(second["queue"], json!([44]));
    assert_eq!(second["total"], 1);
    let messages = second["messages"].as_array().expect("second messages");
    assert_eq!(messages.len(), 2);
    assert_eq!(
        messages[0]["msg"],
        "set_re_detection_by_coil_id start=42 end=43 count=2"
    );
    assert_eq!(
        messages[1]["msg"],
        "set_re_detection_by_coil_id start=44 end=44 count=1"
    );

    let (current_status, current) = request_json(app, "GET", "/reDetection/status").await;

    assert_eq!(current_status, StatusCode::OK);
    assert_eq!(current, second);
}

#[tokio::test]
async fn redetection_start_keeps_last_fifty_messages_like_python_deque() {
    let app = app_with_redetection_seed_data();
    let mut latest = Value::Null;

    for coil_id in 100..=150 {
        let (status, body) = request_json(
            app.clone(),
            "GET",
            &format!("/reDetection/start/{coil_id}/{coil_id}"),
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        latest = body;
    }

    let messages = latest["messages"].as_array().expect("messages array");
    assert_eq!(messages.len(), 50);
    assert_eq!(
        messages[0]["msg"],
        "set_re_detection_by_coil_id start=101 end=101 count=0"
    );
    assert_eq!(
        messages[49]["msg"],
        "set_re_detection_by_coil_id start=150 end=150 count=0"
    );
}

#[tokio::test]
async fn redetection_websocket_accepts_qml_start_message_without_immediate_echo() {
    let ws_url = spawn_ws_server(app_with_redetection_seed_data(), "/ws/reDetection").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text(
            json!({
                "from_id": 42,
                "to_id": 44,
                "folder": "D:/Project/BKVison/LG_3D/output"
            })
            .to_string()
            .into(),
        ))
        .await
        .expect("send redetection request");

    let immediate = tokio::time::timeout(Duration::from_millis(300), socket.next()).await;

    assert!(
        immediate.is_err(),
        "Python receive_messages only queues work; status is sent by the periodic sender"
    );

    let message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("periodic redetection websocket message")
        .expect("redetection websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");

    assert_eq!(body["running"], false);
    assert_eq!(body["total"], 3);
    assert_eq!(body["pending"], 3);
    assert_re_detection_python_status_shape(&body);
    assert_eq!(body["progress"].as_f64().expect("progress"), 0.0);
    assert_eq!(body["error"], "");
}

#[tokio::test]
async fn redetection_websocket_invalid_json_message_closes_connection() {
    let app = app_with_redetection_seed_data();
    let ws_url = spawn_ws_server(app.clone(), "/ws/reDetection").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");

    socket
        .send(Message::Text("invalid-json-payload".to_string().into()))
        .await
        .expect("send invalid payload");

    let terminal = tokio::time::timeout(Duration::from_millis(800), socket.next())
        .await
        .expect("invalid websocket payload should terminate the connection");
    assert!(
        matches!(terminal, None | Some(Ok(Message::Close(_)))),
        "connection should close after invalid json message"
    );
}

#[tokio::test]
async fn redetection_websocket_accepts_missing_folder_field() {
    let app = app_with_redetection_seed_data();
    let ws_url = spawn_ws_server(app.clone(), "/ws/reDetection").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");

    socket
        .send(
            Message::Text(
                json!({
                    "from_id": 42,
                    "to_id": 44
                })
                .to_string()
                .into(),
            ),
        )
        .await
        .expect("send payload without folder");

    let status = tokio::time::timeout(Duration::from_millis(1800), socket.next())
        .await
        .expect("status should still be pushed without folder");
    let message = status.expect("websocket should return a message");
    match message {
        Ok(Message::Text(text)) => {
            assert!(!text.is_empty(), "status payload should not be empty");
        }
        Ok(Message::Close(_)) => panic!("connection closed unexpectedly when folder was omitted"),
        Ok(_) => {}
        Err(_) => panic!("websocket should continue running when folder is omitted"),
    }
}

#[tokio::test]
async fn redetection_websocket_pushes_status_periodically_like_python() {
    let ws_url = spawn_ws_server(app_with_redetection_seed_data(), "/ws/reDetection").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text(
            json!({
                "from_id": 42,
                "to_id": 44,
                "folder": "D:/Project/BKVison/LG_3D/output"
            })
            .to_string()
            .into(),
        ))
        .await
        .expect("send redetection request");

    let first_message = socket
        .next()
        .await
        .expect("initial redetection websocket message")
        .expect("initial message ok");
    let first_body: Value =
        serde_json::from_str(first_message.to_text().expect("initial text message")).expect("json");

    let second_message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("periodic redetection websocket message")
        .expect("second redetection websocket message")
        .expect("second message ok");
    let second_body: Value =
        serde_json::from_str(second_message.to_text().expect("second text message")).expect("json");

    assert_eq!(second_body, first_body);
    assert_eq!(second_body["running"], false);
    assert_eq!(second_body["total"], 3);
    assert_eq!(second_body["pending"], 3);
}

#[tokio::test]
async fn alg_2d_models_start_stop_and_progress_match_qml_contract() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let classifier_dir = model_dir.join("classifier");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&classifier_dir).expect("classifier dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(model_dir.join("detector.pt"), b"placeholder").expect("detector model");
    fs::write(model_dir.join("coil_mask.onnx"), b"placeholder").expect("segment model");
    fs::write(
        classifier_dir.join("classifier.json"),
        r#"{"model_name":"cls","checkpoint_path":"cls.ckpt"}"#,
    )
    .expect("classifier config");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let ws_url = spawn_ws_server(app_with_seed_data(), "/ws/alg_2d/test/progress").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect alg websocket");
    let message = socket
        .next()
        .await
        .expect("alg progress websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");
    assert_eq!(body["task_id"], Value::Null);
    assert_eq!(body["status"], "idle");

    let (models_status, models_body) = request_json(app.clone(), "GET", "/alg_2d/models").await;

    assert_eq!(models_status, StatusCode::OK);
    assert_eq!(
        models_body["models"]
            .as_array()
            .expect("models array")
            .iter()
            .map(|model| model["name"].as_str().expect("model name"))
            .collect::<Vec<_>>(),
        vec!["classifier.json", "detector.pt", "coil_mask.onnx"]
    );
    assert_eq!(models_body["models"][0]["type"], "classifier");
    assert_eq!(
        models_body["models"][0]["display_name"],
        "分类器 · classifier.json"
    );
    assert_eq!(
        models_body["models"][1]["display_name"],
        "检测 · detector.pt"
    );
    assert_eq!(
        models_body["models"][2]["display_name"],
        "分割 · coil_mask.onnx"
    );

    let start_response = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 2.0,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": true,
                "prioritize": false
            }
        }),
    )
    .await;
    assert_eq!(start_response.status(), StatusCode::OK);
    let start_body = response_json(start_response).await;
    assert_eq!(start_body["ok"], true);
    let task_id = start_body["task_id"].as_str().expect("task id");
    assert!(!task_id.is_empty());

    let stop_response = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/stop",
        json!({ "task_id": task_id }),
    )
    .await;
    assert_eq!(stop_response.status(), StatusCode::OK);
    let stop_body = response_json(stop_response).await;
    assert_eq!(stop_body, json!({"ok": true, "message": "当前无任务"}));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_progress_websocket_pushes_updates_without_client_poll_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(model_dir.join("detector.pt"), b"placeholder").expect("detector model");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let ws_url = spawn_ws_server(app.clone(), "/ws/alg_2d/test/progress").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect alg websocket");
    let initial_message = socket
        .next()
        .await
        .expect("initial alg progress websocket message")
        .expect("initial message ok");
    let initial_body: Value =
        serde_json::from_str(initial_message.to_text().expect("initial text message"))
            .expect("initial json");
    assert_eq!(initial_body["task_id"], Value::Null);
    assert_eq!(initial_body["status"], "idle");

    let start_response = request_json_body(
        app,
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.4,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": false
            }
        }),
    )
    .await;
    assert_eq!(start_response.status(), StatusCode::OK);
    let start_body = response_json(start_response).await;
    let task_id = start_body["task_id"].as_str().expect("task id");

    let update_message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("Python broadcasts alg progress updates without client polling")
        .expect("alg progress websocket update")
        .expect("update message ok");
    let update_body: Value =
        serde_json::from_str(update_message.to_text().expect("update text message"))
            .expect("update json");

    assert_eq!(update_body["task_id"], task_id);
    assert_eq!(update_body["status"], "完成");
    assert_eq!(update_body["message"], "未找到可测试图片");
    assert_eq!(update_body["finished"], true);
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_test_stop_accepts_empty_body_like_python() {
    let response = request_response(app_with_seed_data(), "POST", "/alg_2d/test/stop").await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(
        response_json(response).await,
        json!({"ok": true, "message": "当前无任务"})
    );
}

#[tokio::test]
async fn alg_2d_test_start_processes_image_files_into_python_style_output_folders() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let nested_dir = target_dir.join("nested");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&nested_dir).expect("target dir");
    fs::write(model_dir.join("detector.pt"), b"placeholder").expect("detector model");
    fs::write(target_dir.join("first.jpg"), b"fake image one").expect("first image");
    fs::write(nested_dir.join("second.png"), b"fake image two").expect("second image");
    fs::write(target_dir.join("ignored.txt"), b"not an image").expect("ignored text");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let start_response = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.4,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": false
            }
        }),
    )
    .await;

    assert_eq!(start_response.status(), StatusCode::OK);
    let start_body = response_json(start_response).await;
    assert_eq!(start_body["ok"], true);
    let task_id = start_body["task_id"].as_str().expect("task id").to_string();

    let expected_first = output_dir.join("normal").join("empty").join("first.jpg");
    let expected_second = output_dir.join("normal").join("empty").join("second.png");
    for _ in 0..100 {
        if expected_first.exists() && expected_second.exists() {
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    assert!(
        expected_first.exists(),
        "first output image should be copied"
    );
    assert!(
        expected_second.exists(),
        "second output image should be copied"
    );
    assert!(
        target_dir.join("first.jpg").exists(),
        "copy mode should keep the source image"
    );
    assert!(
        !output_dir
            .join("normal")
            .join("empty")
            .join("ignored.txt")
            .exists()
    );

    let ws_url = spawn_ws_server(app, "/ws/alg_2d/test/progress").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect alg websocket");
    let message = socket
        .next()
        .await
        .expect("alg progress websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");
    assert_eq!(body["task_id"], task_id);
    assert_eq!(body["status"], "完成");
    assert_eq!(body["done"], 2);
    assert_eq!(body["total"], 2);
    assert_eq!(body["finished"], true);
    assert_eq!(body["summary"]["normal"], 2);
    assert_eq!(body["summary"]["empty"], 2);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_test_start_does_not_write_empty_detector_label_without_boxes_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(model_dir.join("detector.pt"), b"placeholder").expect("detector model");
    RgbImage::from_pixel(4, 3, Rgb([20, 30, 40]))
        .save_with_format(target_dir.join("sample.jpg"), ImageFormat::Jpeg)
        .expect("write sample image");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let start_response = request_json_body(
        app,
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.4,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": true
            }
        }),
    )
    .await;

    assert_eq!(start_response.status(), StatusCode::OK);
    let expected_image = output_dir.join("normal").join("empty").join("sample.jpg");
    let unexpected_xml = output_dir.join("normal").join("empty").join("sample.xml");
    for _ in 0..100 {
        if expected_image.exists() {
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    assert!(
        expected_image.exists(),
        "fallback image output should still be copied"
    );
    assert!(
        !unexpected_xml.exists(),
        "Python alg_test_manager only writes save_label outputs when detector boxes exist"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_test_prioritize_mode_skips_normal_image_output_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(model_dir.join("detector.pt"), b"placeholder").expect("detector model");
    fs::write(target_dir.join("normal.jpg"), b"fake normal image").expect("normal image");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let start_response = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.4,
            "mode": "move",
            "options": {
                "classify_save": true,
                "save_label": false,
                "prioritize": true
            }
        }),
    )
    .await;
    assert_eq!(start_response.status(), StatusCode::OK);
    let start_body = response_json(start_response).await;
    let task_id = start_body["task_id"].as_str().expect("task id").to_string();

    let unexpected_output = output_dir.join("normal").join("empty").join("normal.jpg");
    for _ in 0..100 {
        let ws_url = spawn_ws_server(app.clone(), "/ws/alg_2d/test/progress").await;
        let (mut socket, _) = connect_async(&ws_url).await.expect("connect alg websocket");
        let message = socket
            .next()
            .await
            .expect("alg progress websocket message")
            .expect("message ok");
        let body: Value =
            serde_json::from_str(message.to_text().expect("text message")).expect("json");
        if body["finished"] == true {
            assert_eq!(body["task_id"], task_id);
            assert_eq!(body["done"], 1);
            assert_eq!(body["total"], 1);
            assert_eq!(body["summary"]["normal"], 1);
            assert_eq!(body["summary"]["empty"], 1);
            assert_eq!(body["summary"]["skipped"], 1);
            assert_eq!(body["message"], "处理完成，共 1 张");
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    assert!(
        !unexpected_output.exists(),
        "prioritize mode should not copy or move normal fallback images"
    );
    assert!(
        target_dir.join("normal.jpg").exists(),
        "prioritize mode should leave source image in place even when mode is move"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_test_start_classifier_uses_classify_folder_and_ignores_save_label_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(
        model_dir.join("classifier.json"),
        r#"{"model_name":"cls","checkpoint_path":"./cls.pt"}"#,
    )
    .expect("classifier model");
    RgbImage::from_pixel(12, 8, Rgb([40, 50, 60]))
        .save_with_format(target_dir.join("good.jpg"), ImageFormat::Jpeg)
        .expect("write sample image");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let start_response = request_json_body(
        app,
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "classifier.json",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.2,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": true
            }
        }),
    )
    .await;

    assert_eq!(start_response.status(), StatusCode::OK);
    let expected_image = output_dir.join("normal").join("classified").join("normal").join("good.jpg");
    let unexpected_xml = output_dir.join("normal").join("classified").join("normal").join("good.xml");
    for _ in 0..100 {
        if expected_image.exists() {
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    assert!(
        expected_image.exists(),
        "classifier result should be written into classified folder by predicted label"
    );
    assert!(
        !unexpected_xml.exists(),
        "classifier save_label should be ignored and no xml should be written"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_test_start_classifier_empty_image_marks_empty_and_normal_summary_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let model_dir = root.join("model");
    let target_dir = root.join("target");
    let output_dir = root.join("output");
    fs::create_dir_all(&model_dir).expect("model dir");
    fs::create_dir_all(&target_dir).expect("target dir");
    fs::write(
        model_dir.join("classifier.json"),
        r#"{"model_name":"cls","checkpoint_path":"./cls.pt"}"#,
    )
    .expect("classifier model");
    RgbImage::from_pixel(12, 8, Rgb([40, 50, 60]))
        .save_with_format(target_dir.join("empty_case.jpg"), ImageFormat::Jpeg)
        .expect("write empty-like sample image");
    let _model_guard = set_env_var_guard("RUST_API_MODEL_DIR", &model_dir);

    let app = app_with_seed_data();
    let start_response = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "classifier.json",
            "target": target_dir.to_string_lossy(),
            "output": output_dir.to_string_lossy(),
            "threshold": 0.2,
            "mode": "copy",
            "options": {
                "classify_save": true,
                "save_label": true
            }
        }),
    )
    .await;
    assert_eq!(start_response.status(), StatusCode::OK);
    let start_body = response_json(start_response).await;
    let task_id = start_body["task_id"].as_str().expect("task id").to_string();

    let ws_url = spawn_ws_server(app, "/ws/alg_2d/test/progress").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect alg websocket");
    for _ in 0..100 {
        let message = socket
            .next()
            .await
            .expect("alg progress websocket message")
            .expect("message ok");
        let body: Value =
            serde_json::from_str(message.to_text().expect("text message")).expect("json");
        if body["finished"] == true {
            assert_eq!(body["task_id"], task_id);
            assert_eq!(body["status"], "完成");
            assert_eq!(body["done"], 1);
            assert_eq!(body["total"], 1);
            assert_eq!(body["summary"]["normal"], 1);
            assert_eq!(body["summary"]["empty"], 1);
            assert_eq!(body["summary"]["abnormal"], 0);
            assert_eq!(body["summary"]["skipped"], 0);
            break;
        }
    }

    let expected_image = output_dir.join("normal").join("empty").join("empty_case.jpg");
    assert!(
        expected_image.exists(),
        "classifier empty image should be written to normal/empty"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn server_state_routes_return_empty_qml_compatible_state_without_runtime() {
    let app = app_with_seed_data();

    let (status, body) = request_json(app.clone(), "GET", "/getServerState").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!([]));

    let ws_url = spawn_ws_server(app, "/ws/DetectionState").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    let message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("periodic server state websocket message")
        .expect("server state websocket message")
        .expect("first message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");

    assert_eq!(body, json!([]));
}

#[tokio::test]
async fn server_state_websocket_pushes_status_periodically_like_python() {
    let ws_url = spawn_ws_server(app_with_seed_data(), "/ws/DetectionState").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");

    let first_message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("periodic server state websocket message")
        .expect("first server state websocket message")
        .expect("first message ok");
    let second_message = tokio::time::timeout(Duration::from_millis(1500), socket.next())
        .await
        .expect("periodic server state websocket message")
        .expect("second server state websocket message")
        .expect("second message ok");
    let first_body: Value =
        serde_json::from_str(first_message.to_text().expect("initial text message")).expect("json");
    let second_body: Value =
        serde_json::from_str(second_message.to_text().expect("second text message")).expect("json");

    assert_eq!(first_body, json!([]));
    assert_eq!(second_body, first_body);
}

#[tokio::test]
async fn server_state_websocket_invalid_json_message_closes_connection() {
    let ws_url = spawn_ws_server(app_with_seed_data(), "/ws/DetectionState").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");

    socket
        .send(Message::Text("invalid-json-payload".to_string().into()))
        .await
        .expect("send invalid payload");

    let terminal = tokio::time::timeout(Duration::from_millis(800), socket.next())
        .await
        .expect("invalid websocket payload should terminate the connection");
    assert!(
        matches!(terminal, None | Some(Ok(Message::Close(_)))),
        "connection should close after invalid json message"
    );
}

#[tokio::test]
async fn hardware_returns_python_compatible_status_objects() {
    let response = request_response(app_with_seed_data(), "GET", "/hardware").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("hardware body");
    for key in ["cpu", "memory", "disk", "gpu"] {
        let item = &body[key];
        assert!(
            item.is_object(),
            "{key} should be a Python-compatible object"
        );
        assert!(item["key"].is_string(), "{key}.key should be a string");
        assert!(item["value"].is_string(), "{key}.value should be a string");
        assert!(item["msg"].is_string(), "{key}.msg should be a string");
        let level = item["level"]
            .as_i64()
            .unwrap_or_else(|| panic!("{key}.level should be an integer"));
        assert!(
            (1..=3).contains(&level),
            "{key}.level should be between 1 and 3"
        );
    }
    assert_eq!(body["cpu"]["key"], "CPU");
    assert_eq!(body["memory"]["key"], "内存");
    assert_eq!(body["disk"]["key"], "硬盘");
    assert_eq!(body["gpu"]["key"], "显卡");
}

#[tokio::test]
async fn camera_read_status_routes_return_configured_offline_shapes_for_qml() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera config temp root");
    let capture_config_path = write_camera_config(&root);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let response = request_response(app_with_seed_data(), "GET", "/capture_status").await;
    let status = response.status();
    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("capture status body");
    assert_eq!(body["ok"], false);
    assert_eq!(body["service"], "CapAll");
    assert_eq!(body["serviceUrl"], "http://127.0.0.1:6100/capture/status");
    assert!(body.get("cameraCount").is_none());
    let cameras = body["cameras"].as_array().expect("capture status cameras");
    assert_eq!(cameras.len(), 2);
    assert_eq!(cameras[0]["key"], "Cap_S_D");
    assert_eq!(cameras[0]["serviceUrl"], "http://127.0.0.1:6100");
    assert_eq!(cameras[0]["legacyServiceUrl"], "http://127.0.0.1:6104");
    assert_eq!(
        sorted_value_keys(&cameras[0]["status"]),
        vec!["connected", "message", "ok", "serviceUrl"]
    );
    assert_eq!(cameras[0]["status"]["ok"], false);
    assert_eq!(cameras[0]["status"]["connected"], false);
    assert_eq!(
        cameras[0]["status"]["serviceUrl"],
        "http://127.0.0.1:6100/cameras/Cap_S_D/status"
    );

    let adjust_response = request_response(app_with_seed_data(), "GET", "/camera_adjust").await;
    let adjust_status = adjust_response.status();
    assert_eq!(adjust_status, StatusCode::OK);
    let adjust_body: Value =
        serde_json::from_slice(&response_bytes(adjust_response).await).expect("camera adjust body");
    assert_eq!(
        adjust_body["configFile"],
        capture_config_path.to_string_lossy().to_string()
    );
    assert_eq!(adjust_body["captureServiceUrl"], "http://127.0.0.1:6100");
    assert_eq!(adjust_body["captureStatus"]["ok"], false);
    assert_eq!(adjust_body["captureStatus"]["cameraCount"], 2);
    assert_eq!(
        sorted_value_keys(&adjust_body["cameras"][0]["status"]),
        vec![
            "capture",
            "connected",
            "lastError3D",
            "lastFrameAge3D",
            "message",
            "ok",
            "serviceUrl"
        ]
    );
    assert_eq!(
        sorted_value_keys(&adjust_body["cameras"][0]["status"]["capture"]),
        vec!["connected", "message", "ok", "serviceUrl"]
    );
    assert_eq!(adjust_body["cameras"][0]["status"]["capture"]["ok"], false);
    assert_eq!(adjust_body["cameras"][0]["status"]["lastError3D"], "");

    let alarm_response = request_response(app_with_seed_data(), "GET", "/cameraAlarm").await;
    let alarm_status = alarm_response.status();
    assert_eq!(alarm_status, StatusCode::OK);
    let alarm_body: Value =
        serde_json::from_slice(&response_bytes(alarm_response).await).expect("camera alarm body");
    assert_eq!(alarm_body["S_D"]["cameraKey"], "Cap_S_D");
    assert_eq!(alarm_body["S_D"]["cameraName"], "S_D");
    assert_eq!(alarm_body["S_D"]["connected"], false);
    assert_eq!(alarm_body["S_D"]["ok"], false);
    assert_eq!(alarm_body["S_D"]["level"], 3);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_read_status_routes_use_capture_service_success_payloads_like_python() {
    let _settings_env_guard = lock_test_env();
    let mock_service = axum::Router::new().route(
        "/capture/status",
        axum::routing::get(|| async {
            Json(json!({
                "ok": true,
                "message": "capture ready",
                "cameraCount": 2,
                "service": "CapAll",
                "cameras": [
                    {
                        "key": "Cap_S_D",
                        "ok": true,
                        "connected": true,
                        "message": "S ready",
                        "camera2D": {
                            "ok": true,
                            "connected": true,
                            "message": "2D ready",
                            "params": {
                                "exposureTime": 1200,
                                "gain": 8
                            },
                            "lastFrameAge": 1.25,
                            "serviceReady": true
                        },
                        "lastFrameAge3D": 2.5,
                        "lastError3D": ""
                    },
                    {
                        "key": "Cap_L_D",
                        "ok": false,
                        "connected": false,
                        "message": "L offline",
                        "lastError3D": "3D error"
                    }
                ]
            }))
        }),
    );
    let mock_base_url = spawn_http_server(mock_service).await;
    let mock_port = mock_base_url
        .rsplit(':')
        .next()
        .expect("mock port")
        .parse::<u16>()
        .expect("mock port number");

    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera config temp root");
    let capture_config_path = write_camera_config_with_endpoint(&root, "127.0.0.1", mock_port);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let capture_response = request_response(app_with_seed_data(), "GET", "/capture_status").await;
    assert_eq!(capture_response.status(), StatusCode::OK);
    let capture_body: Value =
        serde_json::from_slice(&response_bytes(capture_response).await).expect("capture body");
    assert_eq!(capture_body["ok"], true);
    assert_eq!(capture_body["message"], "capture ready");
    assert_eq!(capture_body["cameraCount"], 2);
    assert_eq!(capture_body["cameras"][0]["key"], "Cap_S_D");
    assert!(capture_body["cameras"][0].get("name").is_none());

    let adjust_response = request_response(app_with_seed_data(), "GET", "/camera_adjust").await;
    assert_eq!(adjust_response.status(), StatusCode::OK);
    let adjust_body: Value =
        serde_json::from_slice(&response_bytes(adjust_response).await).expect("camera adjust body");
    assert_eq!(adjust_body["captureStatus"]["ok"], true);
    assert_eq!(adjust_body["captureStatus"]["message"], "capture ready");
    assert_eq!(adjust_body["captureStatus"]["cameraCount"], 2);
    assert_eq!(adjust_body["cameras"][0]["key"], "Cap_S_D");
    assert_eq!(adjust_body["cameras"][0]["status"]["ok"], true);
    assert_eq!(adjust_body["cameras"][0]["status"]["message"], "2D ready");
    assert_eq!(
        adjust_body["cameras"][0]["status"]["params"]["exposureTime"],
        1200
    );
    assert_eq!(
        adjust_body["cameras"][0]["status"]["capture"]["message"],
        "S ready"
    );
    assert_eq!(adjust_body["cameras"][0]["status"]["lastFrameAge3D"], 2.5);
    assert_eq!(adjust_body["cameras"][1]["status"]["message"], "L offline");
    assert_eq!(
        adjust_body["cameras"][1]["status"]["lastError3D"],
        "3D error"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_alarm_uses_capture_service_success_payloads_like_python() {
    let _settings_env_guard = lock_test_env();
    let mock_service = axum::Router::new().route(
        "/capture/status",
        axum::routing::get(|| async {
            Json(json!({
                "ok": true,
                "message": "capture ready",
                "cameraCount": 2,
                "cameras": [
                    {
                        "key": "Cap_S_D",
                        "ok": true,
                        "connected": true,
                        "message": "S capture",
                        "camera2D": {
                            "ok": true,
                            "connected": true,
                            "message": "2D ready",
                            "DeviceTemperature": 36,
                            "lastFrameAge": 1.25
                        },
                        "lastError2D": "",
                        "lastError3D": "",
                        "serviceReady": true,
                        "cap2D": true,
                        "cap3D": true
                    },
                    {
                        "key": "Cap_L_D",
                        "ok": false,
                        "connected": true,
                        "message": "capture warning",
                        "camera2D": {
                            "ok": true,
                            "connected": true,
                            "message": "2D ready",
                            "lastFrameAge": 2.5
                        },
                        "lastError2D": "",
                        "lastError3D": "3D timeout",
                        "serviceReady": true,
                        "cap2D": true,
                        "cap3D": true
                    }
                ]
            }))
        }),
    );
    let mock_base_url = spawn_http_server(mock_service).await;
    let mock_port = mock_base_url
        .rsplit(':')
        .next()
        .expect("mock port")
        .parse::<u16>()
        .expect("mock port number");

    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera config temp root");
    let capture_config_path = write_camera_config_with_endpoint(&root, "127.0.0.1", mock_port);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let response = request_response(app_with_seed_data(), "GET", "/cameraAlarm").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera alarm body");
    assert_eq!(body["S_D"]["cameraKey"], "Cap_S_D");
    assert_eq!(body["S_D"]["cameraName"], "S_D");
    assert_eq!(body["S_D"]["DeviceTemperature"], 36);
    assert_eq!(body["S_D"]["level"], 1);
    assert_eq!(body["S_D"]["msg"], "2D ready");
    assert_eq!(body["S_D"]["ok"], true);
    assert_eq!(body["S_D"]["captureOk"], true);
    assert_eq!(body["S_D"]["lastFrameAge"], 1.25);

    assert_eq!(body["L_D"]["cameraKey"], "Cap_L_D");
    assert_eq!(body["L_D"]["level"], 3);
    assert_eq!(body["L_D"]["msg"], "3D timeout");
    assert_eq!(body["L_D"]["ok"], false);
    assert_eq!(body["L_D"]["captureOk"], false);
    assert_eq!(body["L_D"]["lastError3D"], "3D timeout");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_alarm_returns_offline_alarms_without_per_camera_timeout_when_capture_status_has_no_cameras()
 {
    let _settings_env_guard = lock_test_env();
    let per_camera_calls = Arc::new(AtomicU64::new(0));
    let calls_for_route = Arc::clone(&per_camera_calls);
    let mock_service = axum::Router::new()
        .route(
            "/capture/status",
            axum::routing::get(|| async {
                Json(json!({
                    "ok": false,
                    "message": "capture service unavailable",
                    "serviceUrl": "http://127.0.0.1/capture/status"
                }))
            }),
        )
        .route(
            "/cameras/{key}/status",
            axum::routing::get(move || {
                let calls = Arc::clone(&calls_for_route);
                async move {
                    calls.fetch_add(1, Ordering::Relaxed);
                    tokio::time::sleep(Duration::from_millis(250)).await;
                    Json(json!({"ok": false, "message": "should not be queried"}))
                }
            }),
        );
    let mock_base_url = spawn_http_server(mock_service).await;
    let mock_port = mock_base_url
        .rsplit(':')
        .next()
        .expect("mock port")
        .parse::<u16>()
        .expect("mock port number");

    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera config temp root");
    let capture_config_path = write_camera_config_with_endpoint(&root, "127.0.0.1", mock_port);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let started = Instant::now();
    let response = request_response(app_with_seed_data(), "GET", "/cameraAlarm").await;
    let elapsed = started.elapsed();

    assert_eq!(response.status(), StatusCode::OK);
    assert!(
        elapsed < Duration::from_millis(200),
        "offline alarm should not wait for per-camera probes, elapsed={elapsed:?}"
    );
    assert_eq!(per_camera_calls.load(Ordering::Relaxed), 0);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera alarm body");
    assert_eq!(body["S_D"]["cameraKey"], "Cap_S_D");
    assert_eq!(body["S_D"]["level"], 3);
    assert_eq!(body["S_D"]["msg"], "capture service unavailable");
    assert_eq!(body["S_D"]["ok"], false);
    assert_eq!(body["L_D"]["cameraKey"], "Cap_L_D");
    assert_eq!(body["L_D"]["level"], 3);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_adjust_returns_offline_status_without_per_camera_timeout_when_capture_status_has_no_cameras()
 {
    let _settings_env_guard = lock_test_env();
    let per_camera_calls = Arc::new(AtomicU64::new(0));
    let calls_for_route = Arc::clone(&per_camera_calls);
    let mock_service = axum::Router::new()
        .route(
            "/capture/status",
            axum::routing::get(|| async {
                Json(json!({
                    "ok": false,
                    "message": "capture service unavailable",
                    "serviceUrl": "http://127.0.0.1/capture/status"
                }))
            }),
        )
        .route(
            "/cameras/{key}/status",
            axum::routing::get(move || {
                let calls = Arc::clone(&calls_for_route);
                async move {
                    calls.fetch_add(1, Ordering::Relaxed);
                    tokio::time::sleep(Duration::from_millis(250)).await;
                    Json(json!({"ok": false, "message": "should not be queried"}))
                }
            }),
        );
    let mock_base_url = spawn_http_server(mock_service).await;
    let mock_port = mock_base_url
        .rsplit(':')
        .next()
        .expect("mock port")
        .parse::<u16>()
        .expect("mock port number");

    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera adjust fallback temp root");
    let capture_config_path = write_camera_config_with_endpoint(&root, "127.0.0.1", mock_port);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let started = Instant::now();
    let response = request_response(app_with_seed_data(), "GET", "/camera_adjust").await;
    let elapsed = started.elapsed();

    assert_eq!(response.status(), StatusCode::OK);
    assert!(
        elapsed < Duration::from_millis(200),
        "offline camera adjust should not wait for per-camera probes, elapsed={elapsed:?}"
    );
    assert_eq!(per_camera_calls.load(Ordering::Relaxed), 0);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera adjust body");
    assert_eq!(body["captureStatus"]["ok"], false);
    assert_eq!(
        body["captureStatus"]["message"],
        "capture service unavailable"
    );
    assert_eq!(body["captureStatus"]["cameraCount"], 2);
    assert_eq!(body["cameras"][0]["status"]["capture"]["ok"], false);
    assert_eq!(
        body["cameras"][0]["status"]["capture"]["message"],
        "capture service unavailable"
    );
    assert_eq!(body["cameras"][0]["status"]["ok"], false);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_alarm_falls_back_to_camera_data_keys_for_local_placeholder_capture_config() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera fallback temp root");
    let capture_config_path = write_local_placeholder_camera_config(&root);
    let server_config_path = write_camera_server_config(&root);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);
    let _server_guard = set_env_var_guard("API_SERVER_CONFIG", &server_config_path);

    let response = request_response(app_with_seed_data(), "GET", "/cameraAlarm").await;
    let status = response.status();
    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera alarm body");
    assert_eq!(body["Cap_S_D"]["cameraKey"], "Cap_S_D");
    assert_eq!(body["Cap_S_D"]["cameraName"], "Cap_S_D");
    assert!(body.get("Camera 1").is_none());

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_data_returns_configured_capture_folder_for_coil_and_camera_key() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera data temp root");
    let server_config_path = write_camera_server_config(&root);
    let _server_guard = set_env_var_guard("API_SERVER_CONFIG", &server_config_path);

    let response =
        request_response(app_with_seed_data(), "GET", "/cameraData/193113/Cap_S_D").await;
    let status = response.status();
    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera data body");
    assert_eq!(body["cameraKey"], "Cap_S_D");
    assert_eq!(body["coilId"], 193113);
    assert_eq!(body["surface"], "S");
    assert_eq!(body["source"], "G:\\Cap_S_D");
    assert_eq!(body["folder"], "G:\\Cap_S_D\\193113");
    assert_eq!(body["cropLeft"], 100);
    assert_eq!(body["cropRight"], 100);

    let missing_response = request_response(
        app_with_process_rows(),
        "GET",
        "/cameraData/193113/Cap_UNKNOWN",
    )
    .await;
    assert_eq!(missing_response.status(), StatusCode::NOT_FOUND);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn camera_adjust_post_routes_proxy_payload_and_reconnect_to_capture_service() {
    let _settings_env_guard = lock_test_env();
    let mock_service = axum::Router::new()
        .route(
            "/cameras/Cap_S_D/params",
            axum::routing::post(|Json(body): Json<Value>| async move {
                Json(json!({
                    "ok": true,
                    "route": "params",
                    "received": body,
                }))
            }),
        )
        .route(
            "/cameras/Cap_S_D/reconnect",
            axum::routing::post(|| async {
                Json(json!({
                    "ok": true,
                    "route": "reconnect",
                }))
            }),
        );
    let mock_base_url = spawn_http_server(mock_service).await;
    let mock_port = mock_base_url
        .rsplit(':')
        .next()
        .expect("mock port")
        .parse::<u16>()
        .expect("mock port number");

    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("camera post temp root");
    let capture_config_path = write_camera_config_with_endpoint(&root, "127.0.0.1", mock_port);
    let _capture_guard = set_env_var_guard("RUST_API_CAPTURE_CONFIG", &capture_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/camera_adjust/Cap_S_D",
        json!({
            "exposureTime": 1200,
            "gain": 8,
            "save": true,
        }),
    )
    .await;
    let status = response.status();
    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("camera post body");
    assert_eq!(body["ok"], true);
    assert_eq!(body["route"], "params");
    assert_eq!(body["received"]["exposureTime"], 1200);
    assert_eq!(body["received"]["gain"], 8);
    assert_eq!(body["received"]["save"], true);

    let reconnect_response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/camera_adjust/Cap_S_D/reconnect",
        json!({}),
    )
    .await;
    let reconnect_status = reconnect_response.status();
    assert_eq!(reconnect_status, StatusCode::OK);
    let reconnect_body: Value = serde_json::from_slice(&response_bytes(reconnect_response).await)
        .expect("camera reconnect body");
    assert_eq!(reconnect_body["ok"], true);
    assert_eq!(reconnect_body["route"], "reconnect");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn info_returns_qml_initialization_contract_from_runtime_config() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_full_info_runtime_config(&config_path, &save_s, &save_l);
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");

    let response = request_response(app_with_data_config(config), "GET", "/info").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("info body");
    assert_eq!(body["ErrorMap"]["DataFolderError"], -3);
    assert_eq!(body["ErrorMap"]["ImageError"], -2);
    assert_eq!(body["RendererList"], json!(["JET"]));
    assert_eq!(body["ColorMaps"]["JET"], 2);
    assert_eq!(body["SaveImageType"], ".png");
    assert_eq!(body["PreviewSize"], json!([512, 512]));
    assert_eq!(body["surfaceS"]["key"], "S");
    assert_eq!(
        body["surfaceS"]["saveFolder"].as_str(),
        Some(save_s.to_string_lossy().as_ref())
    );
    assert_eq!(body["surfaceS"]["rotate"], 90);
    assert_eq!(body["surfaceS"]["folderList"][0]["cameraKey"], "S_D");
    assert_eq!(body["surfaceL"]["key"], "L");
    assert_eq!(
        body["surfaceL"]["saveFolder"].as_str(),
        Some(save_l.to_string_lossy().as_ref())
    );
    assert_eq!(body["surfaceL"]["direction"], "R");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn info_reads_renderer_list_and_save_image_type_from_server_config_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        &config_path,
        serde_json::to_vec(&json!({
            "RendererList": ["JET", "GRAY", "TURBO"],
            "SaveImageType": ".jpg",
            "surface": [
                {"key": "S", "saveFolder": save_s.to_string_lossy()},
                {"key": "L", "saveFolder": save_l.to_string_lossy()}
            ]
        }))
        .expect("config json"),
    )
    .expect("write runtime config");
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");

    let (status, body) = request_json(app_with_data_config(config), "GET", "/info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["RendererList"], json!(["JET", "GRAY", "TURBO"]));
    assert_eq!(body["SaveImageType"], ".jpg");
    assert_eq!(body["surfaceS"]["key"], "S");
    assert_eq!(body["surfaceL"]["key"], "L");

    let _ = fs::remove_dir_all(root);
}

#[test]
fn default_runtime_config_uses_developer_server_config_like_python() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    let config_dir = root.join("configs");
    fs::create_dir_all(&config_dir).expect("config dir");
    let prod_save = root.join("Prod_Save_S");
    let dev_save = root.join("Dev_Save_S");
    fs::write(
        config_dir.join("Server3D.json"),
        serde_json::to_vec(&json!({
            "surface": [
                {"key": "S", "saveFolder": prod_save.to_string_lossy()}
            ]
        }))
        .expect("production config json"),
    )
    .expect("write production config");
    fs::write(
        config_dir.join("Server3DLoc2.json"),
        serde_json::to_vec(&json!({
            "surface": [
                {"key": "S", "saveFolder": dev_save.to_string_lossy()}
            ]
        }))
        .expect("developer config json"),
    )
    .expect("write developer config");
    let _api_config_guard = remove_env_var_guard("API_SERVER_CONFIG");
    let _config_dir_guard = set_env_var_guard("CONFIG_3D_DIR", &root);
    let _developer_mode_guard = set_env_var_guard("API_DEVELOPER_MODE", "true");

    let config = DataRuntimeConfig::load_default().expect("runtime config");
    let info = config.api_info();

    assert_eq!(
        info["surfaceS"]["saveFolder"].as_str(),
        Some(dev_save.to_string_lossy().as_ref())
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn info_returns_every_configured_surface_key_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let save_t = root.join("Save_T");
    let config_path = root.join("Server3D.json");
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        &config_path,
        serde_json::to_vec(&json!({
            "surface": [
                {"key": "S", "saveFolder": save_s.to_string_lossy(), "direction": "L"},
                {"key": "L", "saveFolder": save_l.to_string_lossy(), "direction": "R"},
                {
                    "key": "T",
                    "saveFolder": save_t.to_string_lossy(),
                    "direction": "M",
                    "folderList": [
                        {"cameraKey": "T_M", "source": "H:\\Cap_T_M"}
                    ]
                }
            ]
        }))
        .expect("config json"),
    )
    .expect("write runtime config");
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");

    let (status, body) = request_json(app_with_data_config(config), "GET", "/info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["surfaceT"]["key"], "T");
    assert_eq!(
        body["surfaceT"]["saveFolder"].as_str(),
        Some(save_t.to_string_lossy().as_ref())
    );
    assert_eq!(body["surfaceT"]["direction"], "M");
    assert_eq!(body["surfaceT"]["folderList"][0]["cameraKey"], "T_M");
    assert_eq!(body["surfaceS"]["key"], "S");
    assert_eq!(body["surfaceL"]["key"], "L");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn info_does_not_inject_missing_default_surfaces_like_python() {
    let root = unique_temp_dir();
    let save_t = root.join("Save_T");
    let config_path = root.join("Server3D.json");
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent).expect("runtime config parent");
    }
    fs::write(
        &config_path,
        serde_json::to_vec(&json!({
            "surface": [
                {
                    "key": "T",
                    "saveFolder": save_t.to_string_lossy(),
                    "rotate": 0,
                    "x_rotate": 0,
                    "direction": "M",
                    "folderList": []
                }
            ]
        }))
        .expect("config json"),
    )
    .expect("write runtime config");
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");

    let (status, body) = request_json(app_with_data_config(config), "GET", "/info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["surfaceT"]["key"], "T");
    assert_eq!(
        body["surfaceT"]["saveFolder"].as_str(),
        Some(save_t.to_string_lossy().as_ref())
    );
    assert!(
        body.get("surfaceS").is_none(),
        "Python serverConfigProperty.to_dict() only returns configured surfaces"
    );
    assert!(
        body.get("surfaceL").is_none(),
        "Python serverConfigProperty.to_dict() only returns configured surfaces"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn database_info_returns_python_compatible_startup_shape() {
    let _env_lock = lock_test_env();
    let _database_url_guard = set_env_var_guard(
        DATABASE_URL_ENV,
        "mysql+pymysql://test_user:test_pass@127.0.0.1:3306/Coil?charset=utf8mb4",
    );

    let response = request_response(app_with_seed_data(), "GET", "/database_info").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("database_info body");
    assert_eq!(body["url"][0], "mysql+pymysql");
    assert_eq!(body["url"][1], "test_user");
    assert_eq!(body["url"][2], "test_pass");
    assert_eq!(body["url"][3], "127.0.0.1");
    assert_eq!(body["url"][4], 3306);
    assert_eq!(body["url"][5], "Coil");
    assert_eq!(body["url"][6]["charset"], "utf8mb4");
    assert_eq!(body["echo"], false);
    assert_eq!(body["coil_last"]["Id"], 42);
}

#[tokio::test]
async fn database_info_coil_last_uses_python_coil_table_shape() {
    let _env_lock = lock_test_env();
    let _database_url_guard = set_env_var_guard(
        DATABASE_URL_ENV,
        "mysql+pymysql://test_user:test_pass@127.0.0.1:3306/Coil?charset=utf8mb4",
    );

    let (status, body) = request_json(app_with_seed_data(), "GET", "/database_info").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["coil_last"]["Id"], 42);
    assert_eq!(body["coil_last"]["SecondaryCoilId"], 42);
    assert_eq!(body["coil_last"]["DetectionTime"]["year"], 2026);
    assert_eq!(body["coil_last"]["DetectionTime"]["month"], 6);
    assert!(body["coil_last"].get("CoilNo").is_none());
}

#[tokio::test]
async fn database_info_coil_last_serializes_in_python_field_order() {
    let _env_lock = lock_test_env();
    let _database_url_guard = set_env_var_guard(
        DATABASE_URL_ENV,
        "mysql+pymysql://test_user:test_pass@127.0.0.1:3306/Coil?charset=utf8mb4",
    );

    let response = request_response(app_with_seed_data(), "GET", "/database_info").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body =
        String::from_utf8(response_bytes(response).await.to_vec()).expect("database info utf8");
    assert!(
        body.contains(
            r#""coil_last":{"SecondaryCoilId":42,"DetectionTime":{"year":2026,"month":6,"weekday":5,"day":27,"hour":12,"minute":35,"second":10},"DefectCountL":1,"Status_L":1,"Grade":2,"DefectCountS":3,"Id":42,"CheckStatus":2,"Status_S":2,"Msg":""}"#
        ),
        "{body}"
    );
}

#[tokio::test]
async fn defect_dict_reads_python_config_shape_for_qml_startup() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {
                "测试缺陷": {
                    "level": 3,
                    "color": "#123456",
                    "show": true,
                    "name": "测试缺陷",
                    "num": 0
                }
            },
            "default": {
                "level": 4,
                "color": "#FFA500",
                "show": true
            }
        }))
        .expect("defect json"),
    )
    .expect("write defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_response(app_with_seed_data(), "GET", "/defectDict").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("defectDict body");
    assert_eq!(body["data"]["测试缺陷"]["level"], 3);
    assert_eq!(body["data"]["测试缺陷"]["color"], "#123456");
    assert_eq!(body["data"]["测试缺陷"]["show"], true);
    assert_eq!(body["data"]["测试缺陷"]["name"], "测试缺陷");
    assert_eq!(body["data"]["测试缺陷"]["num"], 0);
    assert_eq!(body["default"]["level"], 4);
    assert_eq!(body["default"]["show"], true);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn defect_dict_all_returns_python_database_field_names() {
    let repository = InMemoryCoilRepository::new().with_defect_classes(vec![
        DefectClassDictRow {
            id: 2,
            defect_class: 20,
            defect_name: "擦伤".to_string(),
            defect_type: Some("surface".to_string()),
            defect_color: Some("#FF0000".to_string()),
            defect_level: Some(3),
            visible: Some(1),
            defect_desc: Some("表面擦伤".to_string()),
        },
        DefectClassDictRow {
            id: 1,
            defect_class: 10,
            defect_name: "压痕".to_string(),
            defect_type: None,
            defect_color: None,
            defect_level: Some(2),
            visible: Some(0),
            defect_desc: None,
        },
    ]);

    let (status, body) = request_json(
        build_app(ApiState::new(Arc::new(repository))),
        "GET",
        "/defectDictAll",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("defect dict all rows");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0]["Id"], 1);
    assert_eq!(rows[0]["defectClass"], 10);
    assert_eq!(rows[0]["defectName"], "压痕");
    assert_eq!(rows[0]["defectType"], Value::Null);
    assert_eq!(rows[0]["defectColor"], Value::Null);
    assert_eq!(rows[0]["defectLevel"], 2);
    assert_eq!(rows[0]["visible"], 0);
    assert_eq!(rows[0]["defectDesc"], Value::Null);
    assert_eq!(rows[1]["Id"], 2);
    assert_eq!(rows[1]["defectName"], "擦伤");
    assert_eq!(rows[1]["defectColor"], "#FF0000");
}

#[tokio::test]
async fn set_defect_dict_updates_config_data_and_preserves_default() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {
                "旧缺陷": {
                    "level": 1,
                    "color": "#111111",
                    "show": false,
                    "name": "旧缺陷",
                    "num": 0
                }
            },
            "default": {
                "level": 4,
                "color": "#FFA500",
                "show": true
            }
        }))
        .expect("defect json"),
    )
    .expect("write defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/setDefectDict",
        json!({
            "新缺陷": {
                "level": 2,
                "color": "#00FF00",
                "show": true,
                "name": "新缺陷",
                "num": 0
            }
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["status"], "success");
    assert_eq!(body["count"], 1);

    let persisted: Value =
        serde_json::from_slice(&fs::read(&defect_config_path).expect("persisted config"))
            .expect("json");
    assert_eq!(persisted["data"]["新缺陷"]["level"], 2);
    assert_eq!(persisted["data"]["新缺陷"]["color"], "#00FF00");
    assert_eq!(persisted["data"].as_object().expect("data").len(), 1);
    assert_eq!(persisted["default"]["level"], 4);
    assert_eq!(persisted["default"]["show"], true);

    let (_, read_body) = request_json(app_with_seed_data(), "GET", "/defectDict").await;
    assert_eq!(read_body["data"]["新缺陷"]["show"], true);
    assert_eq!(read_body["default"]["color"], "#FFA500");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn coil_list_value_change_keys_match_python_startup_keys() {
    let response =
        request_response(app_with_seed_data(), "GET", "/coil_list_value_change_keys").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("keys body");
    assert_eq!(
        body,
        json!([
            "二级内径",
            "二级卷径",
            "二级厚度",
            "宽度",
            "PLC位置信息",
            "缺陷",
            "距离平均",
            "识别速度",
            "生产间隔"
        ])
    );
}

#[tokio::test]
async fn grader_list_returns_python_secondary_coil_shape_and_next_text() {
    let response = request_response(app_with_grader_rows(), "GET", "/grader_list?count=1").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("grader list body");
    let rows = body.as_array().expect("grader list rows");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["Id"], 42);
    assert_eq!(rows[0]["CoilNo"], "LG-20260627-0042");
    assert_eq!(rows[0]["CoilType"], "Q235");
    assert_eq!(rows[0]["CoilInside"], 610.0);
    assert_eq!(rows[0]["CoilDia"], 1320.0);
    assert_eq!(rows[0]["Thickness"], 2.4);
    assert_eq!(rows[0]["Width"], 1250.0);
    assert_eq!(rows[0]["Weight"], 55.0);
    assert_eq!(rows[0]["ActWidth"], 1248.5);
    assert_eq!(rows[0]["CreateTime"]["year"], 2026);
    assert_eq!(rows[0]["childrenCoil"], json!([]));
    assert_eq!(rows[0]["Next"], "外委横切(配送)");
}

#[tokio::test]
async fn grader_list_datetime_object_serializes_in_python_field_order() {
    let response = request_response(app_with_grader_rows(), "GET", "/grader_list?count=1").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body =
        String::from_utf8(response_bytes(response).await.to_vec()).expect("grader list utf8");

    assert!(
        body.contains(
            r#""CreateTime":{"year":2026,"month":6,"weekday":5,"day":27,"hour":12,"minute":34,"second":56}"#
        ),
        "{body}"
    );
}

#[tokio::test]
async fn grader_list_secondary_coil_serializes_in_python_field_order() {
    let response = request_response(app_with_grader_rows(), "GET", "/grader_list?count=1").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body =
        String::from_utf8(response_bytes(response).await.to_vec()).expect("grader list utf8");

    assert_eq!(
        body,
        r#"[{"ActWidth":1248.5,"CoilNo":"LG-20260627-0042","CreateTime":{"year":2026,"month":6,"weekday":5,"day":27,"hour":12,"minute":34,"second":56},"CoilType":"Q235","CoilInside":610.0,"Id":42,"CoilDia":1320.0,"Thickness":2.4,"Width":1250.0,"Weight":55.0,"childrenCoil":[],"Next":"外委横切(配送)"}]"#
    );
}

#[tokio::test]
async fn grader_list_rounds_mysql_float_noise_like_python_json() {
    let response = request_response(app_with_grader_rows(), "GET", "/grader_list?count=2").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("grader list body");
    let rows = body.as_array().expect("grader list rows");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[1]["Id"], 41);
    assert_eq!(rows[1]["Thickness"], 2.3);
}

#[tokio::test]
async fn grader_list_invalid_count_returns_fastapi_query_validation_error() {
    let response = request_response(app_with_seed_data(), "GET", "/grader_list?count=abc").await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "count"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn coil_status_returns_python_default_when_missing() {
    let response =
        request_response(app_with_seed_data(), "GET", "/check/get_coil_status/193113").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body_bytes = response_bytes(response).await;
    assert_eq!(
        String::from_utf8(body_bytes.to_vec()).expect("coil status body text"),
        r#"{"status":0,"msg":"","secondaryCoilId":193113,"Id":-1}"#
    );
    let body: Value = serde_json::from_slice(&body_bytes).expect("coil status body");
    assert_eq!(
        body,
        json!({
            "status": 0,
            "msg": "",
            "secondaryCoilId": 193113,
            "Id": -1,
        })
    );
}

#[tokio::test]
async fn set_coil_status_upserts_and_get_returns_saved_status() {
    let app = app_with_seed_data();
    let set_response = request_response(
        app.clone(),
        "GET",
        "/check/set_coil_status/42/2/needs-review",
    )
    .await;
    let set_status = set_response.status();

    assert_eq!(set_status, StatusCode::OK);
    let set_body: Value =
        serde_json::from_slice(&response_bytes(set_response).await).expect("set status body");
    assert_eq!(set_body, Value::Null);

    let get_response = request_response(app, "GET", "/check/get_coil_status/42").await;
    let get_status = get_response.status();
    assert_eq!(get_status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(get_response).await).expect("coil status body");
    assert_eq!(body["status"], 2);
    assert_eq!(body["msg"], "needs-review");
    assert_eq!(body["secondaryCoilId"], 42);
    assert!(body["Id"].as_i64().unwrap_or_default() > 0);
}

#[tokio::test]
async fn coil_check_routes_reject_non_python_int_converter_paths_like_python() {
    for uri in [
        "/check/get_coil_status/abc",
        "/check/get_coil_status/-1",
        "/check/set_coil_status/abc/1",
        "/check/set_coil_status/-1/1",
        "/check/set_coil_status/1/abc",
        "/check/set_coil_status/1/-1",
        "/check/set_coil_status/1/abc/message",
        "/check/set_coil_status/1/-1/message",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn coil_state_endpoint_returns_python_field_shape_and_empty_array_when_missing() {
    let response = request_response(app_with_process_rows(), "GET", "/search/CoilState/42").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("coil state body");
    let rows = body.as_array().expect("coil state rows");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0]["Id"], 9);
    assert_eq!(rows[0]["secondaryCoilId"], 42);
    assert_eq!(rows[0]["surface"], "S");
    assert_eq!(rows[0]["scan3dCoordinateScaleX"], 0.3369);
    assert_eq!(rows[0]["scan3dCoordinateScaleZ"], 0.0162);
    assert_eq!(rows[0]["median_3d"], 57745.0);
    assert_eq!(rows[0]["median_3d_mm"], 936.9);
    assert_eq!(rows[0]["start"], 46917.7);
    assert_eq!(rows[0]["lowerArea_percent"], 0.007);
    assert_eq!(rows[0]["startTime"]["year"], 2026);
    assert_eq!(
        rows[0]
            .as_object()
            .expect("coil state object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "Id",
            "scan3dCoordinateScaleY",
            "start",
            "mask_area",
            "surface",
            "scan3dCoordinateScaleZ",
            "step",
            "width",
            "secondaryCoilId",
            "rotate",
            "upperLimit",
            "height",
            "x_rotate",
            "lowerLimit",
            "jsonData",
            "median_3d",
            "lowerArea",
            "median_3d_mm",
            "upperArea",
            "startTime",
            "colorFromValue_mm",
            "lowerArea_percent",
            "scan3dCoordinateScaleX",
            "colorToValue_mm",
            "upperArea_percent",
        ]
    );
    assert_eq!(rows[1]["surface"], "L");

    let (missing_status, missing_body) =
        request_json(app_with_process_rows(), "GET", "/search/CoilState/999").await;
    assert_eq!(missing_status, StatusCode::OK);
    assert_eq!(missing_body, json!([]));
}

#[tokio::test]
async fn process_data_routes_reject_non_python_int_converter_paths_like_python() {
    for uri in [
        "/search/CoilState/abc",
        "/search/CoilState/-1",
        "/search/PlcData/abc",
        "/search/PlcData/-1",
        "/get_point_data/abc/S",
        "/get_point_data/-1/S",
        "/get_line_data/abc/S",
        "/get_line_data/-1/S",
    ] {
        let response = request_response(app_with_process_rows(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn alarm_defect_image_and_camera_routes_reject_non_python_int_converter_paths_like_python() {
    for uri in [
        "/coilAlarm/abc",
        "/coilAlarm/-1",
        "/search/defects/abc/S",
        "/search/defects/-1/S",
        "/search/getDefectAll/abc/1",
        "/search/getDefectAll/-1/1",
        "/search/getDefectAll/1/abc",
        "/search/getDefectAll/1/-1",
        "/search/defects_all/abc/S",
        "/search/defects_all/-1/S",
        "/manual_defects/abc/S",
        "/manual_defects/-1/S",
        "/classifier_image/abc/S/class/1/2/3/4",
        "/classifier_image/-1/S/class/1/2/3/4",
        "/defect_image/S/abc/GRAY/1/2/3/4",
        "/defect_image/S/-1/GRAY/1/2/3/4",
        "/clipMaxImage/abc/S",
        "/clipMaxImage/-1/S",
        "/cameraData/abc/S_D",
        "/cameraData/-1/S_D",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn plc_data_endpoint_returns_python_field_shape_and_null_when_missing() {
    let response = request_response(app_with_process_rows(), "GET", "/search/PlcData/42").await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc data body");
    assert_eq!(body["Id"], 12);
    assert_eq!(body["secondaryCoilId"], 42);
    assert_eq!(body["location_S"], 123.4);
    assert_eq!(body["location_L"], 456.7);
    assert_eq!(body["location_laser"], 89.1);
    assert_eq!(body["startTime"]["year"], 2026);
    assert_eq!(body["pclData"], "{\"source\":\"unit-test\"}");

    let (missing_status, missing_body) =
        request_json(app_with_process_rows(), "GET", "/search/PlcData/999").await;
    assert_eq!(missing_status, StatusCode::OK);
    assert_eq!(missing_body, Value::Null);
}

#[tokio::test]
async fn point_data_endpoint_returns_python_field_names_filtered_by_surface() {
    let (status, body) =
        request_json(app_with_point_line_rows(), "GET", "/get_point_data/42/S").await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("point rows");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0]["Id"], 1);
    assert_eq!(rows[0]["secondaryCoilId"], 42);
    assert_eq!(rows[0]["surface"], "S");
    assert_eq!(rows[0]["type"], "outer");
    assert_eq!(rows[0]["x"], 11.0);
    assert_eq!(rows[0]["y"], 22.0);
    assert_eq!(rows[0]["z"], 33.0);
    assert_eq!(rows[0]["z_mm"], -6.69945);
    assert_eq!(rows[0]["crateTime"]["year"], 2026);
    assert_eq!(
        rows[0]
            .as_object()
            .expect("point data object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "secondaryCoilId",
            "surface",
            "x",
            "z",
            "data",
            "type",
            "Id",
            "y",
            "z_mm",
            "crateTime",
        ]
    );
    assert_eq!(rows[1]["Id"], 2);
    assert_eq!(rows[1]["type"], "inner");
    assert_eq!(rows[1]["data"], "{\"label\":\"A\"}");

    let (_, missing_body) =
        request_json(app_with_point_line_rows(), "GET", "/get_point_data/999/S").await;
    assert_eq!(missing_body, json!([]));
}

#[tokio::test]
async fn line_data_endpoint_returns_python_field_names_filtered_by_surface() {
    let (status, body) =
        request_json(app_with_point_line_rows(), "GET", "/get_line_data/42/S").await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("line rows");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["Id"], 4);
    assert_eq!(rows[0]["secondaryCoilId"], 42);
    assert_eq!(rows[0]["surface"], "S");
    assert_eq!(rows[0]["type"], "diameter");
    assert_eq!(rows[0]["center_x"], 100.0);
    assert_eq!(rows[0]["center_y"], 200.0);
    assert_eq!(rows[0]["width"], 300.0);
    assert_eq!(rows[0]["height"], 20.0);
    assert_eq!(rows[0]["rotation_angle"], 1.5);
    assert_eq!(rows[0]["x1"], 10.0);
    assert_eq!(rows[0]["y1"], 20.0);
    assert_eq!(rows[0]["x2"], 110.0);
    assert_eq!(rows[0]["y2"], 120.0);
    assert_eq!(rows[0]["data"], "[1,2,3]");
    assert_eq!(rows[0]["inner_min_value"], 12.0);
    assert_eq!(rows[0]["inner_min_value_mm"], 1.2);
    assert_eq!(rows[0]["outer_max_value"], 42.0);
    assert_eq!(rows[0]["outer_max_value_mm"], 1.40666);
    assert_eq!(rows[0]["crateTime"]["minute"], 41);
    assert_eq!(
        rows[0]
            .as_object()
            .expect("line data object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "width",
            "inner_min_value",
            "outer_max_value_mm",
            "height",
            "inner_min_value_mm",
            "crateTime",
            "secondaryCoilId",
            "rotation_angle",
            "inner_max_value",
            "surface",
            "x1",
            "inner_max_value_mm",
            "Id",
            "y1",
            "outer_min_value",
            "type",
            "x2",
            "outer_min_value_mm",
            "center_x",
            "y2",
            "outer_max_value",
            "center_y",
            "data",
        ]
    );

    let (_, missing_body) =
        request_json(app_with_point_line_rows(), "GET", "/get_line_data/42/X").await;
    assert_eq!(missing_body, json!([]));
}

#[tokio::test]
async fn plc_curve_endpoint_returns_python_field_items_and_invalid_field_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/plc_curve/location_S?limit=1",
    )
    .await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve body");
    assert_eq!(body["field"], "location_S");
    let items = body["items"].as_array().expect("plc curve items");
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["coil_id"], 42);
    assert_eq!(items[0]["time"], "2026-06-27T12:36:00");
    assert_eq!(items[0]["value"], 123.4);

    let (invalid_status, invalid_body) = request_json(
        app_with_process_rows(),
        "GET",
        "/plc_curve/location_X?limit=1",
    )
    .await;
    assert_eq!(invalid_status, StatusCode::OK);
    assert_eq!(
        invalid_body,
        json!({
            "field": "location_X",
            "items": [],
            "error": "invalid field",
        })
    );
}

#[tokio::test]
async fn plc_curve_invalid_start_id_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/plc_curve/location_S?start_id=abc&limit=1",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "start_id"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn plc_curve_negative_limit_clamps_to_python_minimum_one() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/plc_curve/location_S?limit=-1",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve body");
    assert_eq!(body["field"], "location_S");
    let items = body["items"].as_array().expect("plc curve items");
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["coil_id"], 42);
    assert_eq!(items[0]["value"], 123.4);
}

#[tokio::test]
async fn plc_curve_negative_start_id_uses_python_filtered_ascending_window() {
    let response = request_response(
        app_with_plc_curve_range_rows(),
        "GET",
        "/plc_curve/location_S?start_id=-1&limit=2",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve body");
    let items = body["items"].as_array().expect("plc curve items");
    assert_eq!(items.len(), 2);
    assert_eq!(items[0]["coil_id"], 10);
    assert_eq!(items[1]["coil_id"], 20);
}

#[tokio::test]
async fn plc_curve_all_endpoint_merges_latest_plc_state_and_width_values() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/plc_curve_all?start_id=42&end_id=42&limit=10",
    )
    .await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve all body");
    let items = body["items"].as_array().expect("plc curve all items");
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["coil_id"], 42);
    assert_eq!(items[0]["time"], "2026-06-27T12:36:00");
    assert_eq!(items[0]["location_S"], 123.4);
    assert_eq!(items[0]["location_L"], 456.7);
    assert_eq!(items[0]["location_laser"], 89.1);
    assert_eq!(items[0]["median_3d_mm_S"], 936.9);
    assert_eq!(items[0]["median_3d_mm_L"], 899.5);
    assert_eq!(items[0]["median_3d_mm_avg"], 918.2);
    assert_eq!(items[0]["width_"], 1248.5);
}

#[tokio::test]
async fn plc_curve_all_negative_limit_clamps_to_python_minimum_one() {
    let response =
        request_response(app_with_process_rows(), "GET", "/plc_curve_all?limit=-1").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve all body");
    let items = body["items"].as_array().expect("plc curve all items");
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["coil_id"], 42);
    assert_eq!(items[0]["width_"], 1248.5);
}

#[tokio::test]
async fn plc_curve_all_negative_start_id_uses_python_filtered_ascending_window() {
    let response = request_response(
        app_with_plc_curve_range_rows(),
        "GET",
        "/plc_curve_all?start_id=-1&limit=2",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("plc curve all body");
    let items = body["items"].as_array().expect("plc curve all items");
    assert_eq!(items.len(), 2);
    assert_eq!(items[0]["coil_id"], 10);
    assert_eq!(items[1]["coil_id"], 20);
}

#[tokio::test]
async fn plc_curve_all_invalid_start_id_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/plc_curve_all?start_id=abc&limit=1",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "start_id"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_list_query_parameters_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let coil_list = &body["paths"]["/coilList/{number}"]["get"];

    assert_eq!(
        coil_list["parameters"],
        json!([
            {
                "name": "number",
                "in": "path",
                "required": true,
                "schema": {"type": "integer", "title": "Number"}
            },
            {
                "name": "coil_id",
                "in": "query",
                "required": false,
                "schema": {"title": "Coil Id"}
            },
            {
                "name": "rev",
                "in": "query",
                "required": false,
                "schema": {"default": true, "title": "Rev"}
            }
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_common_query_parameters_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/grader_list"]["get"]["parameters"],
        json!([
            {
                "name": "count",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 100, "title": "Count"}
            }
        ])
    );
    assert_eq!(
        body["paths"]["/speedtest/download"]["get"]["parameters"],
        json!([
            {
                "name": "size_in_mb",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 10, "title": "Size In Mb"}
            }
        ])
    );
    assert_eq!(
        body["paths"]["/plc_curve_all"]["get"]["parameters"],
        json!([
            {
                "name": "start_id",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "Start Id"}
            },
            {
                "name": "end_id",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "End Id"}
            },
            {
                "name": "limit",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 200, "title": "Limit"}
            }
        ])
    );
    assert_eq!(
        body["paths"]["/plc_curve/{field}"]["get"]["parameters"],
        json!([
            {
                "name": "field",
                "in": "path",
                "required": true,
                "schema": {"type": "string", "title": "Field"}
            },
            {
                "name": "start_id",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "Start Id"}
            },
            {
                "name": "end_id",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 0, "title": "End Id"}
            },
            {
                "name": "limit",
                "in": "query",
                "required": false,
                "schema": {"type": "integer", "default": 200, "title": "Limit"}
            }
        ])
    );
    assert_eq!(
        body["paths"]["/control/set_property"]["get"]["parameters"],
        json!([
            {
                "name": "key",
                "in": "query",
                "required": true,
                "schema": {"title": "Key"}
            },
            {
                "name": "value",
                "in": "query",
                "required": true,
                "schema": {"title": "Value"}
            }
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_render_query_parameters_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let render = &body["paths"]["/coilData/Render/{surfaceKey}/{coil_id}"]["get"];

    assert_eq!(
        render["parameters"],
        json!([
            {
                "name": "surfaceKey",
                "in": "path",
                "required": true,
                "schema": {"type": "string", "title": "Surfacekey"}
            },
            {
                "name": "coil_id",
                "in": "path",
                "required": true,
                "schema": {"type": "string", "title": "Coil Id"}
            },
            {
                "name": "scale",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "number",
                    "description": "缩放比例",
                    "default": 1.0,
                    "title": "Scale"
                },
                "description": "缩放比例"
            },
            {
                "name": "mask",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "boolean",
                    "description": "是否应用掩码",
                    "default": true,
                    "title": "Mask"
                },
                "description": "是否应用掩码"
            },
            {
                "name": "min_value",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "integer",
                    "description": "最小值",
                    "default": 0,
                    "title": "Min Value"
                },
                "description": "最小值"
            },
            {
                "name": "max_value",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "integer",
                    "description": "最大值",
                    "default": 255,
                    "title": "Max Value"
                },
                "description": "最大值"
            },
            {
                "name": "minValue",
                "in": "query",
                "required": false,
                "schema": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "description": "兼容 QML 旧参数：最小值",
                    "title": "Minvalue"
                },
                "description": "兼容 QML 旧参数：最小值"
            },
            {
                "name": "maxValue",
                "in": "query",
                "required": false,
                "schema": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "description": "兼容 QML 旧参数：最大值",
                    "title": "Maxvalue"
                },
                "description": "兼容 QML 旧参数：最大值"
            },
            {
                "name": "thumbnail",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "boolean",
                    "description": "是否返回缩略图（1024x1024）",
                    "default": false,
                    "title": "Thumbnail"
                },
                "description": "是否返回缩略图（1024x1024）"
            },
            {
                "name": "grayscale",
                "in": "query",
                "required": false,
                "schema": {
                    "type": "boolean",
                    "description": "是否使用灰度模式（GRAY）而非伪彩色（JET）",
                    "default": false,
                    "title": "Grayscale"
                },
                "description": "是否使用灰度模式（GRAY）而非伪彩色（JET）"
            }
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_image_query_parameters_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/coilData/Area/{surface_key}/{coil_id}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"scale","in":"query","required":false,"schema":{"default":1,"title":"Scale"}},
            {"name":"mask","in":"query","required":false,"schema":{"type":"boolean","default":true,"title":"Mask"}},
            {"name":"valueFrom","in":"query","required":false,"schema":{"default":0,"title":"Valuefrom"}},
            {"name":"valueTo","in":"query","required":false,"schema":{"default":255,"title":"Valueto"}},
            {"name":"r","in":"query","required":false,"schema":{"default":255,"title":"R"}},
            {"name":"g","in":"query","required":false,"schema":{"default":0,"title":"G"}},
            {"name":"b","in":"query","required":false,"schema":{"default":0,"title":"B"}}
        ])
    );
    assert_eq!(
        body["paths"]["/coilData/Error/{surface_key}/{coil_id}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"type":"string","title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"scale","in":"query","required":false,"schema":{"type":"number","default":1.0,"title":"Scale"}},
            {"name":"mask","in":"query","required":false,"schema":{"type":"boolean","default":true,"title":"Mask"}},
            {"name":"minValue","in":"query","required":false,"schema":{"type":"number","default":0,"title":"Minvalue"}},
            {"name":"maxValue","in":"query","required":false,"schema":{"type":"number","default":255,"title":"Maxvalue"}},
            {"name":"force_cache","in":"query","required":false,"schema":{"type":"boolean","default":false,"title":"Force Cache"}}
        ])
    );
    assert_eq!(
        body["paths"]["/image/preview/{surface_key}/{coil_id}/{type_}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"type_","in":"path","required":true,"schema":{"type":"string","title":"Type "}},
            {"name":"mask","in":"query","required":false,"schema":{"type":"boolean","default":false,"title":"Mask"}}
        ])
    );
    assert_eq!(
        body["paths"]["/image/source/{surface_key}/{coil_id}/{type_}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"type_","in":"path","required":true,"schema":{"type":"string","title":"Type "}},
            {"name":"mask","in":"query","required":false,"schema":{"type":"boolean","default":false,"title":"Mask"}}
        ])
    );
    assert_eq!(
        body["paths"]["/image/area/{surface_key}/{coil_id}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"type":"string","title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"type_","in":"query","required":false,"schema":{"type":"string","default":"AREA","title":"Type "}},
            {"name":"row","in":"query","required":false,"schema":{"type":"integer","maximum":2,"minimum":-2,"description":"瓦片行索引","default":0,"title":"Row"},"description":"瓦片行索引"},
            {"name":"col","in":"query","required":false,"schema":{"type":"integer","maximum":2,"minimum":0,"description":"瓦片列索引","default":0,"title":"Col"},"description":"瓦片列索引"},
            {"name":"count","in":"query","required":false,"schema":{"type":"integer","maximum":3,"minimum":0,"description":"瓦片行列数","default":0,"title":"Count"},"description":"瓦片行列数"},
            {"name":"level","in":"query","required":false,"schema":{"type":"integer","maximum":4,"minimum":0,"description":"瓦片质量等级 0-4","default":4,"title":"Level"},"description":"瓦片质量等级 0-4"}
        ])
    );
    assert_eq!(
        body["paths"]["/image/area/{surface_key}/{coil_id}/{type_}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"type":"string","title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"string","title":"Coil Id"}},
            {"name":"type_","in":"path","required":true,"schema":{"type":"string","title":"Type "}},
            {"name":"row","in":"query","required":false,"schema":{"type":"integer","maximum":2,"minimum":-2,"description":"瓦片行索引","default":0,"title":"Row"},"description":"瓦片行索引"},
            {"name":"col","in":"query","required":false,"schema":{"type":"integer","maximum":2,"minimum":0,"description":"瓦片列索引","default":0,"title":"Col"},"description":"瓦片列索引"},
            {"name":"count","in":"query","required":false,"schema":{"type":"integer","maximum":3,"minimum":0,"description":"瓦片行列数","default":0,"title":"Count"},"description":"瓦片行列数"},
            {"name":"level","in":"query","required":false,"schema":{"type":"integer","maximum":4,"minimum":0,"description":"瓦片质量等级 0-4","default":4,"title":"Level"},"description":"瓦片质量等级 0-4"}
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_remaining_get_parameters_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/check/get_coil_status/{coil_id}"]["get"]["parameters"],
        json!([
            {"name":"coil_id","in":"path","required":true,"schema":{"title":"Coil Id"}}
        ])
    );
    assert_eq!(
        body["paths"]["/check/set_coil_status/{coil_id}/{status}"]["get"]["parameters"],
        json!([
            {"name":"coil_id","in":"path","required":true,"schema":{"title":"Coil Id"}},
            {"name":"status","in":"path","required":true,"schema":{"title":"Status"}},
            {"name":"msg","in":"query","required":false,"schema":{"default":"","title":"Msg"}}
        ])
    );
    assert_eq!(
        body["paths"]["/check/set_coil_status/{coil_id}/{status}/{msg}"]["get"]["parameters"],
        json!([
            {"name":"coil_id","in":"path","required":true,"schema":{"title":"Coil Id"}},
            {"name":"status","in":"path","required":true,"schema":{"title":"Status"}},
            {"name":"msg","in":"path","required":true,"schema":{"title":"Msg"}}
        ])
    );
    assert_eq!(
        body["paths"]["/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}"]["get"]["parameters"],
        json!([
            {"name":"surface_key","in":"path","required":true,"schema":{"title":"Surface Key"}},
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"integer","title":"Coil Id"}},
            {"name":"type_","in":"path","required":true,"schema":{"type":"string","title":"Type "}},
            {"name":"x","in":"path","required":true,"schema":{"type":"string","title":"X"}},
            {"name":"y","in":"path","required":true,"schema":{"type":"string","title":"Y"}},
            {"name":"w","in":"path","required":true,"schema":{"type":"string","title":"W"}},
            {"name":"h","in":"path","required":true,"schema":{"type":"string","title":"H"}}
        ])
    );
    for path in [
        "/exportXlsxByDateTime/{start}/{end}",
        "/exportXlsxById/{start}/{end}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["parameters"],
            json!([
                {"name":"start","in":"path","required":true,"schema":{"title":"Start"}},
                {"name":"end","in":"path","required":true,"schema":{"title":"End"}},
                {"name":"export_type","in":"query","required":false,"schema":{"default":"3D","title":"Export Type"}},
                {"name":"export_config","in":"query","required":false,"schema":{"title":"Export Config"}}
            ])
        );
    }
    assert_eq!(
        body["paths"]["/search/getDefectAll/{start_coil_id}/{end_coil_id}"]["get"]["parameters"],
        json!([
            {"name":"start_coil_id","in":"path","required":true,"schema":{"title":"Start Coil Id"}},
            {"name":"end_coil_id","in":"path","required":true,"schema":{"title":"End Coil Id"}}
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_json_mutation_request_bodies_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    for path in [
        "/alg_2d/test/start",
        "/control/set_config",
        "/export_defects",
        "/manual_defect/add",
        "/setDefectDict",
    ] {
        let title = match path {
            "/alg_2d/test/start" => "Payload",
            "/control/set_config" | "/setDefectDict" => "Data",
            _ => "Request",
        };
        assert_eq!(
            body["paths"][path]["post"]["requestBody"],
            json!({
                "content": {
                    "application/json": {
                        "schema": {
                            "additionalProperties": true,
                            "type": "object",
                            "title": title
                        }
                    }
                },
                "required": true
            })
        );
    }

    assert_eq!(
        body["paths"]["/alg_2d/test/stop"]["post"]["requestBody"],
        json!({
            "content": {
                "application/json": {
                    "schema": {
                        "anyOf": [
                            {"additionalProperties": true, "type": "object"},
                            {"type": "null"}
                        ],
                        "title": "Payload"
                    }
                }
            }
        })
    );
    assert_eq!(
        body["paths"]["/manual_defect/update/{defect_id}"]["put"]["requestBody"],
        json!({
            "required": true,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "additionalProperties": true,
                        "title": "Request"
                    }
                }
            }
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_typed_request_bodies_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/camera_adjust/{camera_key}"]["post"]["requestBody"],
        json!({
            "required": true,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/CameraAdjustmentPayload"}
                }
            }
        })
    );
    assert_eq!(
        body["paths"]["/export_xlsx"]["post"]["requestBody"],
        json!({
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ExportXlsxConfigModel"}
                }
            },
            "required": true
        })
    );
    assert_eq!(
        body["paths"]["/settings/test_mode"]["post"]["requestBody"],
        json!({
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/TestModeRequest"}
                }
            },
            "required": true
        })
    );
    assert_eq!(
        body["paths"]["/speedtest/upload"]["post"]["requestBody"],
        json!({
            "content": {
                "multipart/form-data": {
                    "schema": {"$ref": "#/components/schemas/Body_upload_test_speedtest_upload_post"}
                }
            },
            "required": true
        })
    );

    assert_eq!(
        body["components"]["schemas"]["CameraAdjustmentPayload"],
        json!({
            "properties": {
                "exposureTime": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Exposuretime"
                },
                "gain": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Gain"
                },
                "save": {"type": "boolean", "title": "Save", "default": true}
            },
            "type": "object",
            "title": "CameraAdjustmentPayload"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["ExportXlsxConfigModel"],
        json!({
            "properties": {
                "export_type": {"type": "string", "title": "Export Type"},
                "detection_3d_info": {"type": "boolean", "title": "Detection 3D Info"},
                "defect_info": {"type": "boolean", "title": "Defect Info"},
                "defect_show_info": {"type": "boolean", "title": "Defect Show Info"},
                "defect_un_show_info": {"type": "boolean", "title": "Defect Un Show Info"},
                "area_defect_image": {"type": "boolean", "title": "Area Defect Image", "default": true},
                "export_plc_data": {"type": "boolean", "title": "Export Plc Data"},
                "startDate": {"type": "string", "title": "Startdate"},
                "endDate": {"type": "string", "title": "Enddate"}
            },
            "type": "object",
            "required": [
                "export_type",
                "detection_3d_info",
                "defect_info",
                "defect_show_info",
                "defect_un_show_info",
                "export_plc_data",
                "startDate",
                "endDate"
            ],
            "title": "ExportXlsxConfigModel"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["TestModeRequest"],
        json!({
            "properties": {
                "enabled": {"type": "boolean", "title": "Enabled"}
            },
            "type": "object",
            "required": ["enabled"],
            "title": "TestModeRequest"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["Body_upload_test_speedtest_upload_post"],
        json!({
            "properties": {
                "file": {
                    "type": "string",
                    "contentMediaType": "application/octet-stream",
                    "title": "File"
                }
            },
            "type": "object",
            "required": ["file"],
            "title": "Body_upload_test_speedtest_upload_post"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_test_mode_response_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/settings/test_mode"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/TestModeResponse"})
    );
    assert_eq!(
        body["paths"]["/settings/test_mode"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/SetTestModeResponse"})
    );
    assert_eq!(
        body["paths"]["/settings/test_mode_status"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/TestModeStatusResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["TestModeResponse"],
        json!({
            "properties": {
                "test_mode": {"type": "boolean", "title": "Test Mode"}
            },
            "type": "object",
            "required": ["test_mode"],
            "title": "TestModeResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["SetTestModeResponse"],
        json!({
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "test_mode": {"type": "boolean", "title": "Test Mode"}
            },
            "type": "object",
            "required": ["status", "test_mode"],
            "title": "SetTestModeResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["TestModeStatusResponse"],
        json!({
            "properties": {
                "config_file_exists": {"type": "boolean", "title": "Config File Exists"},
                "config_file_value": {"type": "boolean", "title": "Config File Value"},
                "developer_mode": {"type": "boolean", "title": "Developer Mode"},
                "is_local": {"type": "boolean", "title": "Is Local"},
                "config_file_path": {"type": "string", "title": "Config File Path"}
            },
            "type": "object",
            "required": [
                "config_file_exists",
                "config_file_value",
                "developer_mode",
                "is_local",
                "config_file_path"
            ],
            "title": "TestModeStatusResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_runtime_info_response_contract_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/runtime_info"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/RuntimeInfoResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["RuntimeInfoResponse"],
        json!({
            "properties": {
                "python_version": {"type": "string", "title": "Python Version"},
                "cache_mode": {"type": "string", "title": "Cache Mode"},
                "cpu_model": {"type": "string", "title": "Cpu Model"},
                "gpus": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Gpus"
                },
                "is_local": {"type": "boolean", "title": "Is Local"},
                "developer_mode": {"type": "boolean", "title": "Developer Mode"},
                "offline_mode": {"type": "boolean", "title": "Offline Mode"}
            },
            "type": "object",
            "required": [
                "python_version",
                "cache_mode",
                "cpu_model",
                "gpus",
                "is_local",
                "developer_mode",
                "offline_mode"
            ],
            "title": "RuntimeInfoResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_camera_and_hardware_status_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/hardware"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/HardwareStatusResponse"})
    );
    assert_eq!(
        body["paths"]["/camera_adjust"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/CameraAdjustmentStatusResponse"})
    );
    assert_eq!(
        body["paths"]["/cameraAlarm"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/CameraAlarmResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["HardwareStatusResponse"]["required"],
        json!(["cpu", "memory", "disk", "gpu"])
    );
    assert_eq!(
        body["components"]["schemas"]["HardwareStatusItem"]["required"],
        json!(["key", "value", "msg", "level"])
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAdjustmentStatusResponse"]["required"],
        json!([
            "configFile",
            "captureServiceUrl",
            "captureStatus",
            "cameras"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAdjustmentStatusResponse"]["properties"]["cameras"],
        json!({
            "items": {"$ref": "#/components/schemas/CameraAdjustmentItem"},
            "type": "array",
            "title": "Cameras"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAdjustmentItem"]["required"],
        json!([
            "key",
            "name",
            "sn",
            "serverIp",
            "serverPort",
            "yamlConfig",
            "serviceUrl",
            "legacyServiceUrl",
            "status"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAdjustmentRuntimeStatus"]["properties"]["capture"],
        json!({"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"})
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAlarmResponse"]["additionalProperties"],
        json!({"$ref": "#/components/schemas/CameraAlarmItem"})
    );
    assert_eq!(
        body["components"]["schemas"]["CameraAlarmItem"]["required"],
        json!([
            "DeviceTemperature",
            "level",
            "msg",
            "connected",
            "ok",
            "captureOk",
            "lastFrameAge",
            "lastError2D",
            "lastError3D",
            "serviceUrl",
            "cameraKey",
            "cameraName"
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_capture_status_and_camera_action_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/capture_status"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/CaptureStatusResponse"})
    );
    assert_eq!(
        body["paths"]["/camera_adjust/{camera_key}"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/CameraActionResponse"})
    );
    assert_eq!(
        body["paths"]["/camera_adjust/{camera_key}/reconnect"]["post"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/CameraActionResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["CaptureStatusResponse"]["required"],
        json!(["ok"])
    );
    assert_eq!(
        body["components"]["schemas"]["CaptureStatusResponse"]["properties"]["cameras"],
        json!({
            "items": {"$ref": "#/components/schemas/CaptureStatusCamera"},
            "type": "array",
            "title": "Cameras"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CaptureStatusCamera"]["required"],
        json!(["key"])
    );
    assert_eq!(
        body["components"]["schemas"]["CaptureStatusCamera"]["properties"]["status"],
        json!({"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"})
    );
    assert_eq!(
        body["components"]["schemas"]["CameraActionResponse"]["properties"]["ok"],
        json!({"type": "boolean", "title": "Ok"})
    );
    assert_eq!(
        body["components"]["schemas"]["CameraActionResponse"]["additionalProperties"],
        json!(true)
    );
}

#[tokio::test]
async fn openapi_json_describes_startup_info_response_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/RootResponse"})
    );
    assert_eq!(
        body["paths"]["/version"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"type": "string", "title": "Version"})
    );
    assert_eq!(
        body["paths"]["/delay"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"type": "integer", "title": "Delay"})
    );
    assert_eq!(
        body["paths"]["/database_info"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/DatabaseInfoResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["RootResponse"]["required"],
        json!(["/docs"])
    );
    assert_eq!(
        body["components"]["schemas"]["RootResponse"]["properties"]["/docs"],
        json!({"type": "string", "title": "Docs"})
    );
    assert_eq!(
        body["components"]["schemas"]["DatabaseInfoResponse"]["required"],
        json!(["url", "echo", "coil_last"])
    );
    assert_eq!(
        body["components"]["schemas"]["DatabaseInfoResponse"]["properties"]["url"],
        json!({"$ref": "#/components/schemas/DatabaseUrlInfo"})
    );
    assert_eq!(
        body["components"]["schemas"]["DatabaseInfoResponse"]["properties"]["coil_last"],
        json!({
            "anyOf": [
                {"type": "object", "additionalProperties": true},
                {"type": "null"}
            ],
            "title": "Coil Last"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["DatabaseUrlInfo"]["prefixItems"],
        json!([
            {"type": "string", "title": "Driver"},
            {"type": "string", "title": "Username"},
            {"type": "string", "title": "Password"},
            {"type": "string", "title": "Host"},
            {"type": "integer", "title": "Port"},
            {"type": "string", "title": "Database"},
            {"type": "object", "title": "Query", "additionalProperties": true}
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_info_response_contract_for_qml_tauri_startup() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/info"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/InfoResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["InfoResponse"]["required"],
        json!([
            "ErrorMap",
            "RendererList",
            "ColorMaps",
            "SaveImageType",
            "PreviewSize"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["InfoResponse"]["properties"]["ErrorMap"],
        json!({"$ref": "#/components/schemas/InfoErrorMap"})
    );
    assert_eq!(
        body["components"]["schemas"]["InfoResponse"]["properties"]["RendererList"],
        json!({
            "items": {"type": "string"},
            "type": "array",
            "title": "Rendererlist"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["InfoResponse"]["properties"]["PreviewSize"],
        json!({
            "prefixItems": [
                {"type": "integer", "title": "Width"},
                {"type": "integer", "title": "Height"}
            ],
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "title": "Previewsize"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["InfoResponse"]["properties"]["surfaceS"],
        json!({"$ref": "#/components/schemas/InfoSurface"})
    );
    assert_eq!(
        body["components"]["schemas"]["InfoSurface"]["required"],
        json!(["key", "saveFolder", "folderList"])
    );
    assert_eq!(
        body["components"]["schemas"]["InfoSurface"]["properties"]["folderList"],
        json!({
            "items": {"$ref": "#/components/schemas/InfoSurfaceFolder"},
            "type": "array",
            "title": "Folderlist"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["InfoSurfaceFolder"]["required"],
        json!(["cameraKey", "source"])
    );
}

#[tokio::test]
async fn openapi_json_describes_defect_dictionary_response_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/defectDict"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/DefectDictionaryResponse"})
    );
    assert_eq!(
        body["paths"]["/defectDictAll"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/DefectDictionaryRow"},
            "type": "array",
            "title": "Response Get Defect Dict All Defectdictall Get"
        })
    );
    assert_eq!(
        body["paths"]["/setDefectDict"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/SetDefectDictionaryResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["DefectDictionaryResponse"]["required"],
        json!(["data", "default"])
    );
    assert_eq!(
        body["components"]["schemas"]["DefectDictionaryResponse"]["properties"]["data"],
        json!({
            "type": "object",
            "additionalProperties": {"$ref": "#/components/schemas/DefectDictionaryEntry"},
            "title": "Data"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["DefectDictionaryEntry"]["required"],
        json!(["level", "color", "show"])
    );
    assert_eq!(
        body["components"]["schemas"]["DefectDictionaryRow"]["required"],
        json!([
            "Id",
            "defectClass",
            "defectName",
            "defectType",
            "defectColor",
            "defectLevel",
            "visible",
            "defectDesc"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["SetDefectDictionaryResponse"]["required"],
        json!(["status", "count"])
    );
}

#[tokio::test]
async fn openapi_json_describes_control_config_response_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/control/config"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/ControlConfigResponse"})
    );
    assert_eq!(
        body["paths"]["/control/set_config"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"type": "null"})
    );
    assert_eq!(
        body["paths"]["/control/set_property"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"type": "null"})
    );
    assert_eq!(
        body["components"]["schemas"]["ControlConfigResponse"],
        json!({
            "type": "object",
            "additionalProperties": true,
            "title": "ControlConfigResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_check_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/check/get_coil_status/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/CoilCheckResponse"})
    );
    assert_eq!(
        body["paths"]["/check/set_coil_status/{coil_id}/{status}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"type": "null"})
    );
    assert_eq!(
        body["paths"]["/check/set_coil_status/{coil_id}/{status}/{msg}"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"],
        json!({"type": "null"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilCheckResponse"],
        json!({
            "type": "object",
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "status": {"type": "integer", "title": "Status"},
                "msg": {"type": "string", "title": "Msg"}
            },
            "required": ["Id", "secondaryCoilId", "status", "msg"],
            "title": "CoilCheckResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_startup_data_presence_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/coil_list_value_change_keys"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "items": {"type": "string"},
            "type": "array",
            "title": "Response Coil List Value Change Keys Coil List Value Change Keys Get"
        })
    );
    assert_eq!(
        body["paths"]["/data_has/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/DataHasResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["DataHasResponse"],
        json!({
            "type": "object",
            "additionalProperties": {"$ref": "#/components/schemas/DataHasSurfaceFlags"},
            "title": "DataHasResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["DataHasSurfaceFlags"],
        json!({
            "properties": {
                "3D": {"type": "boolean", "title": "3D"},
                "MESH": {"type": "boolean", "title": "Mesh"},
                "JPG": {"type": "boolean", "title": "Jpg"},
                "2D": {"type": "boolean", "title": "2D"}
            },
            "type": "object",
            "required": ["3D", "MESH", "JPG", "2D"],
            "title": "DataHasSurfaceFlags"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_list_and_flush_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/coilList/{number}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
            "type": "array",
            "title": "Response Get Coil Coillist  Number  Get"
        })
    );
    assert_eq!(
        body["paths"]["/flush/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/FlushCoilListResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["FlushCoilListResponse"]["properties"]["coilList"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
            "type": "array",
            "title": "Coillist"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["required"],
        json!([
            "Id",
            "CoilNo",
            "CreateTime",
            "CoilType",
            "CoilInside",
            "CoilDia",
            "Thickness",
            "Width",
            "Weight",
            "ActWidth",
            "NextCode",
            "NextInfo",
            "hasCoil",
            "hasAlarmInfo",
            "AlarmInfo",
            "DefectCountS",
            "DefectCountL",
            "DetectionTime",
            "CheckStatus",
            "Status_L",
            "Status_S",
            "Grade",
            "Msg",
            "childrenCoil",
            "childrenAlarmInfo",
            "childrenCoilDefect",
            "maxDefectName",
            "maxDefectLevel",
            "maxDefectSurface",
            "childrenCoilCheck"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["properties"]["AlarmInfo"],
        json!({"$ref": "#/components/schemas/CoilSummaryAlarmInfo"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["properties"]["childrenCoil"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilSummaryChildCoil"},
            "type": "array",
            "title": "Childrencoil"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["properties"]["childrenCoilDefect"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilSummaryDefect"},
            "type": "array",
            "title": "Childrencoildefect"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryAlarmInfo"]["required"],
        json!(["S", "L"])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryAlarmSurface"]["required"],
        json!([
            "secondaryCoilId",
            "surface",
            "defectGrad",
            "taperShapeGrad",
            "looseCoilGrad",
            "flatRollGrad",
            "grad",
            "nextCode",
            "nextName",
            "createTime",
            "taperShapeMsg",
            "looseCoilMsg",
            "flatRollMsg",
            "defectMsg"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryDefect"]["required"],
        json!([
            "Id",
            "secondaryCoilId",
            "surface",
            "defectName",
            "defectLevel",
            "defectClass",
            "defectStatus",
            "defectX",
            "defectY",
            "defectW",
            "defectH",
            "defectSource",
            "is_area"
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_search_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let expected_summary_array = json!({
        "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
        "type": "array",
        "title": "Response Coil Summary List"
    });

    for path in [
        "/search/coilId/{coil_id}",
        "/search/coilNo/{coil_no}",
        "/search/DateTime/{start}/{end}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
            expected_summary_array,
            "{path}"
        );
    }
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["properties"]["Id"],
        json!({"type": "integer", "title": "Id"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryItem"]["properties"]["AlarmInfo"],
        json!({"$ref": "#/components/schemas/CoilSummaryAlarmInfo"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilSummaryAlarmInfo"]["properties"]["S"],
        json!({"$ref": "#/components/schemas/CoilSummaryAlarmSurface"})
    );
}

#[tokio::test]
async fn openapi_json_describes_detail_response_contract_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/detail/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilDetailResponse"},
                {"$ref": "#/components/schemas/ErrorMessageResponse"}
            ],
            "title": "Response Get Coil Detail Api Detail  Coil Id  Get"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["ErrorMessageResponse"],
        json!({
            "properties": {
                "error": {"type": "string", "title": "Error"}
            },
            "type": "object",
            "required": ["error"],
            "title": "ErrorMessageResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailResponse"]["required"],
        json!([
            "hasCoil",
            "hasAlarmInfo",
            "AlarmInfo",
            "SecondaryCoilId",
            "DetectionTime",
            "DefectCountL",
            "Status_L",
            "Grade",
            "DefectCountS",
            "Id",
            "CheckStatus",
            "Status_S",
            "Msg",
            "NextCode",
            "NextInfo",
            "childrenCoilDefect",
            "defects",
            "childrenTaperShapePoint",
            "childrenAlarmTaperShape",
            "childrenAlarmLooseCoil",
            "childrenAlarmFlatRoll",
            "childrenCoilCheck",
            "ActWidth",
            "CoilNo",
            "CreateTime",
            "CoilType",
            "CoilInside",
            "CoilDia",
            "Thickness",
            "Width",
            "Weight",
            "childrenCoil",
            "childrenAlarmInfo",
            "maxDefectName",
            "maxDefectLevel",
            "maxDefectSurface"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailResponse"]["properties"]["childrenCoilDefect"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilDetailDefect"},
            "type": "array",
            "title": "Childrencoildefect"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailResponse"]["properties"]["defects"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilDetailDefectAlias"},
            "type": "array",
            "title": "Defects"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailResponse"]["properties"]["childrenTaperShapePoint"],
        json!({
            "items": {"$ref": "#/components/schemas/TaperShapePointItem"},
            "type": "array",
            "title": "Childrentapershapepoint"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailResponse"]["properties"]["childrenAlarmInfo"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilDetailAlarmInfoItem"},
            "type": "array",
            "title": "Childrenalarminfo"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailDefect"]["properties"]["defectTime"],
        json!({
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "title": "Defecttime"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilDetailDefectAlias"]["properties"]["defectTime"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Defecttime"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["TaperShapePointItem"]["required"],
        json!([
            "Id",
            "secondaryCoilId",
            "surface",
            "x",
            "y",
            "value",
            "level",
            "err_msg",
            "crateTime",
            "data"
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_process_measurement_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/search/CoilState/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilStateItem"},
            "type": "array",
            "title": "Response Coil State List"
        })
    );
    assert_eq!(
        body["paths"]["/search/PlcData/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/PlcDataItem"},
                {"type": "null"}
            ],
            "title": "Response Get Plc Data Search Plcdata  Coil Id  Get"
        })
    );
    assert_eq!(
        body["paths"]["/get_point_data/{coil_id}/{surface_key}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/PointDataItem"},
            "type": "array",
            "title": "Response Point Data List"
        })
    );
    assert_eq!(
        body["paths"]["/get_line_data/{coil_id}/{surface_key}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/LineDataItem"},
            "type": "array",
            "title": "Response Line Data List"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilStateItem"]["properties"]["startTime"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Starttime"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilStateItem"]["required"],
        json!([
            "Id",
            "scan3dCoordinateScaleY",
            "start",
            "mask_area",
            "surface",
            "scan3dCoordinateScaleZ",
            "step",
            "width",
            "secondaryCoilId",
            "rotate",
            "upperLimit",
            "height",
            "x_rotate",
            "lowerLimit",
            "jsonData",
            "median_3d",
            "lowerArea",
            "median_3d_mm",
            "upperArea",
            "startTime",
            "colorFromValue_mm",
            "lowerArea_percent",
            "scan3dCoordinateScaleX",
            "colorToValue_mm",
            "upperArea_percent"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["PlcDataItem"]["properties"]["pclData"],
        json!({"type": "string", "title": "Pcldata"})
    );
    assert_eq!(
        body["components"]["schemas"]["PointDataItem"]["properties"]["crateTime"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Cratetime"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["LineDataItem"]["required"],
        json!([
            "width",
            "inner_min_value",
            "outer_max_value_mm",
            "height",
            "inner_min_value_mm",
            "crateTime",
            "secondaryCoilId",
            "rotation_angle",
            "inner_max_value",
            "surface",
            "x1",
            "inner_max_value_mm",
            "Id",
            "y1",
            "outer_min_value",
            "type",
            "x2",
            "outer_min_value_mm",
            "center_x",
            "y2",
            "outer_max_value",
            "center_y",
            "data"
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_defect_and_manual_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let expected_auto_defect_array = json!({
        "items": {"$ref": "#/components/schemas/DefectItem"},
        "type": "array",
        "title": "Response Defect List"
    });

    for path in [
        "/search/defects/{coil_id}/{direction}",
        "/search/getDefectAll/{start_coil_id}/{end_coil_id}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
            expected_auto_defect_array,
            "{path}"
        );
    }
    assert_eq!(
        body["paths"]["/search/defects_all/{coil_id}/{direction}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({
            "items": {
                "anyOf": [
                    {"$ref": "#/components/schemas/AutoDefectItem"},
                    {"$ref": "#/components/schemas/ManualDefectItem"}
                ]
            },
            "type": "array",
            "title": "Response Defect List Including Manual"
        })
    );
    assert_eq!(
        body["paths"]["/manual_defects/{coil_id}/{direction}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/ManualDefectItem"},
            "type": "array",
            "title": "Response Manual Defect List"
        })
    );
    for (method, path) in [
        ("post", "/manual_defect/add"),
        ("put", "/manual_defect/update/{defect_id}"),
    ] {
        assert_eq!(
            body["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"],
            json!({"$ref": "#/components/schemas/ManualDefectMutationResponse"}),
            "{method} {path}"
        );
    }
    assert_eq!(
        body["paths"]["/manual_defect/delete/{defect_id}"]["delete"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/DeleteManualDefectResponse"})
    );
    assert_eq!(
        body["paths"]["/export_defects"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/ExportDefectsResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["DefectItem"]["required"],
        json!([
            "Id",
            "secondaryCoilId",
            "surface",
            "defectClass",
            "defectName",
            "defectStatus",
            "defectTime",
            "defectX",
            "defectY",
            "defectW",
            "defectH",
            "defectSource",
            "defectData"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["DefectItem"]["properties"]["defectData"],
        json!({
            "anyOf": [
                {"type": "object", "additionalProperties": true},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Defectdata"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["AutoDefectItem"]["required"],
        json!([
            "Id",
            "secondaryCoilId",
            "surface",
            "defectClass",
            "defectName",
            "defectStatus",
            "defectTime",
            "defectX",
            "defectY",
            "defectW",
            "defectH",
            "defectSource",
            "defectData",
            "type"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["ManualDefectItem"]["properties"]["remark"],
        json!({
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "title": "Remark"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["ManualDefectMutationResponse"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/ManualDefectItem"},
                {"$ref": "#/components/schemas/ManualDefectErrorResponse"}
            ],
            "title": "ManualDefectMutationResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["DeleteManualDefectResponse"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/DeleteManualDefectSuccessResponse"},
                {"$ref": "#/components/schemas/ManualDefectErrorResponse"}
            ],
            "title": "DeleteManualDefectResponse"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["ExportDefectsResponse"]["required"],
        json!(["exported"])
    );
}

#[tokio::test]
async fn openapi_json_describes_grader_and_summary_sync_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/grader_list"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/GraderListItem"},
            "type": "array",
            "title": "Response Grader List"
        })
    );
    for path in ["/sync_summaries", "/sync_summaries_range"] {
        assert_eq!(
            body["paths"][path]["post"]["responses"]["200"]["content"]["application/json"]["schema"],
            json!({"$ref": "#/components/schemas/SyncSummariesResponse"}),
            "{path}"
        );
    }
    assert_eq!(
        body["components"]["schemas"]["GraderListItem"]["required"],
        json!([
            "ActWidth",
            "CoilNo",
            "CreateTime",
            "CoilType",
            "CoilInside",
            "Id",
            "CoilDia",
            "Thickness",
            "Width",
            "Weight",
            "Next"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["GraderListItem"]["properties"]["CreateTime"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Createtime"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["GraderListItem"]["properties"]["childrenCoil"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilSummaryChildCoil"},
            "type": "array",
            "title": "Childrencoil"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["SyncSummariesResponse"],
        json!({
            "properties": {
                "synced": {"type": "integer", "title": "Synced"},
                "message": {"type": "string", "title": "Message"},
                "error": {"type": "string", "title": "Error"}
            },
            "type": "object",
            "required": ["synced"],
            "additionalProperties": true,
            "title": "SyncSummariesResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_info_and_height_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/coilInfo/{coil_id}/{surface_key}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilInfoResponse"},
                {"type": "null"}
            ],
            "title": "Response Get Info Coilinfo  Coil Id   Surface Key  Get"
        })
    );
    assert_eq!(
        body["paths"]["/coilData/heightData/{surface_key}/{coil_id}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({
            "items": {"$ref": "#/components/schemas/HeightDataSegment"},
            "type": "array",
            "title": "Response Height Data Segments"
        })
    );
    assert_eq!(
        body["paths"]["/coilData/heightPoint/{surface_key}/{coil_id}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/HeightPointResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilInfoResponse"]["additionalProperties"],
        json!(true)
    );
    assert_eq!(
        body["components"]["schemas"]["CoilInfoResponse"]["properties"]["circleConfig"],
        json!({
            "type": "object",
            "additionalProperties": true,
            "title": "Circleconfig"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["HeightDataSegment"]["required"],
        json!(["pointL", "pointR", "points"])
    );
    assert_eq!(
        body["components"]["schemas"]["HeightDataSegment"]["properties"]["pointL"],
        json!({"$ref": "#/components/schemas/HeightDataPoint2D"})
    );
    assert_eq!(
        body["components"]["schemas"]["HeightDataSegment"]["properties"]["points"],
        json!({
            "items": {"$ref": "#/components/schemas/HeightDataPoint3D"},
            "type": "array",
            "title": "Points"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["HeightDataPoint3D"]["prefixItems"],
        json!([
            {"type": "integer", "title": "X"},
            {"type": "integer", "title": "Y"},
            {"type": "number", "title": "Z"}
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["HeightPointResponse"],
        json!({
            "anyOf": [
                {"type": "integer"},
                {"type": "number"},
                {"type": "string"}
            ],
            "title": "HeightPointResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_xlsx_export_responses_as_binary_files_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let expected_content = json!({
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
            "schema": {"type": "string", "format": "binary"}
        }
    });

    for (method, path) in [
        ("get", "/exportXlsxById/{start}/{end}"),
        ("get", "/exportXlsxByDateTime/{start}/{end}"),
        ("post", "/export_xlsx"),
        ("get", "/exportDataSimple"),
        ("get", "/export_1h"),
        ("post", "/export_1h"),
        ("get", "/export_24h"),
        ("post", "/export_24h"),
        ("get", "/export_today"),
        ("post", "/export_today"),
    ] {
        assert_eq!(
            body["paths"][path][method]["responses"]["200"]["content"], expected_content,
            "{method} {path}"
        );
    }
}

#[tokio::test]
async fn openapi_json_describes_diagnostic_and_image_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let binary_content = |content_type: &str| {
        json!({
            content_type: {
                "schema": {"type": "string", "format": "binary"}
            }
        })
    };
    let image_content = |content_types: &[&str]| {
        let mut content = serde_json::Map::new();
        for content_type in content_types {
            content.insert(
                (*content_type).to_string(),
                json!({"schema": {"type": "string", "format": "binary"}}),
            );
        }
        Value::Object(content)
    };

    assert_eq!(
        body["paths"]["/download_test"]["get"]["responses"]["200"]["content"],
        json!({
            "application/octet-stream": {
                "schema": {"type": "string", "format": "binary"}
            },
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorMessageResponse"}
            }
        })
    );
    assert_eq!(
        body["paths"]["/speedtest/download"]["get"]["responses"]["200"]["content"],
        binary_content("application/octet-stream")
    );
    assert_eq!(
        body["paths"]["/speedtest/upload"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/SpeedTestUploadResponse"})
    );
    assert_eq!(
        body["paths"]["/cameraData/{coil_id}/{camera_key}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/CameraDataResponse"})
    );

    for path in [
        "/coilData/Render/{surfaceKey}/{coil_id}",
        "/image/preview/{surface_key}/{coil_id}/{type_}",
        "/image/source/{surface_key}/{coil_id}/{type_}",
        "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
        "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["responses"]["200"]["content"],
            image_content(&["image/jpeg", "image/png"]),
            "{path}"
        );
    }
    for path in [
        "/coilData/Area/{surface_key}/{coil_id}",
        "/coilData/Error/{surface_key}/{coil_id}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["responses"]["200"]["content"],
            binary_content("image/png"),
            "{path}"
        );
    }
    for path in [
        "/image/area/{surface_key}/{coil_id}",
        "/image/area/{surface_key}/{coil_id}/{type_}",
    ] {
        assert_eq!(
            body["paths"][path]["get"]["responses"]["200"]["content"],
            json!({
                "image/jpeg": {
                    "schema": {"type": "string", "format": "binary"}
                },
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AreaImageMetadataResponse"}
                }
            }),
            "{path}"
        );
    }

    assert_eq!(
        body["components"]["schemas"]["SpeedTestUploadResponse"]["required"],
        json!([
            "filename",
            "file_size_mb",
            "upload_time_s",
            "upload_speed_mb_s"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CameraDataResponse"]["required"],
        json!(["cameraKey", "coilId", "surface", "source", "folder"])
    );
    assert_eq!(
        body["components"]["schemas"]["CameraDataResponse"]["additionalProperties"],
        true
    );
    assert_eq!(
        body["components"]["schemas"]["AreaImageMetadataResponse"],
        json!({
            "properties": {
                "width": {"type": "integer", "title": "Width"},
                "height": {"type": "integer", "title": "Height"}
            },
            "type": "object",
            "required": ["width", "height"],
            "title": "AreaImageMetadataResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_plc_curve_response_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/plc_curve/{field}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/PlcCurveResponse"})
    );
    assert_eq!(
        body["paths"]["/plc_curve_all"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/PlcCurveAllResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveResponse"]["required"],
        json!(["field", "items"])
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveResponse"]["properties"]["items"],
        json!({
            "items": {"$ref": "#/components/schemas/PlcCurveItem"},
            "type": "array",
            "title": "Items"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveItem"]["required"],
        json!(["coil_id", "time", "value"])
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveItem"]["properties"]["value"],
        json!({
            "anyOf": [{"type": "number"}, {"type": "null"}],
            "title": "Value"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveAllResponse"]["required"],
        json!(["items"])
    );
    assert_eq!(
        body["components"]["schemas"]["PlcCurveAllItem"]["required"],
        json!([
            "coil_id",
            "time",
            "location_S",
            "location_L",
            "location_laser",
            "median_3d_mm_S",
            "median_3d_mm_L",
            "median_3d_mm_avg",
            "width_"
        ])
    );
}

#[tokio::test]
async fn openapi_json_describes_coil_alarm_response_contracts_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/coilAlarm/{coil_id}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/CoilAlarmResponse"})
    );
    assert_eq!(
        body["paths"]["/coilAlarm/get_info"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"type": "null"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmResponse"]["required"],
        json!(["FlatRoll", "TaperShape", "LooseCoil"])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmResponse"]["properties"]["FlatRoll"],
        json!({"$ref": "#/components/schemas/CoilAlarmFlatRollMap"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmResponse"]["properties"]["TaperShape"],
        json!({"$ref": "#/components/schemas/CoilAlarmTaperShapeMap"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmResponse"]["properties"]["LooseCoil"],
        json!({"$ref": "#/components/schemas/CoilAlarmLooseCoilMap"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmFlatRollMap"]["additionalProperties"],
        json!({"$ref": "#/components/schemas/CoilAlarmFlatRollItem"})
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmTaperShapeMap"]["additionalProperties"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilAlarmTaperShapeItem"},
            "type": "array"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmLooseCoilMap"]["additionalProperties"],
        json!({
            "items": {"$ref": "#/components/schemas/CoilAlarmLooseCoilItem"},
            "type": "array"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmFlatRollItem"]["required"],
        json!([
            "secondaryCoilId",
            "out_circle_height",
            "inner_circle_center_x",
            "data",
            "surface",
            "inner_circle_center_y",
            "out_circle_center_x",
            "inner_circle_radius",
            "accuracy_x",
            "out_circle_center_y",
            "accuracy_y",
            "out_circle_radius",
            "level",
            "Id",
            "inner_circle_width",
            "err_msg",
            "out_circle_width",
            "inner_circle_height",
            "crateTime"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmTaperShapeItem"]["required"],
        json!([
            "in_taper_max_x",
            "err_msg",
            "surface",
            "in_taper_max_y",
            "crateTime",
            "out_taper_max_x",
            "in_taper_max_value",
            "data",
            "out_taper_max_y",
            "in_taper_min_x",
            "Id",
            "out_taper_max_value",
            "in_taper_min_y",
            "out_taper_min_x",
            "in_taper_min_value",
            "out_taper_min_y",
            "rotation_angle",
            "secondaryCoilId",
            "out_taper_min_value",
            "level"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmLooseCoilItem"]["required"],
        json!([
            "surface",
            "Id",
            "secondaryCoilId",
            "rotation_angle",
            "err_msg",
            "data",
            "max_width",
            "level",
            "crateTime"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmLooseCoilItem"]["properties"]["data"],
        json!({
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "title": "Data"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["CoilAlarmFlatRollItem"]["properties"]["crateTime"],
        json!({
            "anyOf": [
                {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                {"type": "string"},
                {"type": "null"}
            ],
            "title": "Cratetime"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_area_system_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/clip_config"]["post"]["requestBody"],
        json!({
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ClipConfigPayload"}
                }
            },
            "required": true
        })
    );
    assert_eq!(
        body["paths"]["/area/rejoin"]["post"]["requestBody"],
        json!({
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AreaRejoinPayload"}
                }
            },
            "required": true
        })
    );
    assert_eq!(
        body["paths"]["/area/status"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/AreaStatusResponse"})
    );
    assert_eq!(
        body["paths"]["/area/scan"]["post"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/AreaStatusResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["ClipConfigPayload"]["required"],
        json!(["surface_key"])
    );
    assert_eq!(
        body["components"]["schemas"]["ClipConfigPayload"]["properties"]["mode"],
        json!({
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "title": "Mode"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["AreaRejoinPayload"]["properties"]["coil_id"],
        json!({"type": "integer", "title": "Coil Id"})
    );
    assert_eq!(
        body["components"]["schemas"]["AreaStatusResponse"]["required"],
        json!(["status", "surfaces", "queueDepths", "scanner"])
    );
    assert_eq!(
        body["components"]["schemas"]["AreaStatusResponse"]["properties"]["scanner"],
        json!({"$ref": "#/components/schemas/AreaScannerStatus"})
    );
    assert_eq!(
        body["components"]["schemas"]["AreaSurfaceStatus"]["required"],
        json!(["queueSize", "lastCoilId"])
    );
    assert_eq!(
        body["components"]["schemas"]["AreaSurfaceStatus"]["properties"]["clipConfig"],
        json!({"$ref": "#/components/schemas/AreaClipConfig"})
    );
    assert_eq!(
        body["components"]["schemas"]["AreaScannerStatus"]["required"],
        json!([
            "enabled",
            "scanInterval",
            "scanLimit",
            "maxQueueDepth",
            "minImagesPerCamera",
            "maxCameraCountSkew",
            "scanRunning",
            "lastScanStartTime",
            "lastScanTime",
            "lastScanError",
            "lastCandidates",
            "queued",
            "skippedProcessed",
            "skippedIncomplete",
            "skippedQueueFull",
            "queueFailures"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["AreaScannerStatus"]["properties"]["queued"],
        json!({
            "items": {"$ref": "#/components/schemas/AreaScanQueuedItem"},
            "type": "array",
            "title": "Queued"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["AreaScanQueuedItem"]["required"],
        json!(["coil_id", "reason"])
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_software_update_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/software_update/manifest"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/SoftwareUpdateManifest"})
    );
    assert_eq!(
        body["paths"]["/updates/{file_name}"]["get"]["responses"]["200"]["content"]["application/octet-stream"]
            ["schema"],
        json!({"type": "string", "format": "binary"})
    );
    assert!(
        body["paths"]["/updates/{file_name}"]["get"]["responses"]["200"]["content"]
            .as_object()
            .expect("updates response content")
            .get("application/json")
            .is_none()
    );
    assert_eq!(
        body["components"]["schemas"]["SoftwareUpdateManifest"]["required"],
        json!([
            "version",
            "latest_version",
            "download_url",
            "package_url",
            "file_name"
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["SoftwareUpdateManifest"]["properties"]["release_notes"],
        json!({
            "items": {"type": "string"},
            "type": "array",
            "title": "Release Notes"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_re_detection_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/reDetection/status"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/ReDetectionStatusResponse"})
    );
    assert_eq!(
        body["paths"]["/reDetection/start/{from_id}/{to_id}"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/ReDetectionStatusResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["ReDetectionStatusResponse"]["required"],
        json!([
            "total", "done", "pending", "running", "error", "queue", "messages", "progress"
        ])
    );
    assert_eq!(
        sorted_object_keys(
            &body["components"]["schemas"]["ReDetectionStatusResponse"]["properties"]
        ),
        vec![
            "done".to_string(),
            "error".to_string(),
            "messages".to_string(),
            "pending".to_string(),
            "progress".to_string(),
            "queue".to_string(),
            "running".to_string(),
            "total".to_string(),
        ]
    );
    assert_eq!(
        body["components"]["schemas"]["ReDetectionStatusResponse"]["properties"]["running"],
        json!({"type":"boolean","title":"Running"})
    );
    assert_eq!(
        body["components"]["schemas"]["ReDetectionStatusResponse"]["properties"]["queue"],
        json!({"items":{"type":"integer"},"type":"array","title":"Queue"})
    );
    assert_eq!(
        body["components"]["schemas"]["ReDetectionStatusResponse"]["properties"]["messages"],
        json!({"items":{"type":"object"},"type":"array","title":"Messages"})
    );
    assert_eq!(
        body["components"]["schemas"]["ReDetectionStatusResponse"]["properties"]["progress"],
        json!({"type":"number","title":"Progress"})
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_server_state_contract_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/getServerState"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/ServerStateResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["ServerStateResponse"]["type"],
        json!("array")
    );
    assert_eq!(
        body["components"]["schemas"]["ServerStateResponse"]["items"],
        json!({"$ref": "#/components/schemas/ServerStateEntry"})
    );
    assert_eq!(
        body["components"]["schemas"]["ServerStateEntry"]["anyOf"],
        json!([
            {"$ref": "#/components/schemas/ServerStateTuple"},
            {"$ref": "#/components/schemas/ServerStateMessage"},
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"}
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["ServerStateTuple"]["prefixItems"],
        json!([
            {"type": "string", "title": "Type"},
            {"title": "Message"}
        ])
    );
    assert_eq!(
        body["components"]["schemas"]["ServerStateMessage"]["properties"]["level"],
        json!({
            "anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "string"}],
            "title": "Level"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_alg_test_http_contracts_for_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/alg_2d/models"]["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        json!({"$ref": "#/components/schemas/AlgModelListResponse"})
    );
    assert_eq!(
        body["paths"]["/alg_2d/test/start"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/AlgTestStartResponse"})
    );
    assert_eq!(
        body["paths"]["/alg_2d/test/stop"]["post"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/AlgTestStopResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["AlgTestStartResponse"]["required"],
        json!(["ok", "task_id"])
    );
    assert_eq!(
        body["components"]["schemas"]["AlgTestStartResponse"]["properties"]["ok"],
        json!({"type":"boolean","title":"Ok"})
    );
    assert_eq!(
        body["components"]["schemas"]["AlgTestStartResponse"]["properties"]["task_id"],
        json!({"type":"string","title":"Task Id"})
    );
    assert_eq!(
        body["components"]["schemas"]["AlgTestStopResponse"]["required"],
        json!(["ok", "message"])
    );
    assert_eq!(
        body["components"]["schemas"]["AlgTestStopResponse"]["properties"]["message"],
        json!({"type":"string","title":"Message"})
    );
    assert_eq!(
        body["components"]["schemas"]["AlgModelListResponse"]["required"],
        json!(["models"])
    );
    assert_eq!(
        body["components"]["schemas"]["AlgModelListResponse"]["properties"]["models"],
        json!({
            "items": {"$ref": "#/components/schemas/AlgModelInfo"},
            "type": "array",
            "title": "Models"
        })
    );
    assert_eq!(
        body["components"]["schemas"]["AlgModelInfo"]["required"],
        json!(["name", "type", "display_name"])
    );
    assert_eq!(
        body["components"]["schemas"]["AlgModelInfo"]["properties"]["type"],
        json!({"type":"string","title":"Type"})
    );
}

#[tokio::test]
async fn openapi_json_describes_rust_clip_max_contract_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/clipMaxImage/{coil_id}/{key}"]["get"]["parameters"],
        json!([
            {"name":"coil_id","in":"path","required":true,"schema":{"type":"integer","title":"Coil Id"}},
            {"name":"key","in":"path","required":true,"schema":{"type":"string","title":"Key"}},
            {"name":"save_url","in":"query","required":false,"schema":{"title":"Save Url"}}
        ])
    );
    assert_eq!(
        body["paths"]["/clipMaxImage/{coil_id}/{key}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"type": "null"})
    );
}

#[tokio::test]
async fn openapi_json_describes_backup_image_task_null_response_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/backupImageTask/{from_id}/{to_id}/{save_folder}"]["get"]["parameters"],
        json!([
            {"name":"from_id","in":"path","required":true,"schema":{"type":"integer","title":"From Id"}},
            {"name":"to_id","in":"path","required":true,"schema":{"type":"integer","title":"To Id"}},
            {"name":"save_folder","in":"path","required":true,"schema":{"type":"string","title":"Save Folder"}}
        ])
    );
    assert_eq!(
        body["paths"]["/backupImageTask/{from_id}/{to_id}/{save_folder}"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"],
        json!({"type": "null"})
    );
}

#[tokio::test]
async fn openapi_json_describes_save_to_sql_response_for_qml_tauri_ui() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;

    assert_eq!(
        body["paths"]["/save_to_sql/{sql_file}"]["get"]["parameters"],
        json!([
            {"name":"sql_file","in":"path","required":true,"schema":{"type":"string","title":"Sql File"}}
        ])
    );
    assert_eq!(
        body["paths"]["/save_to_sql/{sql_file}"]["get"]["responses"]["200"]["content"]["application/json"]
            ["schema"],
        json!({"$ref": "#/components/schemas/SaveToSqlResponse"})
    );
    assert_eq!(
        body["components"]["schemas"]["SaveToSqlResponse"],
        json!({
            "properties": {
                "state": {"type": "boolean", "title": "State"}
            },
            "type": "object",
            "required": ["state"],
            "title": "SaveToSqlResponse"
        })
    );
}

#[tokio::test]
async fn openapi_json_describes_validation_responses_like_fastapi() {
    let (_, body) = request_json(app_with_seed_data(), "GET", "/openapi.json").await;
    let validation_response = json!({
        "description": "Validation Error",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
            }
        }
    });

    for (method, path) in [
        ("get", "/coilList/{number}"),
        ("get", "/coilData/Render/{surfaceKey}/{coil_id}"),
        ("post", "/control/set_config"),
        ("post", "/speedtest/upload"),
        ("delete", "/manual_defect/delete/{defect_id}"),
        ("post", "/sync_summaries_range"),
    ] {
        assert_eq!(
            body["paths"][path][method]["responses"]["422"],
            validation_response
        );
    }

    assert!(
        body["paths"]["/version"]["get"]["responses"]
            .as_object()
            .expect("version responses")
            .get("422")
            .is_none()
    );
}

#[tokio::test]
async fn settings_test_mode_get_and_post_read_write_python_config_shape() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("settings temp root");
    let config_path = root.join("test_mode_config.json");
    let _env_guard = set_env_var_guard("RUST_API_TEST_MODE_CONFIG", &config_path);
    let _developer_mode_guard = set_env_var_guard("API_DEVELOPER_MODE", "false");
    let _config_dir_guard = set_env_var_guard("CONFIG_3D_DIR", root.join("config").to_string_lossy().as_ref());
    let _computername_guard = set_env_var_guard("COMPUTERNAME", "production-host");
    let _hostname_guard = set_env_var_guard("HOSTNAME", "production-host");

    let initial_response =
        request_response(app_with_seed_data(), "GET", "/settings/test_mode").await;
    let initial_status = initial_response.status();
    assert_eq!(initial_status, StatusCode::OK);
    let initial_body: Value =
        serde_json::from_slice(&response_bytes(initial_response).await).expect("initial body");
    assert_eq!(initial_body, json!({"test_mode": false}));

    let post_response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/settings/test_mode",
        json!({"enabled": true}),
    )
    .await;
    let post_status = post_response.status();
    let post_body: Value =
        serde_json::from_slice(&response_bytes(post_response).await).expect("post body");
    assert_eq!(post_status, StatusCode::OK);
    assert_eq!(post_body, json!({"status": "success", "test_mode": true}));

    let persisted: Value =
        serde_json::from_slice(&fs::read(&config_path).expect("persisted config")).expect("json");
    assert_eq!(persisted["test_mode"], true);

    let read_response = request_response(app_with_seed_data(), "GET", "/settings/test_mode").await;
    let read_status = read_response.status();
    assert_eq!(read_status, StatusCode::OK);
    let read_body: Value =
        serde_json::from_slice(&response_bytes(read_response).await).expect("read body");
    assert_eq!(read_body, json!({"test_mode": true}));

    let response =
        request_response(app_with_seed_data(), "GET", "/settings/test_mode_status").await;
    assert_eq!(response.status(), StatusCode::OK);
    let status_bytes = response_bytes(response).await;
    let status_text = String::from_utf8(status_bytes.to_vec()).expect("status body text");
    let expected_config_path =
        serde_json::to_string(config_path.to_string_lossy().as_ref()).expect("config path json");
    assert_eq!(
        status_text,
        format!(
            r#"{{"config_file_exists":true,"config_file_value":true,"developer_mode":true,"is_local":true,"config_file_path":{expected_config_path}}}"#
        )
    );
    let status_body: Value = serde_json::from_slice(&status_bytes).expect("status body");
    assert_eq!(status_body["config_file_exists"], true);
    assert_eq!(status_body["config_file_value"], true);
    assert_eq!(status_body["developer_mode"], true);
    assert_eq!(status_body["is_local"], true);
    assert_eq!(
        status_body["config_file_path"].as_str(),
        Some(config_path.to_string_lossy().as_ref())
    );
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn coil_list_returns_python_compatible_summary_shape() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/coilList/20").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().expect("array").len(), 1);
    assert_eq!(body[0]["Id"], 42);
    assert_eq!(body[0]["CoilNo"], "LG-20260627-0042");
    assert_eq!(body[0]["CreateTime"], "2026-06-27 12:34:56");
    assert_eq!(body[0]["DetectionTime"], "2026-06-27 12:35:10");
    assert_eq!(body[0]["DefectCountS"], 3);
    assert_eq!(body[0]["DefectCountL"], 1);
    assert_eq!(body[0]["Status_S"], 2);
    assert_eq!(body[0]["Status_L"], 1);
    assert_eq!(body[0]["Grade"], 2);
    assert_eq!(body[0]["AlarmInfo"]["S"]["grad"], 2);
    assert_eq!(body[0]["AlarmInfo"]["L"]["grad"], 1);
    assert_eq!(body[0]["childrenCoilDefect"][0]["defectName"], "压痕");
}

#[tokio::test]
async fn coil_list_invalid_number_returns_fastapi_path_validation_error() {
    let response = request_response(app_with_seed_data(), "GET", "/coilList/abc").await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["path", "number"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn coil_list_negative_number_returns_python_internal_error() {
    let response = request_response(app_with_seed_data(), "GET", "/coilList/-1").await;

    assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    assert_eq!(
        String::from_utf8(response_bytes(response).await.to_vec()).expect("response text"),
        "Internal Server Error"
    );
}

#[tokio::test]
async fn flush_endpoint_returns_python_compatible_incremental_coil_list_shape() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/flush/41").await;

    assert_eq!(status, StatusCode::OK);
    let coil_list = body["coilList"].as_array().expect("coilList array");
    assert_eq!(coil_list.len(), 1);
    assert_eq!(coil_list[0]["Id"], 42);
    assert_eq!(coil_list[0]["CoilNo"], "LG-20260627-0042");
    assert_eq!(coil_list[0]["childrenCoilDefect"][0]["defectName"], "压痕");

    let (zero_status, zero_body) = request_json(app_with_seed_data(), "GET", "/flush/0").await;
    assert_eq!(zero_status, StatusCode::OK);
    assert_eq!(zero_body, json!({}));
}

#[tokio::test]
async fn flush_endpoint_rejects_non_python_int_converter_paths_like_python() {
    for uri in ["/flush/abc", "/flush/-1"] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"})
        );
    }
}

#[tokio::test]
async fn search_coil_id_invalid_path_returns_fastapi_path_validation_error() {
    let response = request_response(app_with_seed_data(), "GET", "/search/coilId/abc").await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["path", "coil_id"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn search_datetime_invalid_format_returns_python_internal_error() {
    for uri in [
        "/search/DateTime/2026-01-01/2026-01-02",
        "/search/DateTime/bad/start",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(
            String::from_utf8(response_bytes(response).await.to_vec()).expect("response text"),
            "Internal Server Error"
        );
    }
}

#[tokio::test]
async fn search_datetime_valid_format_returns_python_summary_rows() {
    let (status, body) = request_json(
        app_with_seed_data(),
        "GET",
        "/search/DateTime/202606270000/202606282359",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().expect("array").len(), 1);
    assert_eq!(body[0]["Id"], 42);
    assert_eq!(body[0]["CoilNo"], "LG-20260627-0042");
}

#[tokio::test]
async fn search_datetime_filters_by_create_time_not_detection_time() {
    let repository = InMemoryCoilRepository::new().with_coils(vec![
        CoilSummaryRow {
            id: 42,
            coil_no: "DETECTION-IN-RANGE-ONLY".to_string(),
            create_time: Some("2026-06-01 00:00:00".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 2,
            s_taper_shape_grad: 2,
            s_loose_coil_grad: 2,
            s_flat_roll_grad: 2,
            s_grad: 2,
            s_has_alarm: true,
            s_next_code: Some("A".to_string()),
            s_next_name: Some("下一工序".to_string()),
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 3,
            defect_count_l: 0,
            detection_time: Some("2026-06-27 12:35:10".to_string()),
            check_status: 2,
            status_l: 0,
            status_s: 2,
            grade: 2,
            max_defect_name: Some("压痕".to_string()),
            max_defect_level: 2,
            max_defect_surface: Some("S".to_string()),
            has_coil: true,
            has_alarm_info: true,
        },
        CoilSummaryRow {
            id: 43,
            coil_no: "CREATE-IN-RANGE".to_string(),
            create_time: Some("2026-06-27 12:35:10".to_string()),
            coil_type: Some("Q235".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1320.0),
            thickness: Some(2.4),
            width: Some(1250.0),
            weight: Some(65.0),
            act_width: Some(1248.5),
            next_code: Some("A".to_string()),
            next_info: Some("下一工序".to_string()),
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-28 12:35:10".to_string()),
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        },
    ]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let (status, body) =
        request_json(app, "GET", "/search/DateTime/202606271235/202606271236").await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("array");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["Id"], 43);
    assert_eq!(rows[0]["CoilNo"], "CREATE-IN-RANGE");
}

#[tokio::test]
async fn detail_endpoint_returns_python_compatible_full_shape_and_real_defects() {
    let (status, body) = request_json(
        app_with_detail_defect_serialization_data(),
        "GET",
        "/detail/42",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        body.as_object()
            .expect("detail root object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "hasCoil",
            "hasAlarmInfo",
            "AlarmInfo",
            "SecondaryCoilId",
            "DetectionTime",
            "DefectCountL",
            "Status_L",
            "Grade",
            "DefectCountS",
            "Id",
            "CheckStatus",
            "Status_S",
            "Msg",
            "NextCode",
            "NextInfo",
            "childrenCoilDefect",
            "defects",
            "childrenTaperShapePoint",
            "childrenAlarmTaperShape",
            "childrenAlarmLooseCoil",
            "childrenAlarmFlatRoll",
            "childrenCoilCheck",
            "ActWidth",
            "CoilNo",
            "CreateTime",
            "CoilType",
            "CoilInside",
            "CoilDia",
            "Thickness",
            "Width",
            "Weight",
            "childrenCoil",
            "childrenAlarmInfo",
            "maxDefectName",
            "maxDefectLevel",
            "maxDefectSurface",
        ]
    );
    assert_eq!(body["Id"], 42);
    assert_eq!(body["SecondaryCoilId"], 42);
    assert_eq!(body["CoilNo"], "LG-20260627-0042");
    assert_eq!(body["Thickness"], 3.9);
    assert_eq!(body["hasCoil"], true);
    assert_eq!(body["hasAlarmInfo"], true);
    assert_eq!(body["AlarmInfo"]["S"]["grad"], 2);
    assert_eq!(body["childrenCoil"][0]["Id"], 42);
    assert_eq!(body["childrenCoil"][0]["SecondaryCoilId"], 42);
    assert_eq!(
        body["childrenCoil"][0]["DetectionTime"],
        "2026-06-27T12:35:10"
    );
    assert_eq!(body["childrenCoil"][0]["DefectCountS"], 3);
    assert_eq!(body["childrenCoil"][0]["DefectCountL"], 1);
    assert_eq!(
        body["childrenCoil"][0]
            .as_object()
            .expect("childrenCoil object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "SecondaryCoilId",
            "DetectionTime",
            "DefectCountL",
            "Status_L",
            "Grade",
            "DefectCountS",
            "Id",
            "CheckStatus",
            "Status_S",
            "Msg",
        ]
    );
    assert_eq!(body["childrenAlarmInfo"], json!([]));
    assert!(body.get("DateTime").is_none());
    assert_eq!(
        body["childrenCoilDefect"]
            .as_array()
            .expect("defects")
            .len(),
        1
    );
    assert_eq!(body["childrenCoilDefect"][0]["Id"], 7);
    assert_eq!(body["childrenCoilDefect"][0]["defectName"], "压痕");
    assert_eq!(body["childrenCoilDefect"][0]["defectSource"], 0.913837);
    assert_eq!(
        body["childrenCoilDefect"][0]["defectTime"],
        "2026-06-27T12:35:12"
    );
    assert_eq!(body["childrenCoilDefect"][0]["defectData"], "");
    assert_eq!(
        body["childrenCoilDefect"][0]
            .as_object()
            .expect("detail defect object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "surface",
            "secondaryCoilId",
            "Id",
            "defectClass",
            "defectStatus",
            "defectX",
            "defectW",
            "defectSource",
            "defectName",
            "defectTime",
            "defectY",
            "defectH",
            "defectData",
        ]
    );
    assert_eq!(body["defects"][0]["Id"], 7);
    assert_eq!(body["defects"][0]["defectName"], "压痕");
    assert_eq!(body["defects"][0]["defectSource"], 0.913837);
    assert_eq!(body["defects"][0]["defectTime"]["year"], 2026);
    assert_eq!(body["defects"][0]["defectTime"]["month"], 6);
    assert_eq!(body["defects"][0]["defectTime"]["day"], 27);
    assert_eq!(body["defects"][0]["defectTime"]["hour"], 12);
    assert_eq!(body["defects"][0]["defectTime"]["minute"], 35);
    assert_eq!(body["defects"][0]["defectTime"]["second"], 12);
    assert_ne!(body["defects"], body["childrenCoilDefect"]);
    assert_eq!(
        body["defects"][0]
            .as_object()
            .expect("detail defects alias object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "surface",
            "secondaryCoilId",
            "Id",
            "defectClass",
            "defectStatus",
            "defectX",
            "defectW",
            "defectSource",
            "defectName",
            "defectTime",
            "defectY",
            "defectH",
            "defectData",
        ]
    );
    assert_eq!(body["childrenTaperShapePoint"], json!([]));
    assert_eq!(body["childrenAlarmTaperShape"], json!([]));
    assert_eq!(body["childrenAlarmLooseCoil"], json!([]));
    assert_eq!(body["childrenAlarmFlatRoll"], json!([]));
    assert_eq!(body["childrenCoilCheck"][0]["Id"], 61);
    assert_eq!(body["childrenCoilCheck"][0]["secondaryCoilId"], 42);
    assert_eq!(body["childrenCoilCheck"][0]["status"], 1);
    assert_eq!(body["childrenCoilCheck"][0]["msg"], "初检通过");
}

#[tokio::test]
async fn detail_endpoint_uses_alarm_info_children_like_python() {
    let repository = InMemoryCoilRepository::new()
        .with_coils(vec![CoilSummaryRow {
            id: 120,
            coil_no: "LG-20260629-0120".to_string(),
            create_time: Some("2026-06-29 12:00:00".to_string()),
            coil_type: Some("Q345".to_string()),
            coil_inside: Some(610.0),
            coil_dia: Some(1400.0),
            thickness: Some(3.2),
            width: Some(1500.0),
            weight: Some(72.0),
            act_width: Some(1498.0),
            next_code: None,
            next_info: None,
            s_defect_grad: 1,
            s_taper_shape_grad: 1,
            s_loose_coil_grad: 1,
            s_flat_roll_grad: 1,
            s_grad: 1,
            s_has_alarm: false,
            s_next_code: None,
            s_next_name: None,
            l_defect_grad: 1,
            l_taper_shape_grad: 1,
            l_loose_coil_grad: 1,
            l_flat_roll_grad: 1,
            l_grad: 1,
            l_has_alarm: false,
            l_next_code: None,
            l_next_name: None,
            defect_count_s: 0,
            defect_count_l: 0,
            detection_time: Some("2026-06-29 12:05:00".to_string()),
            check_status: 0,
            status_l: 0,
            status_s: 0,
            grade: 0,
            max_defect_name: None,
            max_defect_level: 0,
            max_defect_surface: None,
            has_coil: true,
            has_alarm_info: false,
        }])
        .with_alarm_infos(vec![
            AlarmInfoSummaryRow {
                id: 301,
                secondary_coil_id: 120,
                surface: "S".to_string(),
                next_code: Some("A".to_string()),
                next_name: Some("酸洗".to_string()),
                taper_shape_msg: Some("S塔形报警".to_string()),
                loose_coil_msg: Some("".to_string()),
                flat_roll_msg: Some("正常".to_string()),
                defect_msg: Some("S缺陷报警".to_string()),
                defect_grad: 2,
                taper_shape_grad: 4,
                loose_coil_grad: 1,
                flat_roll_grad: 1,
                grad: 4,
                create_time: Some("2026-06-29 12:06:00".to_string()),
                data: None,
            },
            AlarmInfoSummaryRow {
                id: 302,
                secondary_coil_id: 120,
                surface: "L".to_string(),
                next_code: Some("B".to_string()),
                next_name: Some("冷轧".to_string()),
                taper_shape_msg: Some("".to_string()),
                loose_coil_msg: Some("L松卷报警".to_string()),
                flat_roll_msg: Some("".to_string()),
                defect_msg: Some("".to_string()),
                defect_grad: 1,
                taper_shape_grad: 1,
                loose_coil_grad: 5,
                flat_roll_grad: 1,
                grad: 5,
                create_time: Some("2026-06-29 12:07:00".to_string()),
                data: Some("{\"source\":\"alarm\"}".to_string()),
            },
        ]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let (status, body) = request_json(app, "GET", "/detail/120").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["hasAlarmInfo"], true);
    assert_eq!(body["NextCode"], "B");
    assert_eq!(body["NextInfo"], "冷轧");
    assert_eq!(body["AlarmInfo"]["S"]["Id"], 301);
    assert_eq!(body["AlarmInfo"]["S"]["secondaryCoilId"], 120);
    assert_eq!(body["AlarmInfo"]["S"]["surface"], "S");
    assert_eq!(body["AlarmInfo"]["S"]["nextCode"], "A");
    assert_eq!(body["AlarmInfo"]["S"]["nextName"], "酸洗");
    assert_eq!(body["AlarmInfo"]["S"]["taperShapeMsg"], "S塔形报警");
    assert_eq!(body["AlarmInfo"]["S"]["defectMsg"], "S缺陷报警");
    assert_eq!(body["AlarmInfo"]["S"]["taperShapeGrad"], 4);
    assert_eq!(body["AlarmInfo"]["S"]["grad"], 4);
    assert_eq!(body["AlarmInfo"]["S"]["crateTime"]["year"], 2026);
    assert_eq!(body["AlarmInfo"]["L"]["Id"], 302);
    assert_eq!(body["AlarmInfo"]["L"]["looseCoilMsg"], "L松卷报警");
    assert_eq!(body["AlarmInfo"]["L"]["data"], "{\"source\":\"alarm\"}");
    assert_eq!(
        body["childrenAlarmInfo"]
            .as_array()
            .expect("childrenAlarmInfo")
            .len(),
        2
    );
    assert_eq!(body["childrenAlarmInfo"][0]["Id"], 301);
    assert_eq!(body["childrenAlarmInfo"][0]["surface"], "S");
    assert_eq!(
        body["childrenAlarmInfo"][0]["crateTime"],
        "2026-06-29T12:06:00"
    );
    assert_eq!(body["childrenAlarmInfo"][1]["Id"], 302);
    assert_eq!(body["childrenAlarmInfo"][1]["nextCode"], "B");
}

#[tokio::test]
async fn detail_endpoint_reads_secondary_data_even_when_summary_search_filters_it_out() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("detail defect config dir");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        json!({
            "data": {
                "数据脏污": {"level": 3, "show": true},
                "隐藏背景": {"level": 5, "show": false}
            },
            "default": {"level": 1, "show": true}
        })
        .to_string(),
    )
    .expect("detail defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let (search_status, search_body) =
        request_json(app_with_secondary_only_data(), "GET", "/search/coilId/77").await;

    assert_eq!(search_status, StatusCode::OK);
    assert_eq!(search_body, json!([]));

    let (detail_status, detail_body) =
        request_json(app_with_secondary_only_data(), "GET", "/detail/77").await;

    assert_eq!(detail_status, StatusCode::OK);
    assert_eq!(detail_body["Id"], 77);
    assert_eq!(detail_body["SecondaryCoilId"], 77);
    assert_eq!(detail_body["CoilNo"], "SECONDARY-ONLY-0077");
    assert_eq!(detail_body["hasCoil"], false);
    assert_eq!(detail_body["AlarmInfo"], json!({}));
    assert_eq!(detail_body["childrenCoil"], json!([]));
    assert_eq!(detail_body["childrenAlarmInfo"], json!([]));
    assert_eq!(
        detail_body["childrenCoilDefect"]
            .as_array()
            .expect("detail defects")
            .len(),
        2
    );
    assert_eq!(
        detail_body["defects"]
            .as_array()
            .expect("defects alias")
            .len(),
        2
    );
    assert_eq!(
        detail_body["childrenCoilDefect"][0]["defectTime"],
        "2026-06-28T08:02:03"
    );
    assert_eq!(detail_body["defects"][0]["defectTime"]["year"], 2026);
    assert_eq!(detail_body["defects"][0]["defectTime"]["month"], 6);
    assert_ne!(detail_body["defects"], detail_body["childrenCoilDefect"]);
    assert_eq!(detail_body["maxDefectName"], "数据脏污");
    assert_eq!(detail_body["maxDefectLevel"], 3);
    assert_eq!(detail_body["maxDefectSurface"], "S");
}

#[tokio::test]
async fn detail_endpoint_rejects_non_python_int_converter_paths_like_python() {
    for uri in ["/detail/abc", "/detail/-1"] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"})
        );
    }
}

#[tokio::test]
async fn detail_endpoint_returns_python_error_body_when_missing() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/detail/404").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"error": "Coil not found"}));
}

#[tokio::test]
async fn detail_endpoint_returns_alarm_detail_children() {
    let (status, body) = request_json(app_with_alarm_rows(), "GET", "/detail/42").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["childrenTaperShapePoint"][0]["Id"], 111);
    assert_eq!(body["childrenTaperShapePoint"][0]["surface"], "S");
    assert_eq!(body["childrenTaperShapePoint"][0]["x"], 501);
    assert_eq!(body["childrenTaperShapePoint"][0]["value"], 12.5);
    assert_eq!(body["childrenTaperShapePoint"][0]["err_msg"], "塔形点报警");
    assert_eq!(body["childrenAlarmFlatRoll"][0]["Id"], 81);
    assert_eq!(body["childrenAlarmFlatRoll"][0]["surface"], "S");
    assert_eq!(body["childrenAlarmFlatRoll"][0]["err_msg"], "扁卷报警");
    assert_eq!(
        body["childrenAlarmFlatRoll"][0]["crateTime"],
        "2026-06-27T12:41:00"
    );
    assert_eq!(body["childrenAlarmTaperShape"][0]["Id"], 91);
    assert_eq!(
        body["childrenAlarmTaperShape"][0]["out_taper_max_value"],
        3.4
    );
    assert_eq!(body["childrenAlarmTaperShape"][0]["err_msg"], "塔形报警");
    assert_eq!(
        body["childrenAlarmTaperShape"][0]["crateTime"],
        "2026-06-27T12:42:00"
    );
    assert_eq!(body["childrenAlarmLooseCoil"][0]["Id"], 101);
    assert_eq!(body["childrenAlarmLooseCoil"][0]["max_width"], 200.0);
    assert_eq!(body["childrenAlarmLooseCoil"][0]["err_msg"], "松卷报警");
    assert_eq!(
        body["childrenAlarmLooseCoil"][0]["crateTime"],
        "2026-06-27T12:43:00"
    );
}

#[tokio::test]
async fn coil_alarm_endpoint_returns_python_empty_alarm_sections() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/coilAlarm/42").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["FlatRoll"], json!({}));
    assert_eq!(body["TaperShape"], json!({"S": [], "L": []}));
    assert_eq!(body["LooseCoil"], json!({"L": [], "S": []}));
}

#[tokio::test]
async fn coil_alarm_endpoint_returns_python_alarm_detail_sections() {
    let (status, body) = request_json(app_with_alarm_rows(), "GET", "/coilAlarm/42").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["FlatRoll"]["S"]["Id"], 81);
    assert_eq!(body["FlatRoll"]["S"]["secondaryCoilId"], 42);
    assert_eq!(body["FlatRoll"]["S"]["out_circle_width"], 401.0);
    assert_eq!(body["FlatRoll"]["S"]["level"], 2);
    assert_eq!(body["FlatRoll"]["S"]["crateTime"]["year"], 2026);
    assert_eq!(
        body["FlatRoll"]["S"]
            .as_object()
            .expect("flat roll object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "secondaryCoilId",
            "out_circle_height",
            "inner_circle_center_x",
            "data",
            "surface",
            "inner_circle_center_y",
            "out_circle_center_x",
            "inner_circle_radius",
            "accuracy_x",
            "out_circle_center_y",
            "accuracy_y",
            "out_circle_radius",
            "level",
            "Id",
            "inner_circle_width",
            "err_msg",
            "out_circle_width",
            "inner_circle_height",
            "crateTime",
        ]
    );

    assert_eq!(body["TaperShape"]["S"][0]["Id"], 91);
    assert_eq!(body["TaperShape"]["S"][0]["out_taper_max_x"], 101);
    assert_eq!(body["TaperShape"]["S"][0]["out_taper_max_value"], 3.4);
    assert_eq!(body["TaperShape"]["S"][0]["err_msg"], "塔形报警");
    assert_eq!(body["TaperShape"]["L"], json!([]));
    assert_eq!(
        body["TaperShape"]["S"][0]
            .as_object()
            .expect("taper shape object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "in_taper_max_x",
            "err_msg",
            "surface",
            "in_taper_max_y",
            "crateTime",
            "out_taper_max_x",
            "in_taper_max_value",
            "data",
            "out_taper_max_y",
            "in_taper_min_x",
            "Id",
            "out_taper_max_value",
            "in_taper_min_y",
            "out_taper_min_x",
            "in_taper_min_value",
            "out_taper_min_y",
            "rotation_angle",
            "secondaryCoilId",
            "out_taper_min_value",
            "level",
        ]
    );

    assert_eq!(body["LooseCoil"]["S"][0]["Id"], 101);
    assert_eq!(body["LooseCoil"]["S"][0]["max_width"], 20.0);
    assert_eq!(body["LooseCoil"]["S"][0]["rotation_angle"], 2.5);
    assert_eq!(body["LooseCoil"]["S"][0]["err_msg"], "松卷报警");
    assert_eq!(body["LooseCoil"]["L"], json!([]));
    assert_eq!(
        body["LooseCoil"]["S"][0]
            .as_object()
            .expect("loose coil object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        vec![
            "surface",
            "Id",
            "secondaryCoilId",
            "rotation_angle",
            "err_msg",
            "data",
            "max_width",
            "level",
            "crateTime",
        ]
    );
    let loose_data: Value = serde_json::from_str(
        body["LooseCoil"]["S"][0]["data"]
            .as_str()
            .expect("loose data"),
    )
    .expect("loose data json");
    assert_eq!(loose_data["max_width_raw"], 200.0);
    assert_eq!(loose_data["max_width_mm"], 20.0);
    assert_eq!(loose_data["max_width_scale"], 0.1);
    assert_eq!(loose_data["max_width_unit"], "mm");
}

#[tokio::test]
async fn coil_alarm_endpoint_rounds_mysql_float_values_like_python_driver() {
    let repository = InMemoryCoilRepository::new()
        .with_alarm_flat_rolls(vec![AlarmFlatRollRow {
            id: 1136,
            secondary_coil_id: 77,
            surface: "L".to_string(),
            out_circle_width: Some(5686.38330078125),
            out_circle_height: Some(6905.78125),
            out_circle_center_x: Some(3453.325439453125),
            out_circle_center_y: Some(2860.146728515625),
            out_circle_radius: Some(3449.0),
            inner_circle_width: Some(2224.94384765625),
            inner_circle_height: Some(2659.5966796875),
            inner_circle_center_x: Some(3458.19677734375),
            inner_circle_center_y: Some(2867.544189453125),
            inner_circle_radius: Some(1332.0),
            accuracy_x: Some(0.33943653106689453),
            accuracy_y: Some(1.0),
            level: None,
            err_msg: None,
            crate_time: Some("2025-01-05 16:44:25".to_string()),
            data: None,
        }])
        .with_alarm_taper_shapes(vec![AlarmTaperShapeRow {
            id: 983,
            secondary_coil_id: 77,
            surface: "L".to_string(),
            out_taper_max_x: Some(6843),
            out_taper_max_y: Some(2867),
            out_taper_max_value: Some(9.05713176727295),
            out_taper_min_x: Some(6843),
            out_taper_min_y: Some(2867),
            out_taper_min_value: Some(9.05713176727295),
            in_taper_max_x: Some(2958),
            in_taper_max_y: Some(40),
            in_taper_max_value: Some(61.69044494628906),
            in_taper_min_x: Some(2958),
            in_taper_min_y: Some(40),
            in_taper_min_value: Some(61.69044494628906),
            rotation_angle: Some(260.0),
            level: Some(2),
            err_msg: Some("塔形报警".to_string()),
            crate_time: Some("2025-01-05 16:44:25".to_string()),
            data: None,
        }])
        .with_alarm_loose_coils(vec![AlarmLooseCoilRow {
            id: 984,
            secondary_coil_id: 77,
            surface: "L".to_string(),
            max_width: Some(5.0),
            rotation_angle: Some(0.0),
            level: Some(1),
            err_msg: Some("正常".to_string()),
            crate_time: Some("2025-01-05 16:44:25".to_string()),
            data: None,
        }])
        .with_coil_states(vec![CoilStateRow {
            id: 985,
            secondary_coil_id: 77,
            surface: "L".to_string(),
            start_time: Some("2025-01-05 16:44:25".to_string()),
            scan3d_coordinate_scale_x: Some(0.33943653106689453),
            scan3d_coordinate_scale_y: Some(1.0),
            scan3d_coordinate_scale_z: Some(1.0),
            rotate: Some(0),
            x_rotate: Some(0),
            median_3d: Some(0.0),
            median_3d_mm: Some(0.0),
            color_from_value_mm: Some(0.0),
            color_to_value_mm: Some(0.0),
            start: Some(0.0),
            step: Some(0.0),
            upper_limit: Some(0.0),
            lower_limit: Some(0.0),
            lower_area: Some(0),
            upper_area: Some(0),
            lower_area_percent: Some(0.0),
            upper_area_percent: Some(0.0),
            mask_area: Some(0),
            width: Some(0),
            height: Some(0),
            json_data: None,
        }]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let (status, body) = request_json(app, "GET", "/coilAlarm/77").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["FlatRoll"]["L"]["out_circle_width"], 5686.38);
    assert_eq!(body["FlatRoll"]["L"]["out_circle_height"], 6905.78);
    assert_eq!(body["FlatRoll"]["L"]["out_circle_center_x"], 3453.33);
    assert_eq!(body["FlatRoll"]["L"]["inner_circle_center_x"], 3458.2);
    assert_eq!(body["FlatRoll"]["L"]["accuracy_x"], 0.339437);
    assert_eq!(body["TaperShape"]["L"][0]["out_taper_max_value"], 9.05713);
    assert_eq!(body["TaperShape"]["L"][0]["in_taper_max_value"], 61.6904);
    assert_eq!(body["LooseCoil"]["L"][0]["max_width"], 5.0);
    assert_eq!(
        body["LooseCoil"]["L"][0]["data"],
        "{\"max_width_raw\": 5.0, \"max_width_mm\": 5.0, \"max_width_unit\": \"mm\", \"max_width_scale\": 0.339437, \"max_width_scale_axis\": \"x\"}"
    );
}

#[tokio::test]
async fn coil_alarm_get_info_legacy_schema_route_returns_null_like_python() {
    let response = request_response(app_with_seed_data(), "GET", "/coilAlarm/get_info").await;
    let status = response.status();
    let headers = response.headers().clone();
    let body = response_json(response).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "application/json");
    assert_eq!(body, Value::Null);
}

#[tokio::test]
async fn detail_endpoint_does_not_use_testdata_fallback_like_python() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    fs::create_dir_all(&testdata_dir).expect("create testdata dir");
    fs::write(testdata_dir.join("3D.npz"), b"placeholder").expect("create testdata marker");

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/detail/193113",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, json!({"error": "Coil not found"}));

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn coil_list_uses_testdata_fallback_when_enabled_and_database_empty() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    fs::create_dir_all(&testdata_dir).expect("create testdata dir");
    fs::write(testdata_dir.join("3D.npz"), b"placeholder").expect("create testdata marker");
    let state = test_state(testdata_dir.clone());

    let (status, body) = request_json(build_app(state), "GET", "/coilList/20").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().expect("array").len(), 1);
    assert_eq!(body[0]["Id"], 193113);
    assert_eq!(body[0]["CoilNo"], "193113");
    assert_eq!(body[0]["CoilType"], "TestData");
    assert_eq!(body[0]["NextInfo"], "测试模式");
    assert_eq!(body[0]["hasCoil"], true);
    assert_eq!(body[0]["AlarmInfo"]["S"]["taperShapeMsg"], "测试模式");

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn data_has_returns_testdata_surface_asset_flags() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);
    write_testdata_surface(&testdata_dir, "L", 10, 20);

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/data_has/193113",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        body["S"],
        json!({"3D": true, "MESH": true, "JPG": true, "2D": true})
    );
    assert_eq!(
        body["L"],
        json!({"3D": true, "MESH": true, "JPG": true, "2D": true})
    );

    let (fallback_status, fallback_body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/data_has/999999999",
    )
    .await;

    assert_eq!(fallback_status, StatusCode::OK);
    assert_eq!(fallback_body["S"], body["S"]);
    assert_eq!(fallback_body["L"], body["L"]);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn data_has_and_coil_info_reject_non_python_int_converter_paths_like_python() {
    for uri in [
        "/data_has/abc",
        "/data_has/-1",
        "/coilInfo/abc/S",
        "/coilInfo/-1/S",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn data_has_uses_runtime_configured_surface_folders_when_not_in_test_mode() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);

    let s_coil_dir = save_s.join("123");
    fs::create_dir_all(s_coil_dir.join("jpg")).expect("s jpg dir");
    fs::create_dir_all(s_coil_dir.join("meshes")).expect("s mesh dir");
    fs::write(s_coil_dir.join("3D.npy"), b"legacy depth marker").expect("3d marker");
    fs::write(s_coil_dir.join("jpg").join("GRAY.jpg"), b"gray").expect("gray marker");
    fs::write(s_coil_dir.join("jpg").join("AREA.jpg"), b"area").expect("area marker");
    fs::write(
        s_coil_dir.join("meshes").join("defaultobject_mesh.mesh"),
        b"mesh",
    )
    .expect("mesh marker");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let (status, body) = request_json(app_with_data_config(config), "GET", "/data_has/123").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        body["S"],
        json!({"3D": true, "MESH": true, "JPG": true, "2D": true})
    );
    assert_eq!(
        body["L"],
        json!({"3D": false, "MESH": false, "JPG": false, "2D": false})
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn data_has_mesh_flag_matches_python_default_mesh_filename() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);

    let s_mesh_dir = save_s.join("123").join("meshes");
    let l_mesh_dir = save_l.join("123").join("meshes");
    fs::create_dir_all(&s_mesh_dir).expect("s mesh dir");
    fs::create_dir_all(&l_mesh_dir).expect("l mesh dir");
    fs::write(s_mesh_dir.join("defaultobject.obj"), b"obj").expect("legacy obj marker");
    fs::write(l_mesh_dir.join("defaultobject_mesh.mesh"), b"mesh").expect("python mesh marker");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let (status, body) = request_json(app_with_data_config(config), "GET", "/data_has/123").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["S"]["MESH"], false);
    assert_eq!(body["L"]["MESH"], true);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn coil_info_uses_runtime_configured_surface_depth_when_not_in_test_mode() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_real_npy_coil(&save_s, 321);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let (status, body) = request_json(app_with_data_config(config), "GET", "/coilInfo/321/S").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["coilId"], "321");
    assert_eq!(body["surface"], "S");
    assert_eq!(body["height"], 2);
    assert_eq!(body["width"], 3);
    assert_eq!(body["median_3d"], 30.0);
    assert_eq!(body["median_3d_mm"], 30.0 * 0.016229506582021713);
    assert_eq!(
        body["circleConfig"]["inner_circle"]["circlex"],
        json!([1, 1])
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn coil_info_prefers_latest_matching_coil_state_json_like_python() {
    let repository = InMemoryCoilRepository::new().with_coil_states(vec![
        coil_state_json_row(
            21,
            321,
            "L",
            json!({"coilId":"321","surface":"L","source":"newer-l-1"}),
        ),
        coil_state_json_row(
            20,
            321,
            "L",
            json!({"coilId":"321","surface":"L","source":"newer-l-2"}),
        ),
        coil_state_json_row(
            19,
            321,
            "S",
            json!({
                "coilId": "321",
                "surface": "S",
                "source": "coil-state-json",
                "width": 7000,
                "height": 5200,
                "median_3d_mm": 936.9
            }),
        ),
    ]);

    let (status, body) = request_json(
        build_app(ApiState::new(Arc::new(repository))),
        "GET",
        "/coilInfo/321/S",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["coilId"], "321");
    assert_eq!(body["surface"], "S");
    assert_eq!(body["source"], "coil-state-json");
    assert_eq!(body["width"], 7000);
    assert_eq!(body["height"], 5200);
    assert_eq!(body["median_3d_mm"], 936.9);
}

#[tokio::test]
async fn coil_info_preserves_python_jsondata_number_text_while_compacting() {
    let repository = InMemoryCoilRepository::new().with_coil_states(vec![CoilStateRow {
        id: 19,
        secondary_coil_id: 321,
        surface: "S".to_string(),
        start_time: Some("2026-06-27 12:35:11".to_string()),
        scan3d_coordinate_scale_x: None,
        scan3d_coordinate_scale_y: None,
        scan3d_coordinate_scale_z: None,
        rotate: None,
        x_rotate: None,
        median_3d: None,
        median_3d_mm: None,
        color_from_value_mm: None,
        color_to_value_mm: None,
        start: None,
        step: None,
        upper_limit: None,
        lower_limit: None,
        lower_area: None,
        upper_area: None,
        lower_area_percent: None,
        upper_area_percent: None,
        mask_area: None,
        width: None,
        height: None,
        json_data: Some(
            r#"{"coilId": "321", "surface": "S", "circleConfig": {"inner_circle": [[1, 2], 920.3406982421875]}, "lowerArea_percent": 3.740283839108058e-05, "tinyArea_percent": 1.1065523612831493e-07, "upperArea_percent": 0.00040743257942445557}"#
                .to_string(),
        ),
    }]);

    let response = request_response(
        build_app(ApiState::new(Arc::new(repository))),
        "GET",
        "/coilInfo/321/S",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let content_type = response
        .headers()
        .get(header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok());
    assert_eq!(content_type, Some("application/json"));
    let body = String::from_utf8(response_bytes(response).await.to_vec()).expect("utf8 body");
    assert_eq!(
        body,
        r#"{"coilId":"321","surface":"S","circleConfig":{"inner_circle":[[1,2],920.3406982421875]},"lowerArea_percent":0.00003740283839108058,"tinyArea_percent":1.1065523612831493e-7,"upperArea_percent":0.00040743257942445557}"#
    );
}

#[tokio::test]
async fn height_data_and_point_use_runtime_configured_surface_depth_when_not_in_test_mode() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_real_npy_coil(&save_s, 321);
    write_runtime_long_line_npy_coil(&save_s, 322);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let (point_status, point_body) = request_json(
        app_with_data_config(config.clone()),
        "GET",
        "/coilData/heightPoint/S/321?x=2&y=1",
    )
    .await;

    assert_eq!(point_status, StatusCode::OK);
    assert_eq!(point_body, json!(2600));

    let (line_status, line_body) = request_json(
        app_with_data_config(config),
        "GET",
        "/coilData/heightData/S/322?x1=0&y1=0&x2=104&y2=0",
    )
    .await;

    assert_eq!(line_status, StatusCode::OK);
    let segments = line_body.as_array().expect("segments");
    assert_eq!(segments.len(), 1);
    assert_eq!(segments[0]["pointL"], json!([0, 0]));
    assert_eq!(segments[0]["pointR"], json!([104, 0]));
    assert_eq!(segments[0]["points"].as_array().expect("points").len(), 105);
    assert_eq!(segments[0]["points"][0], json!([0, 0, 500]));
    assert_eq!(segments[0]["points"][104], json!([104, 0, 604]));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn height_point_websocket_uses_runtime_configured_surface_depth_when_not_in_test_mode() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_real_npy_coil(&save_s, 321);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let ws_url = spawn_test_server(app_with_data_config(config)).await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text(
            json!({
                "id": 79,
                "surfaceKey": "S",
                "coilId": "321",
                "x": 2,
                "y": 1
            })
            .to_string()
            .into(),
        ))
        .await
        .expect("send request");

    let message = socket
        .next()
        .await
        .expect("websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");

    assert_eq!(body["id"], 79);
    assert_eq!(body["surface_key"], "S");
    assert_eq!(body["coil_id"], "321");
    assert_eq!(body["value"], 2600);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_serves_runtime_configured_cached_images_when_not_in_test_mode() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_render_cached_coil(&save_s, 323);
    write_runtime_named_gray_image(
        &coil_dir,
        "cache/falsecolor/gray",
        "thumbnail_1024",
        1024,
        256,
    );

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let preview_response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/323?grayscale=true&thumbnail=true",
    )
    .await;
    let preview_headers = preview_response.headers().clone();
    let preview_bytes = response_bytes(preview_response).await;
    let preview_image =
        image::load_from_memory(&preview_bytes).expect("runtime falsecolor gray thumbnail");

    assert_eq!(preview_headers["x-thumbnail"], "true");
    assert_eq!(preview_headers["x-colormap"], "GRAY");
    assert_eq!(preview_headers["x-from-cache"], "true");
    assert_eq!(
        preview_image.dimensions(),
        (1024, 256),
        "Python Render thumbnail reads cache/falsecolor/gray/thumbnail_1024.jpg, not preview/GRAY.jpg"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_thumbnail_prefers_falsecolor_cache_over_preview_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("334");
    fs::create_dir_all(&coil_dir).expect("falsecolor cache coil dir");
    let array = ndarray::Array2::<f64>::from_shape_fn((512, 2048), |(y, x)| ((x + y) % 351) as f64);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write render npy");
    write_runtime_named_gray_image(&coil_dir, "preview", "JET", 64, 32);
    write_runtime_named_gray_image(
        &coil_dir,
        "cache/falsecolor/jet",
        "thumbnail_1024",
        1024,
        256,
    );

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/334?thumbnail=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("falsecolor thumbnail cache");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-colormap"], "JET");
    assert_eq!(headers["x-from-cache"], "true");
    assert_eq!(
        image.dimensions(),
        (1024, 256),
        "Python Render thumbnail uses cache/falsecolor/jet/thumbnail_1024.jpg instead of preview/JET.jpg"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_full_render_ignores_stale_jpg_cache_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_dynamic_render_coil(&save_s, 333);
    fs::create_dir_all(coil_dir.join("jpg")).expect("full render jpg dir");
    fs::write(
        coil_dir.join("jpg").join("JET.jpg"),
        b"\xff\xd8stale-full-render-cache\xff\xd9",
    )
    .expect("write stale render cache");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/333",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated full render jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "JET");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(image.dimensions(), (4, 2));
    assert_ne!(bytes.as_ref(), b"\xff\xd8stale-full-render-cache\xff\xd9");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_preview_route_serves_runtime_preview_cache_from_main_api() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_render_cached_coil(&save_s, 501);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/preview/S/501/GRAY",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(bytes.as_ref(), b"\xff\xd8runtime-gray-preview\xff\xd9");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_source_route_serves_runtime_named_source_image_from_main_api() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 502, 40, 30);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/source/S/502/GRAY",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("source image");

    assert_eq!(image.dimensions(), (40, 30));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_source_route_mask_query_prefers_mask_png_then_uses_placeholder_when_missing_mask() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 503, 40, 30);
    fs::create_dir_all(coil_dir.join("mask")).expect("create source mask dir");
    let mut mask_image = GrayImage::new(10, 12);
    for y in 0..12 {
        for x in 0..10 {
            mask_image.put_pixel(x, y, Luma([((x * 8 + y * 5) % 255) as u8]));
        }
    }
    mask_image
        .save_with_format(coil_dir.join("mask").join("GRAY.png"), ImageFormat::Png)
        .expect("write source mask image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let mask_response = request_response(
        app_with_data_config(config.clone()),
        "GET",
        "/image/source/S/503/GRAY?mask=true",
    )
    .await;
    assert_eq!(mask_response.status(), StatusCode::OK);

    let with_mask_image = image::load_from_memory(&response_bytes(mask_response).await)
        .expect("masked source image");
    assert_eq!(with_mask_image.dimensions(), (10, 12));

    let source_response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/source/S/503/GRAY",
    )
    .await;
    assert_eq!(source_response.status(), StatusCode::OK);
    let source_image =
        image::load_from_memory(&response_bytes(source_response).await).expect("source image");
    assert_eq!(source_image.dimensions(), (40, 30));

    fs::remove_file(coil_dir.join("mask").join("GRAY.png")).expect("remove mask image");
    let fallback_config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let fallback_response = request_response(
        app_with_data_config(fallback_config),
        "GET",
        "/image/source/S/503/GRAY?mask=true",
    )
    .await;
    assert_eq!(fallback_response.status(), StatusCode::OK);
    let fallback_bytes = response_bytes(fallback_response).await;
    assert_eq!(
        fallback_bytes.as_ref(),
        b"\xff\xd8\xff\xdb\x00\x43\x00\xff\xd9",
        "Python route falls back to placeholder when mask file is missing"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_returns_runtime_area_metadata_from_main_api() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("503");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/503?count=0",
    )
    .await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);

    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("area metadata json");

    assert_eq!(body["width"], 90);
    assert_eq!(body["height"], 60);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_missing_metadata_returns_placeholder_jpeg_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    fs::create_dir_all(save_s.join("511")).expect("coil dir");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/511?count=0",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");

    let bytes = response_bytes(response).await;
    assert!(bytes.starts_with(&[0xff, 0xd8]));
    assert!(bytes.ends_with(&[0xff, 0xd9]));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_crops_runtime_area_tile_from_main_api() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("504");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/504?row=1&col=2&count=3&level=4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-tile-level"], "4");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("area tile image");

    assert_eq!(image.dimensions(), (30, 20));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_fallback_uses_python_swapped_row_col_crop_axes() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("506");
    fs::create_dir_all(coil_dir.join("png")).expect("runtime area png dir");
    let mut source = GrayImage::new(90, 60);
    for y in 0..60 {
        for x in 0..90 {
            let tile_x = x / 30;
            let tile_y = y / 20;
            source.put_pixel(x, y, Luma([(tile_y * 80 + tile_x * 20) as u8]));
        }
    }
    source
        .save_with_format(coil_dir.join("png").join("AREA.png"), ImageFormat::Png)
        .expect("write runtime area png");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/506?row=1&col=2&count=3&level=4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-cache"], "fallback");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("area tile image")
        .to_luma8();

    assert_eq!(image.dimensions(), (30, 20));
    let first_pixel = image.get_pixel(0, 0)[0];
    assert!(
        first_pixel.abs_diff(180) <= 2,
        "Python's fallback crop uses x=row and y=col, expected tile value near 180, got {first_pixel}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_preview_and_full_use_jpeg_content_type_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("512");
    write_runtime_named_gray_png_image(&coil_dir, "preview", "AREA", 40, 30);
    write_runtime_named_gray_png_image(&coil_dir, "png", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_data_config(config);

    let preview_response =
        request_response(app.clone(), "GET", "/image/area/S/512/AREA?row=-2&count=3").await;
    let preview_status = preview_response.status();
    let preview_headers = preview_response.headers().clone();
    let preview_bytes = response_bytes(preview_response).await;

    assert_eq!(preview_status, StatusCode::OK);
    assert_eq!(preview_headers["content-type"], "image/jpeg");
    assert_eq!(
        image::load_from_memory(&preview_bytes)
            .expect("png-backed area preview")
            .dimensions(),
        (40, 30)
    );

    let full_response = request_response(app, "GET", "/image/area/S/512/AREA?row=-1&count=3").await;
    let full_status = full_response.status();
    let full_headers = full_response.headers().clone();
    let full_bytes = response_bytes(full_response).await;

    assert_eq!(full_status, StatusCode::OK);
    assert_eq!(full_headers["content-type"], "image/jpeg");
    assert_eq!(
        image::load_from_memory(&full_bytes)
            .expect("png-backed area full image")
            .dimensions(),
        (90, 60)
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_fallback_encodes_grayscale_jpeg_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("507");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/507?row=1&col=2&count=3&level=4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-cache"], "fallback");

    let bytes = response_bytes(response).await;

    assert_eq!(jpeg_sof_component_count(&bytes), Some(1));

    let image = image::load_from_memory(&bytes).expect("area tile image");

    assert_eq!(image.dimensions(), (30, 20));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_fallback_resizes_lower_level_tiles_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("509");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 1200, 900);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/509?row=1&col=2&count=3&level=0",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-tile-level"], "0");
    assert_eq!(headers["x-cache"], "fallback");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("level 0 area tile image");

    assert_eq!(image.dimensions(), (340, 255));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_normalizes_positive_count_to_three_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("510");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 900, 600);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/510?row=1&col=1&count=2&level=4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-cache"], "fallback");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("count-normalized area tile image");

    assert_eq!(image.dimensions(), (300, 200));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_reuses_fallback_generated_tile_cache() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("508");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_data_config(config);
    let uri = "/image/area/S/508?row=1&col=2&count=3&level=2";
    let cache_path = coil_dir
        .join("cache")
        .join("area")
        .join("tild")
        .join("L2")
        .join("2_1.jpg");

    let first_response = request_response(app.clone(), "GET", uri).await;
    let first_headers = first_response.headers().clone();
    assert_eq!(first_response.status(), StatusCode::OK);
    assert_eq!(first_headers["x-cache"], "fallback");
    assert!(
        cache_path.exists(),
        "fallback tile generation should populate the Python-compatible AREA tile cache"
    );

    let second_response = request_response(app, "GET", uri).await;
    let second_headers = second_response.headers().clone();
    assert_eq!(second_response.status(), StatusCode::OK);
    assert_eq!(second_headers["x-cache"], "hit");

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_fallback_prefetches_full_l4_tile_cache_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("515");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_data_config(config);

    let first_response = request_response(
        app.clone(),
        "GET",
        "/image/area/S/515?row=1&col=2&count=3&level=4",
    )
    .await;
    let first_headers = first_response.headers().clone();
    assert_eq!(first_response.status(), StatusCode::OK);
    assert_eq!(first_headers["x-cache"], "fallback");

    for row in 0..3 {
        for col in 0..3 {
            let cache_path = coil_dir
                .join("cache")
                .join("area")
                .join("tild")
                .join("L4")
                .join(format!("{col}_{row}.jpg"));
            assert!(
                cache_path.exists(),
                "fallback AREA tile generation should prefetch the full L4 cache, missing {cache_path:?}"
            );
        }
    }

    let lower_response =
        request_response(app, "GET", "/image/area/S/515?row=0&col=0&count=3&level=2").await;
    let lower_headers = lower_response.headers().clone();
    assert_eq!(lower_response.status(), StatusCode::OK);
    assert_eq!(lower_headers["x-tile-level"], "2");
    assert_eq!(lower_headers["x-cache"], "miss");

    let bytes = response_bytes(lower_response).await;
    let image = image::load_from_memory(&bytes).expect("L4-backed lower-level area tile");
    assert_eq!(image.dimensions(), (30, 20));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_ignores_stale_tile_cache_after_source_update() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("511");
    let cache_path = coil_dir
        .join("cache")
        .join("area")
        .join("tild")
        .join("L4")
        .join("2_1.jpg");
    fs::create_dir_all(cache_path.parent().expect("stale AREA cache parent"))
        .expect("stale AREA cache dir");
    GrayImage::from_pixel(30, 20, Luma([9]))
        .save_with_format(&cache_path, ImageFormat::Jpeg)
        .expect("write stale AREA tile cache");

    std::thread::sleep(Duration::from_millis(1100));

    fs::create_dir_all(coil_dir.join("png")).expect("runtime area png dir");
    let mut source = GrayImage::new(90, 60);
    for y in 0..60 {
        for x in 0..90 {
            let tile_x = x / 30;
            let tile_y = y / 20;
            source.put_pixel(x, y, Luma([(tile_y * 80 + tile_x * 20) as u8]));
        }
    }
    source
        .save_with_format(coil_dir.join("png").join("AREA.png"), ImageFormat::Png)
        .expect("write updated runtime area png");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/511?row=1&col=2&count=3&level=4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-cache"], "fallback");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("fresh area tile image")
        .to_luma8();

    assert_eq!(image.dimensions(), (30, 20));
    let first_pixel = image.get_pixel(0, 0)[0];
    assert!(
        first_pixel.abs_diff(180) <= 2,
        "stale cache should be regenerated from the updated source image, got {first_pixel}"
    );

    let refreshed_cache = image::open(cache_path)
        .expect("refreshed AREA cache")
        .to_luma8();
    assert!(
        refreshed_cache.get_pixel(0, 0)[0].abs_diff(180) <= 2,
        "fallback regeneration should replace the stale AREA tile cache"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_invalid_row_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/image/area/S/193113?row=abc&col=2&count=3&level=4",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "row"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn image_area_typed_route_invalid_row_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/image/area/S/193113/AREA?row=abc&col=2&count=3&level=4",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "row"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn image_area_route_out_of_range_query_returns_fastapi_validation_error() {
    let cases = [
        (
            "/image/area/S/193113?row=-3&col=2&count=3&level=4",
            "row",
            "greater_than_equal",
            "Input should be greater than or equal to -2",
            "-3",
            json!({"ge": -2}),
        ),
        (
            "/image/area/S/193113?row=0&col=-1&count=3&level=4",
            "col",
            "greater_than_equal",
            "Input should be greater than or equal to 0",
            "-1",
            json!({"ge": 0}),
        ),
        (
            "/image/area/S/193113?row=0&col=2&count=4&level=4",
            "count",
            "less_than_equal",
            "Input should be less than or equal to 3",
            "4",
            json!({"le": 3}),
        ),
        (
            "/image/area/S/193113?row=0&col=2&count=3&level=5",
            "level",
            "less_than_equal",
            "Input should be less than or equal to 4",
            "5",
            json!({"le": 4}),
        ),
    ];

    for (uri, field, error_type, message, input, ctx) in cases {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
        assert_eq!(
            response_json(response).await,
            json!({
                "detail": [
                    {
                        "type": error_type,
                        "loc": ["query", field],
                        "msg": message,
                        "input": input,
                        "ctx": ctx
                    }
                ]
            })
        );
    }
}

#[tokio::test]
async fn image_area_route_serves_python_area_tile_cache_when_available() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("505");
    write_runtime_named_gray_image(&coil_dir, "jpg", "AREA", 90, 60);
    write_runtime_named_gray_image(
        &coil_dir.join("cache").join("area").join("tild").join("L2"),
        "",
        "2_1",
        17,
        13,
    );

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/505?row=1&col=2&count=3&level=2",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-tile-level"], "2");
    assert_eq!(headers["x-cache"], "hit");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("cached area tile image");

    assert_eq!(image.dimensions(), (17, 13));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_serves_tile_cache_when_source_is_missing_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("513");
    write_runtime_named_gray_image(
        &coil_dir.join("cache").join("area").join("tild").join("L2"),
        "",
        "2_1",
        17,
        13,
    );

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/513?row=1&col=2&count=3&level=2",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-tile-level"], "2");
    assert_eq!(headers["x-cache"], "hit");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("source-missing cached area tile image");

    assert_eq!(image.dimensions(), (17, 13));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_resizes_l4_cache_when_requested_level_is_missing_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("514");
    let l4_dir = coil_dir.join("cache").join("area").join("tild").join("L4");
    for row in 0..3 {
        for col in 0..3 {
            write_runtime_named_gray_image(&l4_dir, "", &format!("{col}_{row}"), 2000, 1500);
        }
    }

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/514?row=1&col=2&count=3&level=2",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-tile-level"], "2");
    assert_eq!(headers["x-cache"], "miss");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("resized l4 cached area tile");

    assert_eq!(image.dimensions(), (1364, 1023));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_route_uses_l4_tile_cache_for_metadata_when_source_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("506");
    write_runtime_named_gray_image(
        &coil_dir.join("cache").join("area").join("tild").join("L4"),
        "",
        "0_0",
        21,
        19,
    );

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/image/area/S/506?count=0",
    )
    .await;
    let status = response.status();

    assert_eq!(status, StatusCode::OK);

    let body: Value =
        serde_json::from_slice(&response_bytes(response).await).expect("area metadata json");

    assert_eq!(body["width"], 63);
    assert_eq!(body["height"], 57);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn image_area_startup_cleanup_removes_legacy_tile_cache_only_when_enabled() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("507");
    let legacy_tile = coil_dir
        .join("cache")
        .join("area")
        .join("tild")
        .join("1_2.jpg");
    let level_tile = coil_dir
        .join("cache")
        .join("area")
        .join("tild")
        .join("L4")
        .join("1_2.jpg");
    fs::create_dir_all(legacy_tile.parent().expect("legacy parent")).expect("legacy dir");
    fs::create_dir_all(level_tile.parent().expect("level parent")).expect("level dir");
    fs::write(&legacy_tile, b"old").expect("legacy tile");
    fs::write(&level_tile, b"current").expect("level tile");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    {
        let _cleanup_guard = set_env_var_guard("CACHE_AREA_CLEANUP_ON_STARTUP", "true");
        let _app = app_with_data_config(config);
    }

    assert!(
        !legacy_tile.exists(),
        "legacy cache/area/tild/col_row.jpg tile should be removed"
    );
    assert!(
        level_tile.exists(),
        "levelled cache/area/tild/L4/col_row.jpg tile should be preserved"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_routes_return_qml_safe_status_and_queue_shapes() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_scan_area_join_config(
        &join_config_path,
        &root.join("Cap_S_D"),
        &root.join("Cap_L_U"),
        &root.join("Save_S"),
        &root.join("Save_L"),
    );
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let clip_response = request_json_body(
        app.clone(),
        "POST",
        "/clip_config",
        json!({
            "surface_key": "s",
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0,
            "c": 2500.0
        }),
    )
    .await;
    let clip_status = clip_response.status();

    assert_eq!(clip_status, StatusCode::OK);

    let clip_body: Value =
        serde_json::from_slice(&response_bytes(clip_response).await).expect("clip json");

    assert_eq!(clip_body["status"], "ok");
    assert_eq!(clip_body["surface_key"], "S");
    assert_eq!(clip_body["clip_config"]["mode"], "dynamic");
    assert_eq!(clip_body["clip_config"]["fixed"], 180);
    assert_eq!(clip_body["clip_config"]["offset"], 40);

    let rejoin_response = request_json_body(
        app.clone(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 193113, "surface_key": "L"}),
    )
    .await;
    let rejoin_status = rejoin_response.status();

    assert_eq!(rejoin_status, StatusCode::OK);

    let rejoin_body: Value =
        serde_json::from_slice(&response_bytes(rejoin_response).await).expect("rejoin json");

    assert_eq!(rejoin_body["status"], "queued");
    assert_eq!(rejoin_body["coil_id"], 193113);
    assert_eq!(rejoin_body["queued"], json!(["L"]));
    assert_eq!(rejoin_body["failed"], json!([]));

    let (status_status, status_body) = request_json(app.clone(), "GET", "/area/status").await;
    assert_eq!(status_status, StatusCode::OK);
    assert_eq!(status_body["status"], "ok");
    assert_eq!(status_body["scanner"]["enabled"], true);
    assert!(status_body["queueDepths"].get("join").is_some());
    assert!(status_body["surfaces"].get("S").is_some());
    assert!(status_body["surfaces"].get("L").is_some());

    let scan_response = request_json_body(app, "POST", "/area/scan", json!({})).await;
    let scan_status = scan_response.status();
    let scan_body: Value =
        serde_json::from_slice(&response_bytes(scan_response).await).expect("scan json");

    assert_eq!(scan_status, StatusCode::OK);
    assert_eq!(scan_body["status"], "ok");
    assert!(scan_body["scanner"]["lastScanTime"].as_f64().unwrap_or(0.0) > 0.0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_clip_config_persists_join_config_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_area_join_config(&join_config_path);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/clip_config",
        json!({
            "surface_key": "s",
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0,
            "c": 2500.0
        }),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("clip json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["surface_key"], "S");
    assert_eq!(body["clip_config"]["offset"], 77);

    let persisted: Value =
        serde_json::from_slice(&fs::read(&join_config_path).expect("persisted area join config"))
            .expect("persisted json");
    assert_eq!(
        persisted["surfaces"]["S"]["clip_config"],
        json!({
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0,
            "c": 2500.0,
            "offset": 77
        })
    );
    assert_eq!(persisted["surfaces"]["L"]["clip_config"]["offset"], 40);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_clip_config_defaults_l_surface_dynamic_c_like_qml() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_area_join_config(&join_config_path);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/clip_config",
        json!({
            "surface_key": "l",
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0
        }),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("clip json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["surface_key"], "L");
    assert_eq!(body["clip_config"]["c"], 4000.0);

    let persisted: Value =
        serde_json::from_slice(&fs::read(&join_config_path).expect("persisted area join config"))
            .expect("persisted json");
    assert_eq!(persisted["surfaces"]["L"]["clip_config"]["c"], 4000.0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_status_exposes_clip_config_for_qml() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_area_join_config(&join_config_path);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let (initial_status, initial_body) = request_json(app.clone(), "GET", "/area/status").await;
    assert_eq!(initial_status, StatusCode::OK);
    assert_eq!(
        initial_body["surfaces"]["S"]["clipConfig"],
        json!({
            "mode": "fixed",
            "fixed": 200,
            "a": 3.0,
            "b": 220.0,
            "c": 2600.0,
            "offset": 77
        })
    );

    let clip_response = request_json_body(
        app.clone(),
        "POST",
        "/clip_config",
        json!({
            "surface_key": "s",
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0,
            "c": 2500.0
        }),
    )
    .await;
    assert_eq!(clip_response.status(), StatusCode::OK);

    let (updated_status, updated_body) = request_json(app, "GET", "/area/status").await;
    assert_eq!(updated_status, StatusCode::OK);
    assert_eq!(
        updated_body["surfaces"]["S"]["clipConfig"],
        json!({
            "mode": "dynamic",
            "fixed": 180,
            "a": 2.5,
            "b": 210.0,
            "c": 2500.0,
            "offset": 77
        })
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_scan_reads_join_config_camera_folders_and_records_missing_area_work() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    write_scan_area_join_config(&join_config_path, &source_s, &source_l, &save_s, &save_l);
    write_area_camera_jpgs(&source_s, 71, 2);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(app_with_seed_data(), "POST", "/area/scan", json!({})).await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("scan json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["scanner"]["lastCandidates"], json!([71]));
    assert_eq!(
        body["scanner"]["queued"],
        json!([{"coil_id": 71, "reason": "S"}])
    );
    assert_eq!(body["scanner"]["skippedIncomplete"], 0);
    assert_eq!(body["scanner"]["skippedProcessed"], 0);
    assert_eq!(body["joinQueueSize"], 0);
    assert_eq!(body["queueDepths"]["join"], 0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_scan_records_grouped_surface_entries_and_clears_status_queue() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    write_scan_area_join_config(&join_config_path, &source_s, &source_l, &save_s, &save_l);
    write_area_camera_jpgs(&source_s, 72, 2);
    write_area_camera_jpgs(&source_l, 72, 2);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let scan_response =
        request_json_body(app_with_seed_data(), "POST", "/area/scan", json!({})).await;
    let scan_status = scan_response.status();
    let scan_body: Value =
        serde_json::from_slice(&response_bytes(scan_response).await).expect("scan json");

    assert_eq!(scan_status, StatusCode::OK);
    assert_eq!(scan_body["status"], "ok");
    assert_eq!(
        scan_body["scanner"]["queued"],
        json!([{"coil_id": 72, "reason": "S,L"}])
    );
    assert_eq!(scan_body["joinQueueSize"], 0);
    assert_eq!(scan_body["queueDepths"]["join"], 0);
    assert_eq!(scan_body["queueDepths"]["S"], 0);
    assert_eq!(scan_body["queueDepths"]["L"], 0);
    assert_eq!(scan_body["surfaces"]["S"]["queueSize"], 0);
    assert_eq!(scan_body["surfaces"]["S"]["lastCoilId"], Value::Null);
    assert_eq!(scan_body["surfaces"]["L"]["queueSize"], 0);
    assert_eq!(scan_body["surfaces"]["L"]["lastCoilId"], Value::Null);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_scan_processes_complete_camera_inputs_and_clears_queue() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    write_scan_area_join_config(&join_config_path, &source_s, &source_l, &save_s, &save_l);
    write_area_camera_rgb_jpgs(&source_s, 75, 3, 4, 20);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let scan_response = request_json_body(app.clone(), "POST", "/area/scan", json!({})).await;
    let scan_status = scan_response.status();
    let scan_body: Value =
        serde_json::from_slice(&response_bytes(scan_response).await).expect("scan json");

    assert_eq!(scan_status, StatusCode::OK);
    assert_eq!(scan_body["status"], "ok");
    assert_eq!(
        scan_body["scanner"]["queued"],
        json!([{"coil_id": 75, "reason": "S"}])
    );
    assert!(
        save_s.join("75").join("jpg").join("AREA.jpg").exists(),
        "scan should drive Rust's synchronous AREA fallback worker"
    );
    assert!(
        save_s
            .join("75")
            .join("cache")
            .join("area")
            .join("tild")
            .join("L4")
            .join("0_0.jpg")
            .exists(),
        "scan should create Python-compatible AREA tile cache"
    );
    assert_eq!(scan_body["joinQueueSize"], 0);
    assert_eq!(scan_body["queueDepths"]["join"], 0);
    assert_eq!(scan_body["queueDepths"]["S"], 0);
    assert_eq!(scan_body["surfaces"]["S"]["queueSize"], 0);

    let (status_status, status_body) = request_json(app, "GET", "/area/status").await;
    assert_eq!(status_status, StatusCode::OK);
    assert_eq!(status_body["joinQueueSize"], 0);
    assert_eq!(status_body["queueDepths"]["S"], 0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_writes_area_images_and_tile_cache_from_configured_camera_jpgs() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_u = root.join("Cap_S_U");
    let source_m = root.join("Cap_S_M");
    let source_d = root.join("Cap_S_D");
    let save_s = root.join("Save_S");
    write_rejoin_area_join_config(&join_config_path, &source_u, &source_m, &source_d, &save_s);
    write_area_camera_rgb_jpgs(&source_u, 72, 3, 4, 20);
    write_area_camera_rgb_jpgs(&source_m, 72, 3, 4, 80);
    write_area_camera_rgb_jpgs(&source_d, 72, 3, 4, 140);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 72, "surface_key": "S"}),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("rejoin json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "queued");
    assert_eq!(body["queued"], json!(["S"]));

    let area_path = save_s.join("72").join("jpg").join("AREA.jpg");
    let preview_path = save_s.join("72").join("preview").join("AREA.jpg");
    let tile_path = save_s
        .join("72")
        .join("cache")
        .join("area")
        .join("tild")
        .join("L4")
        .join("0_0.jpg");
    assert!(area_path.exists(), "AREA image should be written");
    assert!(preview_path.exists(), "AREA preview should be written");
    assert!(tile_path.exists(), "AREA L4 tile cache should be written");
    assert_eq!(
        image::open(&area_path).expect("area image").dimensions(),
        (6, 10)
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_clears_queue_after_synchronous_output_write() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_u = root.join("Cap_S_U");
    let source_m = root.join("Cap_S_M");
    let source_d = root.join("Cap_S_D");
    let save_s = root.join("Save_S");
    write_rejoin_area_join_config(&join_config_path, &source_u, &source_m, &source_d, &save_s);
    write_area_camera_rgb_jpgs(&source_u, 74, 3, 4, 20);
    write_area_camera_rgb_jpgs(&source_m, 74, 3, 4, 80);
    write_area_camera_rgb_jpgs(&source_d, 74, 3, 4, 140);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let rejoin_response = request_json_body(
        app.clone(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 74, "surface_key": "S"}),
    )
    .await;
    let rejoin_status = rejoin_response.status();
    let rejoin_body: Value =
        serde_json::from_slice(&response_bytes(rejoin_response).await).expect("rejoin json");

    assert_eq!(rejoin_status, StatusCode::OK);
    assert_eq!(rejoin_body["queued"], json!(["S"]));
    assert!(
        save_s.join("74").join("jpg").join("AREA.jpg").exists(),
        "synchronous Rust fallback should write AREA output before returning"
    );

    let (status_status, status_body) = request_json(app, "GET", "/area/status").await;
    assert_eq!(status_status, StatusCode::OK);
    assert_eq!(status_body["joinQueueSize"], 0);
    assert_eq!(status_body["queueDepths"]["join"], 0);
    assert_eq!(status_body["queueDepths"]["S"], 0);
    assert_eq!(status_body["surfaces"]["S"]["queueSize"], 0);
    assert_eq!(status_body["surfaces"]["S"]["lastCoilId"], Value::Null);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_uses_dynamic_clip_from_coil_state_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_u = root.join("Cap_S_U");
    let source_m = root.join("Cap_S_M");
    let source_d = root.join("Cap_S_D");
    let save_s = root.join("Save_S");
    write_dynamic_rejoin_area_join_config(
        &join_config_path,
        &source_u,
        &source_m,
        &source_d,
        &save_s,
    );
    write_area_camera_rgb_jpgs(&source_u, 42, 3, 20, 20);
    write_area_camera_rgb_jpgs(&source_m, 42, 3, 20, 80);
    write_area_camera_rgb_jpgs(&source_d, 42, 3, 20, 140);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_process_rows(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 42, "surface_key": "S"}),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("rejoin json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["queued"], json!(["S"]));
    assert_eq!(
        image::open(save_s.join("42").join("jpg").join("AREA.jpg"))
            .expect("dynamic area image")
            .dimensions(),
        (6, 38)
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_stacks_camera_positions_in_u_m_d_order_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_u = root.join("Cap_S_U");
    let source_m = root.join("Cap_S_M");
    let source_d = root.join("Cap_S_D");
    let save_s = root.join("Save_S");
    write_unordered_rejoin_area_join_config(
        &join_config_path,
        &source_u,
        &source_m,
        &source_d,
        &save_s,
    );
    write_area_camera_solid_jpgs(&source_u, 73, [240, 20, 20]);
    write_area_camera_solid_jpgs(&source_m, 73, [20, 240, 20]);
    write_area_camera_solid_jpgs(&source_d, 73, [20, 20, 240]);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 73, "surface_key": "S"}),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("rejoin json");
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["queued"], json!(["S"]));

    let area = image::open(save_s.join("73").join("jpg").join("AREA.jpg"))
        .expect("ordered area image")
        .to_rgb8();
    assert_eq!(area.dimensions(), (6, 18));
    let top = area.get_pixel(1, 1).0;
    let middle = area.get_pixel(1, 7).0;
    let bottom = area.get_pixel(1, 13).0;
    assert!(
        top[0] > top[1] && top[0] > top[2],
        "U camera should be the top red strip"
    );
    assert!(
        middle[1] > middle[0] && middle[1] > middle[2],
        "M camera should be the middle green strip"
    );
    assert!(
        bottom[2] > bottom[0] && bottom[2] > bottom[1],
        "D camera should be the bottom blue strip"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_trims_in_camera_overlap_like_python_hconcat_list() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    let source_u = root.join("Cap_S_U");
    let source_m = root.join("Cap_S_M");
    let source_d = root.join("Cap_S_D");
    let save_s = root.join("Save_S");
    write_rejoin_area_join_config(&join_config_path, &source_u, &source_m, &source_d, &save_s);
    write_area_camera_overlap_jpgs(&source_u, 76, [240, 20, 20]);
    write_area_camera_overlap_jpgs(&source_m, 76, [20, 240, 20]);
    write_area_camera_overlap_jpgs(&source_d, 76, [20, 20, 240]);
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 76, "surface_key": "S"}),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("rejoin json");
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["queued"], json!(["S"]));

    let area = image::open(save_s.join("76").join("jpg").join("AREA.jpg"))
        .expect("overlap-trimmed area image");
    assert_eq!(
        area.dimensions(),
        (52, 58),
        "Python hconcat_list keeps the first 40px image and only the 12px non-overlap tail from the second image for each U/M/D strip"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_rejoin_reports_missing_configured_surface_as_failed_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_rejoin_area_join_config(
        &join_config_path,
        &root.join("Cap_S_U"),
        &root.join("Cap_S_M"),
        &root.join("Cap_S_D"),
        &root.join("Save_S"),
    );
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let response = request_json_body(
        app.clone(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 73, "surface_key": "L"}),
    )
    .await;
    let status = response.status();
    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("rejoin json");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "queued");
    assert_eq!(body["queued"], json!([]));
    assert_eq!(body["failed"], json!(["L"]));

    let (status_status, status_body) = request_json(app, "GET", "/area/status").await;
    assert_eq!(status_status, StatusCode::OK);
    assert_eq!(status_body["joinQueueSize"], 0);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_status_uses_configured_surfaces_like_python() {
    let _settings_env_guard = lock_test_env();
    let root = unique_temp_dir();
    let join_config_path = root.join("area_join.json");
    write_rejoin_area_join_config(
        &join_config_path,
        &root.join("Cap_S_U"),
        &root.join("Cap_S_M"),
        &root.join("Cap_S_D"),
        &root.join("Save_S"),
    );
    let _join_config_guard = set_env_var_guard("RUST_API_AREA_JOIN_CONFIG", &join_config_path);
    let app = app_with_seed_data();

    let (status_status, status_body) = request_json(app.clone(), "GET", "/area/status").await;
    assert_eq!(status_status, StatusCode::OK);
    assert!(status_body["surfaces"].get("S").is_some());
    assert!(status_body["surfaces"].get("L").is_none());
    assert!(status_body["queueDepths"].get("S").is_some());
    assert!(status_body["queueDepths"].get("L").is_none());

    let scan_response = request_json_body(app, "POST", "/area/scan", json!({})).await;
    let scan_body: Value =
        serde_json::from_slice(&response_bytes(scan_response).await).expect("scan json");
    assert!(scan_body["surfaces"].get("S").is_some());
    assert!(scan_body["surfaces"].get("L").is_none());
    assert!(scan_body["queueDepths"].get("S").is_some());
    assert!(scan_body["queueDepths"].get("L").is_none());

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn alg_2d_area_clip_config_rejects_invalid_mode_like_python() {
    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/clip_config",
        json!({
            "surface_key": "S",
            "mode": "bad-mode",
            "fixed": 200
        }),
    )
    .await;
    let status = response.status();

    assert_eq!(status, StatusCode::BAD_REQUEST);

    let body: Value = serde_json::from_slice(&response_bytes(response).await).expect("json body");

    assert!(
        body["detail"]
            .as_str()
            .expect("detail")
            .contains("Invalid mode")
    );
}

#[tokio::test]
async fn classifier_image_crops_runtime_gray_image_when_cache_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 401, 40, 30);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/classifier_image/401/S/scratch/5/4/8/7",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("classifier crop image");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(image.dimensions(), (8, 7));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn defect_image_crops_runtime_named_source_image_for_qml_defect_cards() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 403, 40, 30);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/defect_image/S/403/GRAY/5/4/8/7",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("defect crop image");

    assert_eq!(image.dimensions(), (8, 7));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn defect_image_uses_python_defaults_for_nan_path_coordinates() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 404, 160, 130);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/defect_image/S/404/GRAY/NaN/NaN/NaN/NaN",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("default defect crop image");

    assert_eq!(image.dimensions(), (100, 100));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn defect_image_prefers_matching_detection_png_when_xml_box_contains_center() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 405, 40, 30);
    let detection_dir = root.join("405").join("detection").join("scratch");
    fs::create_dir_all(&detection_dir).expect("detection dir");
    fs::write(
        detection_dir.join("scratch.xml"),
        r#"
        <annotation>
            <object>
                <bndbox>
                    <xmin>10</xmin>
                    <ymin>20</ymin>
                    <xmax>30</xmax>
                    <ymax>40</ymax>
                </bndbox>
            </object>
        </annotation>
        "#,
    )
    .expect("detection xml");
    GrayImage::from_pixel(6, 5, Luma([180]))
        .save_with_format(detection_dir.join("scratch.png"), ImageFormat::Png)
        .expect("detection png");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/defect_image/S/405/GRAY/12/22/4/4",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");

    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("detection defect image");
    assert_eq!(image.dimensions(), (6, 5));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn classifier_image_prefers_production_cache_in_test_mode_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let cache_path = save_s
        .join("1753")
        .join("classifier")
        .join("scratch")
        .join("1753_0_0_7_6.png");
    fs::create_dir_all(cache_path.parent().expect("classifier parent")).expect("classifier dir");
    GrayImage::from_pixel(7, 6, Luma([180]))
        .save_with_format(&cache_path, ImageFormat::Png)
        .expect("classifier png");
    let testdata_dir = root.join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 3, 2);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        build_app(test_state(testdata_dir.clone()).with_data_config(config)),
        "GET",
        "/classifier_image/1753/S/scratch/0/0/20/20",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("classifier production png");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");
    assert_eq!(image.dimensions(), (7, 6));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn defect_image_prefers_production_detection_in_test_mode_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 1753, 40, 30);
    let detection_dir = root.join("1753").join("detection").join("scratch");
    fs::create_dir_all(&detection_dir).expect("detection dir");
    fs::write(
        detection_dir.join("scratch.xml"),
        r#"<annotation><object><bndbox><xmin>0</xmin><ymin>0</ymin><xmax>20</xmax><ymax>20</ymax></bndbox></object></annotation>"#,
    )
    .expect("detection xml");
    GrayImage::from_pixel(7, 6, Luma([180]))
        .save_with_format(detection_dir.join("scratch.png"), ImageFormat::Png)
        .expect("detection png");
    let testdata_dir = root.join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 5, 4);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        build_app(test_state(testdata_dir.clone()).with_data_config(config)),
        "GET",
        "/defect_image/S/1753/GRAY/1/1/2/2",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("defect production png");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");
    assert_eq!(image.dimensions(), (7, 6));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn clip_max_image_splits_runtime_gray_image_into_python_named_tiles() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 402, 1800, 1800);
    fs::create_dir_all(coil_dir.join("mask")).expect("clip mask dir");
    GrayImage::from_pixel(1800, 1800, Luma([255]))
        .save_with_format(coil_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write full clip mask");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let (status, body) =
        request_json(app_with_data_config(config), "GET", "/clipMaxImage/402/S").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body, Value::Null);

    let output_dir = coil_dir.join("clip_max");
    let mut output_files = fs::read_dir(&output_dir)
        .expect("clip output dir")
        .map(|entry| entry.expect("clip output entry").path())
        .collect::<Vec<_>>();
    output_files.sort();

    assert_eq!(output_files.len(), 100);
    let first_tile = output_dir.join("402_S_0_0_200_200.png");
    assert!(first_tile.exists());
    let image = image::open(first_tile).expect("first tile image");
    assert_eq!(image.dimensions(), (200, 200));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn area_route_generates_runtime_configured_rgba_png_from_depth_range() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("403");
    fs::create_dir_all(&coil_dir).expect("area coil dir");
    write_npy(
        coil_dir.join("3D.npy"),
        &arr2(&[[0.0, 20.0, 50.0], [30.0, 40.0, 60.0]]),
    )
    .expect("write area npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Area/S/403?valueFrom=15&valueTo=45&r=10&g=20&b=30",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("area png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");
    assert_eq!(image.dimensions(), (3, 2));
    assert_eq!(image.get_pixel(1, 0).0, [10, 20, 30, 255]);
    assert_eq!(image.get_pixel(0, 0).0, [0, 0, 0, 0]);
    assert_eq!(image.get_pixel(2, 1).0, [0, 0, 0, 0]);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn area_route_dynamic_generation_ignores_mask_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("408");
    fs::create_dir_all(coil_dir.join("mask")).expect("area mask dir");
    write_npy(coil_dir.join("3D.npy"), &arr2(&[[20.0, 30.0, 40.0]]))
        .expect("write masked area npy");
    let mut mask = GrayImage::from_pixel(3, 1, Luma([255]));
    mask.put_pixel(1, 0, Luma([0]));
    mask.save_with_format(coil_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write area mask");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Area/S/408?mask=true&valueFrom=15&valueTo=45&r=10&g=20&b=30",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("masked area png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(image.dimensions(), (3, 1));
    assert_eq!(
        image.get_pixel(1, 0).0,
        [10, 20, 30, 255],
        "Python Area dynamic generation fills by raw depth range and does not apply MASK.png filtering"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn area_route_returns_python_internal_error_when_depth_file_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    fs::create_dir_all(save_s.join("409")).expect("area coil dir without depth");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Area/S/409?valueFrom=15&valueTo=45&r=10&g=20&b=30",
    )
    .await;

    assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    assert_eq!(
        response_bytes(response).await.as_ref(),
        b"Internal Server Error"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn area_route_uses_testdata_depth_for_any_coil_id_in_test_mode_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);

    let production_dir = save_s.join("1754");
    fs::create_dir_all(&production_dir).expect("production area dir");
    write_npy(production_dir.join("3D.npy"), &arr2(&[[10.0, 40.0, 80.0]]))
        .expect("write production area npy");

    let testdata_dir = root.join("TestData").join("to").join("193113");
    let testdata_surface_dir = testdata_dir.join("S");
    fs::create_dir_all(&testdata_surface_dir).expect("testdata area dir");
    write_npy(testdata_surface_dir.join("3D.npy"), &arr2(&[[10.0, 40.0]]))
        .expect("write testdata area npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        build_app(test_state(testdata_dir.clone()).with_data_config(config)),
        "GET",
        "/coilData/Area/S/1754?valueFrom=20&valueTo=60&r=1&g=2&b=3",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("testdata area png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        image.dimensions(),
        (2, 1),
        "Python test mode maps arbitrary coil image/depth requests to TestData"
    );
    assert_eq!(image.get_pixel(0, 0).0, [0, 0, 0, 0]);
    assert_eq!(image.get_pixel(1, 0).0, [1, 2, 3, 255]);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn area_route_string_coil_id_failures_match_python_internal_error() {
    for uri in ["/coilData/Area/S/abc", "/coilData/Area/S/-1"] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(
            response.status(),
            StatusCode::INTERNAL_SERVER_ERROR,
            "{uri}"
        );
        assert_eq!(
            response_bytes(response).await.as_ref(),
            b"Internal Server Error"
        );
    }
}

#[tokio::test]
async fn error_route_generates_runtime_configured_rgba_png_from_depth_thresholds() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("404");
    fs::create_dir_all(&coil_dir).expect("error coil dir");
    write_npy(coil_dir.join("3D.npy"), &arr2(&[[1100.0, 3000.0, 5000.0]]))
        .expect("write error npy");

    let threshold = 1000.0 * 0.016229506582021713;
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        &format!("/coilData/Error/S/404?minValue={threshold}&maxValue={threshold}"),
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("error png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");
    assert_eq!(image.dimensions(), (3, 1));
    assert_eq!(image.get_pixel(0, 0).0, [0, 0, 255, 255]);
    assert_eq!(image.get_pixel(1, 0).0, [0, 0, 0, 0]);
    assert_eq!(image.get_pixel(2, 0).0, [255, 0, 0, 255]);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn error_route_downscales_depth_like_python_inter_area_before_thresholding() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("405");
    fs::create_dir_all(&coil_dir).expect("error area coil dir");
    write_npy(
        coil_dir.join("3D.npy"),
        &arr2(&[[1100.0, 5000.0], [1100.0, 1100.0]]),
    )
    .expect("write error area npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Error/S/405?scale=0.5&minValue=0&maxValue=0",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("error downscale png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(image.dimensions(), (1, 1));
    assert_eq!(
        image.get_pixel(0, 0).0,
        [255, 0, 0, 255],
        "Python cv2.INTER_AREA averages the 2x2 depth block before Error thresholding, making it exceed the median"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn error_route_force_cache_returns_matching_cached_error_image_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("406");
    fs::create_dir_all(coil_dir.join("png")).expect("error cache png dir");
    let mut cached = image::RgbaImage::from_pixel(2, 1, image::Rgba([0, 0, 0, 0]));
    cached.put_pixel(0, 0, image::Rgba([9, 8, 7, 255]));
    cached.put_pixel(1, 0, image::Rgba([6, 5, 4, 255]));
    cached
        .save_with_format(coil_dir.join("png").join("Error.png"), ImageFormat::Png)
        .expect("write cached error png");
    fs::write(
        coil_dir.join("png").join("Error.json"),
        r#"{"threshold_down":12.5,"threshold_up":34.5}"#,
    )
    .expect("write error cache metadata");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Error/S/406?force_cache=true&minValue=12.5&maxValue=34.5",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("cached force-cache error png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/png");
    assert_eq!(image.dimensions(), (2, 1));
    assert_eq!(image.get_pixel(0, 0).0, [9, 8, 7, 255]);
    assert_eq!(image.get_pixel(1, 0).0, [6, 5, 4, 255]);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn error_route_dynamic_generation_ignores_mask_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("407");
    fs::create_dir_all(coil_dir.join("mask")).expect("error mask dir");
    write_npy(coil_dir.join("3D.npy"), &arr2(&[[1100.0, 1100.0, 5000.0]]))
        .expect("write masked error npy");
    let mut mask = GrayImage::from_pixel(3, 1, Luma([255]));
    mask.put_pixel(2, 0, Luma([0]));
    mask.save_with_format(coil_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write error mask");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Error/S/407?mask=true&minValue=0&maxValue=0",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("masked error png")
        .to_rgba8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(image.dimensions(), (3, 1));
    assert_eq!(
        image.get_pixel(2, 0).0,
        [255, 0, 0, 255],
        "Python Error dynamic generation thresholds raw 3D data and does not apply MASK.png filtering"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn error_route_invalid_scale_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/coilData/Error/S/193113?scale=abc",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "float_parsing",
                    "loc": ["query", "scale"],
                    "msg": "Input should be a valid number, unable to parse string as a number",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn render_route_generates_runtime_configured_jpeg_from_depth_when_cache_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_dynamic_render_coil(&save_s, 324);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/324?scale=0.5&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated runtime render jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "JET");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(image.width(), 2);
    assert_eq!(image.height(), 1);

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_downscaled_size_uses_python_int_truncation() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("332");
    fs::create_dir_all(&coil_dir).expect("odd render coil dir");
    let array = ndarray::Array2::<f64>::from_shape_fn((3, 3), |(y, x)| (x + y * 3) as f64);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write odd render npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/332?scale=0.5&grayscale=true&mask=false&minValue=0&maxValue=8",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated odd-size render jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        image.dimensions(),
        (1, 1),
        "Python uses int(width * scale), int(height * scale) rather than rounding scaled dimensions"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_keeps_original_size_for_scale_at_or_above_python_resize_threshold() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_dynamic_render_coil(&save_s, 326);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/326?scale=2&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated runtime render jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        image.dimensions(),
        (4, 2),
        "Python keeps the original render size unless scale < 0.99"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_downscales_depth_like_python_cv2_resize() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_dynamic_render_coil(&save_s, 327);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/327?scale=0.5&grayscale=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated downscaled grayscale render")
        .to_rgb8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(image.dimensions(), (2, 1));
    for (x, expected) in [(0, 90_u8), (1, 164_u8)] {
        let pixel = image.get_pixel(x, 0).0;
        for channel in pixel {
            assert!(
                channel.abs_diff(expected) <= 1,
                "Python cv2.resize + JPEG quality 90 decodes pixel {x} near {expected}, got {pixel:?}"
            );
        }
    }

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_thumbnail_generates_python_sized_dynamic_image_when_cache_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("328");
    fs::create_dir_all(&coil_dir).expect("thumbnail render coil dir");
    let array = ndarray::Array2::<f64>::from_shape_fn((512, 2048), |(y, x)| ((x + y) % 351) as f64);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write thumbnail render npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/328?thumbnail=true&grayscale=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated dynamic thumbnail render")
        .to_rgb8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(
        image.dimensions(),
        (1024, 256),
        "Python thumbnail generation scales the longest side to 1024 when no cached preview exists"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_thumbnail_writes_falsecolor_cache_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("335");
    fs::create_dir_all(&coil_dir).expect("thumbnail cache coil dir");
    let array = ndarray::Array2::<f64>::from_shape_fn((512, 2048), |(y, x)| ((x + y) % 351) as f64);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write thumbnail cache npy");
    let cache_path = coil_dir
        .join("cache")
        .join("falsecolor")
        .join("gray")
        .join("thumbnail_1024.jpg");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/335?thumbnail=true&grayscale=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(headers["x-from-cache"], "false");
    assert!(
        cache_path.exists(),
        "Python FalseColorCache writes generated thumbnails to cache/falsecolor/gray/thumbnail_1024.jpg"
    );
    assert_eq!(
        fs::read(&cache_path).expect("written thumbnail cache"),
        bytes
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_thumbnail_does_not_use_full_jpg_when_preview_cache_is_missing() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("329");
    fs::create_dir_all(coil_dir.join("jpg")).expect("thumbnail full jpg dir");
    let array = ndarray::Array2::<f64>::from_shape_fn((512, 2048), |(y, x)| ((x + y) % 351) as f64);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write thumbnail render npy");
    GrayImage::from_pixel(2048, 512, Luma([210]))
        .save_with_format(coil_dir.join("jpg").join("GRAY.jpg"), ImageFormat::Jpeg)
        .expect("write full gray jpg");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/329?thumbnail=true&grayscale=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated dynamic thumbnail render")
        .to_rgb8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(
        headers["x-from-cache"], "false",
        "Python thumbnail rendering does not reuse full jpg/GRAY.jpg as a preview-cache hit"
    );
    assert_eq!(
        image.dimensions(),
        (1024, 256),
        "thumbnail=true should generate a 1024-long-side image when preview cache is absent"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_thumbnail_downscales_depth_like_python_inter_area() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("330");
    fs::create_dir_all(&coil_dir).expect("thumbnail area coil dir");
    let array =
        ndarray::Array2::<f64>::from_shape_fn(
            (1707, 1707),
            |(_, x)| {
                if x % 3 == 0 { 350.0 } else { 0.0 }
            },
        );
    write_npy(coil_dir.join("3D.npy"), &array).expect("write thumbnail area npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/330?thumbnail=true&grayscale=true&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated inter-area thumbnail render")
        .to_rgb8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(image.dimensions(), (1024, 1024));
    let pixel = image.get_pixel(1, 0).0;
    for channel in pixel {
        assert!(
            channel.abs_diff(51) <= 12,
            "Python cv2.INTER_AREA thumbnail decodes pixel 1 near 51, got {pixel:?}"
        );
    }

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_grayscale_thumbnail_with_mask_falls_back_to_full_render_like_python() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("331");
    fs::create_dir_all(coil_dir.join("mask")).expect("thumbnail mask dir");
    let array = ndarray::Array2::<f64>::from_elem((1707, 1707), 350.0);
    write_npy(coil_dir.join("3D.npy"), &array).expect("write thumbnail masked npy");
    let mut mask = GrayImage::from_pixel(1707, 1707, Luma([0]));
    for x in (0..1707).step_by(3) {
        for y in 0..1707 {
            mask.put_pixel(x, y, Luma([255]));
        }
    }
    mask.save_with_format(coil_dir.join("mask").join("MASK.png"), ImageFormat::Png)
        .expect("write thumbnail mask");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/331?thumbnail=true&grayscale=true&mask=true&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated grayscale fallback render")
        .to_rgb8();

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(
        image.dimensions(),
        (1707, 1707),
        "Python grayscale thumbnail with mask=true falls back to full render when falsecolor cache is missing"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn render_route_normalizes_depth_with_python_uint8_truncation() {
    let root = unique_temp_dir();
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let config_path = root.join("Server3D.json");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = save_s.join("325");
    fs::create_dir_all(&coil_dir).expect("runtime render coil dir");
    write_npy(coil_dir.join("3D.npy"), &arr2(&[[5.0]])).expect("write midpoint render npy");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_response(
        app_with_data_config(config),
        "GET",
        "/coilData/Render/S/325?grayscale=true&mask=false&minValue=0&maxValue=10",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes)
        .expect("generated grayscale midpoint jpeg")
        .to_rgb8();
    let pixel = image.get_pixel(0, 0).0;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(
        pixel,
        [127, 127, 127],
        "Python casts normalized float values to uint8 by truncating rather than rounding"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn coil_info_returns_testdata_dimensions_and_scale_fields() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilInfo/193113/S",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["coilId"], "193113");
    assert_eq!(body["surface"], "S");
    assert_eq!(body["height"], 12);
    assert_eq!(body["width"], 34);
    assert_eq!(body["scan3dCoordinateScaleX"], 0.33693358302116394);
    assert_eq!(body["scan3dCoordinateScaleZ"], 0.016229506582021713);
    assert_eq!(body["scan3dCoordinateOffsetZ"], 0);
    assert_eq!(body["median_3d"], 0.0);
    assert_eq!(body["median_3d_mm"], 0.0);
    assert_eq!(body["colorFromValue_mm"], -30);
    assert_eq!(body["colorToValue_mm"], 30);
    assert_eq!(
        body["circleConfig"]["inner_circle"]["circlex"],
        json!([17, 6])
    );

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn coil_info_testdata_falls_back_when_coil_state_lookup_times_out() {
    let _env_lock = lock_test_env();
    let _timeout_guard = set_env_var_guard("RUST_API_COIL_INFO_DB_TIMEOUT_MS", "20");
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);
    let repository = InMemoryCoilRepository::new().with_coil_state_delay(Duration::from_secs(5));
    let app = build_app(
        ApiState::new(Arc::new(repository)).with_test_mode(TestModeConfig {
            enabled: true,
            coil_id: 193113,
            project_root: testdata_dir
                .parent()
                .and_then(|path| path.parent())
                .and_then(|path| path.parent())
                .expect("project root")
                .to_path_buf(),
            data_dir: testdata_dir.clone(),
        }),
    );

    let started_at = Instant::now();
    let (status, body) = tokio::time::timeout(
        Duration::from_millis(250),
        request_json(app, "GET", "/coilInfo/193113/S"),
    )
    .await
    .expect("test-mode coilInfo should not wait for a slow database lookup");
    assert!(
        started_at.elapsed() < Duration::from_millis(500),
        "test-mode coilInfo should return from TestData before the slow database lookup finishes"
    );

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["coilId"], "193113");
    assert_eq!(body["surface"], "S");
    assert_eq!(body["height"], 12);
    assert_eq!(body["width"], 34);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_data_and_point_return_python_compatible_testdata_shape() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);

    let (line_status, line_body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/heightData/S/193113?x1=1&y1=2&x2=5&y2=2",
    )
    .await;

    assert_eq!(line_status, StatusCode::OK);
    let segments = line_body.as_array().expect("segments");
    assert_eq!(segments.len(), 1);
    assert_eq!(segments[0]["pointL"], json!([1, 2]));
    assert_eq!(segments[0]["pointR"], json!([5, 2]));
    assert_eq!(segments[0]["points"][0], json!([1, 2, 1003]));
    assert_eq!(segments[0]["points"][4], json!([5, 2, 1007]));

    let (point_status, point_body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/heightPoint/S/193113?x=5&y=2",
    )
    .await;
    assert_eq!(point_status, StatusCode::OK);
    assert_eq!(point_body, json!(1007));

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_point_string_coil_id_uses_testdata_fallback_like_python() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);

    for coil_id in ["abc", "-1"] {
        let (status, body) = request_json(
            build_app(test_state(testdata_dir.clone())),
            "GET",
            &format!("/coilData/heightPoint/S/{coil_id}"),
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        assert_eq!(body, json!(1000));
    }

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_data_string_coil_id_uses_testdata_fallback_like_python() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_testdata_surface(&testdata_dir, "S", 12, 34);

    for coil_id in ["abc", "-1"] {
        let (status, body) = request_json(
            build_app(test_state(testdata_dir.clone())),
            "GET",
            &format!("/coilData/heightData/S/{coil_id}?x1=1&y1=2&x2=5&y2=2"),
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let segments = body.as_array().expect("segments");
        assert_eq!(segments.len(), 1);
        assert_eq!(segments[0]["pointL"], json!([1, 2]));
        assert_eq!(segments[0]["pointR"], json!([5, 2]));
        assert_eq!(segments[0]["points"][0], json!([1, 2, 1003]));
        assert_eq!(segments[0]["points"][4], json!([5, 2, 1007]));
    }

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn coil_info_reads_shape_and_median_from_real_npy_depth_file() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npy_surface(&testdata_dir, "S");

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilInfo/193113/S",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["height"], 2);
    assert_eq!(body["width"], 3);
    assert_eq!(body["median_3d"], 30.0);
    assert_eq!(body["median_3d_mm"], 30.0 * 0.016229506582021713);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_point_reads_real_npy_and_npz_depth_values() {
    let npy_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npy_surface(&npy_dir, "S");
    let npz_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npz_surface(&npz_dir, "S");

    let (npy_status, npy_body) = request_json(
        build_app(test_state(npy_dir.clone())),
        "GET",
        "/coilData/heightPoint/S/193113?x=2&y=1",
    )
    .await;
    let (npz_status, npz_body) = request_json(
        build_app(test_state(npz_dir.clone())),
        "GET",
        "/coilData/heightPoint/S/193113?x=2&y=1",
    )
    .await;

    assert_eq!(npy_status, StatusCode::OK);
    assert_eq!(npy_body, json!(2600));
    assert_eq!(npz_status, StatusCode::OK);
    assert_eq!(npz_body, json!(3050));

    for testdata_dir in [npy_dir, npz_dir] {
        let _ = fs::remove_dir_all(
            testdata_dir
                .parent()
                .and_then(|path| path.parent())
                .and_then(|path| path.parent())
                .expect("cleanup root"),
        );
    }
}

#[tokio::test]
async fn height_point_invalid_x_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/coilData/heightPoint/S/193113?x=abc&y=650",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "x"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn height_data_invalid_x1_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_process_rows(),
        "GET",
        "/coilData/heightData/S/193113?x1=abc&y1=0&x2=10&y2=0",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "x1"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn height_data_samples_real_depth_line_values() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_long_line_npy_surface(&testdata_dir, "S");

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/heightData/S/193113?x1=0&y1=0&x2=104&y2=0",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let segments = body.as_array().expect("segments");
    assert_eq!(segments.len(), 1);
    assert_eq!(segments[0]["pointL"], json!([0, 0]));
    assert_eq!(segments[0]["pointR"], json!([104, 0]));
    assert_eq!(segments[0]["points"].as_array().expect("points").len(), 105);
    assert_eq!(segments[0]["points"][0], json!([0, 0, 500]));
    assert_eq!(segments[0]["points"][104], json!([104, 0, 604]));

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_data_extends_to_image_edges_and_splits_by_mask_like_python() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_masked_edge_line_npy_surface(&testdata_dir, "S");

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/heightData/S/193113?x1=100&y1=0&x2=110&y2=0",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let segments = body.as_array().expect("segments");
    assert_eq!(segments.len(), 2);
    assert_eq!(segments[0]["pointL"], json!([0, 0]));
    assert_eq!(segments[0]["pointR"], json!([104, 0]));
    assert_eq!(segments[0]["points"].as_array().expect("points").len(), 105);
    assert_eq!(segments[0]["points"][0], json!([0, 0, 500]));
    assert_eq!(segments[0]["points"][104], json!([104, 0, 604]));
    assert_eq!(segments[1]["pointL"], json!([125, 0]));
    assert_eq!(segments[1]["pointR"], json!([249, 0]));
    assert_eq!(segments[1]["points"].as_array().expect("points").len(), 125);
    assert_eq!(segments[1]["points"][0], json!([125, 0, 625]));
    assert_eq!(segments[1]["points"][124], json!([249, 0, 749]));

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_data_diagonal_line_splits_by_mask_like_python() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_masked_diagonal_line_npy_surface(&testdata_dir, "S");

    let (status, body) = request_json(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/heightData/S/193113?x1=30&y1=20&x2=130&y2=70",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let segments = body.as_array().expect("segments");
    assert_eq!(segments.len(), 2);
    assert_eq!(segments[0]["pointL"], json!([230, 119]));
    assert_eq!(segments[0]["pointR"], json!([130, 69]));
    assert_eq!(segments[0]["points"].as_array().expect("points").len(), 101);
    assert_eq!(segments[0]["points"][0], json!([230, 119, 3419]));
    assert_eq!(segments[0]["points"][100], json!([130, 69, 2369]));
    assert_eq!(segments[1]["pointL"], json!([109, 59]));
    assert_eq!(segments[1]["pointR"], json!([0, 5]));
    assert_eq!(segments[1]["points"].as_array().expect("points").len(), 110);
    assert_eq!(segments[1]["points"][0], json!([109, 59, 2149]));
    assert_eq!(segments[1]["points"][109], json!([0, 5, 1005]));

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn render_route_serves_testdata_jet_image_by_default() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_render_testdata_surface(&testdata_dir, "S");

    let response = request_response(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/Render/S/193113",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "JET");
    assert_eq!(headers["x-from-cache"], "false");
    assert_ne!(bytes.as_ref(), b"\xff\xd8jet-full\xff\xd9");

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn render_route_serves_grayscale_thumbnail_when_requested() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_render_testdata_surface(&testdata_dir, "S");
    write_runtime_named_gray_image(
        &testdata_dir.join("S"),
        "cache/falsecolor/gray",
        "thumbnail_1024",
        1024,
        256,
    );

    let response = request_response(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/Render/S/193113?grayscale=true&thumbnail=true&minValue=10&maxValue=20",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("testdata falsecolor gray thumbnail");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "true");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(headers["x-from-cache"], "true");
    assert_eq!(
        image.dimensions(),
        (1024, 256),
        "Python Render thumbnail reads cache/falsecolor/gray/thumbnail_1024.jpg instead of preview/GRAY.jpg"
    );

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn string_coil_id_image_routes_use_testdata_fallback_like_python() {
    let render_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_render_testdata_surface(&render_dir, "S");
    let dynamic_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_dynamic_render_surface(&dynamic_dir, "S");

    for coil_id in ["abc", "-1"] {
        let render_response = request_response(
            build_app(test_state(render_dir.clone())),
            "GET",
            &format!("/coilData/Render/S/{coil_id}"),
        )
        .await;
        let render_status = render_response.status();
        let render_headers = render_response.headers().clone();
        let render_bytes = response_bytes(render_response).await;
        assert_eq!(render_status, StatusCode::OK);
        assert_eq!(render_headers["content-type"], "image/jpeg");
        assert_eq!(render_headers["x-from-cache"], "false");
        assert_ne!(render_bytes.as_ref(), b"\xff\xd8jet-full\xff\xd9");

        let preview_response = request_response(
            build_app(test_state(render_dir.clone())),
            "GET",
            &format!("/image/preview/S/{coil_id}/GRAY"),
        )
        .await;
        let preview_status = preview_response.status();
        let preview_headers = preview_response.headers().clone();
        let preview_bytes = response_bytes(preview_response).await;
        assert_eq!(preview_status, StatusCode::OK);
        assert_eq!(preview_headers["content-type"], "image/jpeg");
        assert_eq!(preview_bytes.as_ref(), b"\xff\xd8gray-preview\xff\xd9");

        let source_response = request_response(
            build_app(test_state(render_dir.clone())),
            "GET",
            &format!("/image/source/S/{coil_id}/GRAY"),
        )
        .await;
        let source_status = source_response.status();
        let source_headers = source_response.headers().clone();
        let source_bytes = response_bytes(source_response).await;
        assert_eq!(source_status, StatusCode::OK);
        assert_eq!(source_headers["content-type"], "image/jpeg");
        assert_eq!(source_bytes.as_ref(), b"\xff\xd8gray-full\xff\xd9");

        let masked_source_response = request_response(
            build_app(test_state(render_dir.clone())),
            "GET",
            &format!("/image/source/S/{coil_id}/GRAY?mask=true"),
        )
        .await;
        let masked_source_status = masked_source_response.status();
        let masked_source_headers = masked_source_response.headers().clone();
        let masked_source_bytes = response_bytes(masked_source_response).await;
        assert_eq!(masked_source_status, StatusCode::OK);
        assert_eq!(masked_source_headers["content-type"], "image/jpeg");
        assert_eq!(
            masked_source_bytes.as_ref(),
            b"\xff\xd8\xff\xdb\x00\x43\x00\xff\xd9",
            "mask=true returns placeholder when testdata lacks mask source"
        );

        let area_response = request_response(
            build_app(test_state(render_dir.clone())),
            "GET",
            &format!("/image/area/S/{coil_id}/AREA?count=0"),
        )
        .await;
        let area_status = area_response.status();
        let area_headers = area_response.headers().clone();
        let area_bytes = response_bytes(area_response).await;
        assert_eq!(area_status, StatusCode::OK);
        assert_eq!(area_headers["content-type"], "image/jpeg");
        assert!(area_bytes.starts_with(&[0xff, 0xd8]));
        assert!(area_bytes.ends_with(&[0xff, 0xd9]));

        let error_response = request_response(
            build_app(test_state(dynamic_dir.clone())),
            "GET",
            &format!("/coilData/Error/S/{coil_id}?minValue=10&maxValue=250"),
        )
        .await;
        assert_eq!(error_response.status(), StatusCode::OK);
        assert_eq!(error_response.headers()["content-type"], "image/png");
    }

    let _ = fs::remove_dir_all(
        render_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("render cleanup root"),
    );
    let _ = fs::remove_dir_all(
        dynamic_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("dynamic cleanup root"),
    );
}

#[tokio::test]
async fn render_route_invalid_scale_returns_fastapi_query_validation_error() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/coilData/Render/S/193113?scale=abc",
    )
    .await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    assert_eq!(
        response_json(response).await,
        json!({
            "detail": [
                {
                    "type": "float_parsing",
                    "loc": ["query", "scale"],
                    "msg": "Input should be a valid number, unable to parse string as a number",
                    "input": "abc"
                }
            ]
        })
    );
}

#[tokio::test]
async fn render_route_generates_grayscale_jpeg_from_depth_when_cache_is_missing() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_dynamic_render_surface(&testdata_dir, "S");

    let response = request_response(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/Render/S/193113?grayscale=true&mask=true&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated grayscale jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "GRAY");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(image.width(), 4);
    assert_eq!(image.height(), 2);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn render_route_generates_scaled_jet_jpeg_from_depth_when_cache_is_missing() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_dynamic_render_surface(&testdata_dir, "S");

    let response = request_response(
        build_app(test_state(testdata_dir.clone())),
        "GET",
        "/coilData/Render/S/193113?scale=0.5&mask=false&minValue=0&maxValue=350",
    )
    .await;
    let status = response.status();
    let headers = response.headers().clone();
    let bytes = response_bytes(response).await;
    let image = image::load_from_memory(&bytes).expect("generated jet jpeg");

    assert_eq!(status, StatusCode::OK);
    assert_eq!(headers["content-type"], "image/jpeg");
    assert_eq!(headers["x-thumbnail"], "false");
    assert_eq!(headers["x-colormap"], "JET");
    assert_eq!(headers["x-from-cache"], "false");
    assert_eq!(image.width(), 2);
    assert_eq!(image.height(), 1);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_point_websocket_returns_python_compatible_value_response() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npy_surface(&testdata_dir, "S");
    let ws_url = spawn_test_server(build_app(test_state(testdata_dir.clone()))).await;

    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text(
            json!({
                "id": 77,
                "surface_key": "S",
                "coil_id": "193113",
                "x": 2,
                "y": 1
            })
            .to_string()
            .into(),
        ))
        .await
        .expect("send request");

    let message = socket
        .next()
        .await
        .expect("websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");

    assert_eq!(body["id"], 77);
    assert_eq!(body["surface_key"], "S");
    assert_eq!(body["coil_id"], "193113");
    assert_eq!(body["x"], 2);
    assert_eq!(body["y"], 1);
    assert_eq!(body["value"], 2600);

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_point_websocket_reports_missing_required_fields() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npy_surface(&testdata_dir, "S");
    let ws_url = spawn_test_server(build_app(test_state(testdata_dir.clone()))).await;

    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text(
            json!({"id": 78, "x": 2, "y": 1}).to_string().into(),
        ))
        .await
        .expect("send request");

    let message = socket
        .next()
        .await
        .expect("websocket message")
        .expect("message ok");
    let body: Value = serde_json::from_str(message.to_text().expect("text message")).expect("json");

    assert_eq!(body["id"], 78);
    assert_eq!(body["error"], "surface_key and coil_id are required");

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn height_point_websocket_invalid_json_message_closes_connection() {
    let testdata_dir = unique_temp_dir().join("TestData").join("to").join("193113");
    write_real_npy_surface(&testdata_dir, "S");
    let ws_url = spawn_test_server(build_app(test_state(testdata_dir.clone()))).await;

    let (mut socket, _) = connect_async(&ws_url).await.expect("connect websocket");
    socket
        .send(Message::Text("invalid-json-payload".to_string().into()))
        .await
        .expect("send invalid payload");

    let terminal = tokio::time::timeout(Duration::from_millis(800), socket.next())
        .await
        .expect("invalid websocket payload should terminate the connection");
    assert!(
        matches!(terminal, None | Some(Ok(Message::Close(_)))),
        "connection should close after invalid json message"
    );

    let _ = fs::remove_dir_all(
        testdata_dir
            .parent()
            .and_then(|path| path.parent())
            .and_then(|path| path.parent())
            .expect("cleanup root"),
    );
}

#[tokio::test]
async fn defects_endpoint_returns_python_field_names() {
    let (status, body) = request_json(app_with_seed_data(), "GET", "/search/defects/42/S").await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().expect("array").len(), 1);
    assert_eq!(body[0]["Id"], 7);
    assert_eq!(body[0]["secondaryCoilId"], 42);
    assert_eq!(body[0]["surface"], "S");
    assert_eq!(body[0]["defectName"], "压痕");
    assert_eq!(body[0]["defectX"], 11);
    assert_eq!(body[0]["defectData"], json!({"source":"test"}));
}

#[tokio::test]
async fn auto_defect_search_routes_use_python_datetime_float_and_empty_data_shape() {
    let app = app_with_detail_defect_serialization_data();

    for path in [
        "/search/defects/42/S",
        "/search/getDefectAll/42/42",
        "/search/defects_all/42/S",
    ] {
        let (status, body) = request_json(app.clone(), "GET", path).await;

        assert_eq!(status, StatusCode::OK, "{path}");
        let rows = body.as_array().expect("array");
        assert_eq!(rows.len(), 1, "{path}");
        assert_eq!(rows[0]["defectTime"], "2026-06-27T12:35:12", "{path}");
        assert_eq!(rows[0]["defectSource"], 0.913837, "{path}");
        assert_eq!(rows[0]["defectData"], "", "{path}");
    }
}

#[tokio::test]
async fn defect_all_range_endpoint_returns_flat_rows_sorted_like_python() {
    let (status, body) = request_json(
        app_with_defect_query_rows(),
        "GET",
        "/search/getDefectAll/41/42",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("array");
    assert_eq!(rows.len(), 3);
    assert_eq!(rows[0]["secondaryCoilId"], 41);
    assert_eq!(rows[0]["Id"], 9);
    assert_eq!(rows[1]["secondaryCoilId"], 42);
    assert_eq!(rows[1]["Id"], 7);
    assert_eq!(rows[2]["secondaryCoilId"], 42);
    assert_eq!(rows[2]["Id"], 8);
    assert_eq!(rows[1]["defectName"], "压痕");
    assert_eq!(rows[1]["defectData"], json!({"source":"auto"}));
}

#[tokio::test]
async fn manual_defects_endpoint_returns_manual_rows_for_surface() {
    let (status, body) =
        request_json(app_with_defect_query_rows(), "GET", "/manual_defects/42/S").await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("array");
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["Id"], 51);
    assert_eq!(rows[0]["secondaryCoilId"], 42);
    assert_eq!(rows[0]["surface"], "S");
    assert_eq!(rows[0]["defectName"], "手动压痕");
    assert_eq!(rows[0]["defectTime"], "2026-06-27T12:40:00");
    assert_eq!(rows[0]["defectData"], json!({"manual":true}));
    assert_eq!(rows[0]["remark"], "人工复核");
    assert_eq!(rows[0]["annotator"], "系统用户");
    assert_eq!(rows[0]["type"], "manual");

    let (status, body) =
        request_json(app_with_defect_query_rows(), "GET", "/manual_defects/42/X").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body.as_array().expect("array").len(), 0);
}

#[tokio::test]
async fn defects_all_endpoint_returns_auto_then_manual_rows_for_surface() {
    let (status, body) = request_json(
        app_with_defect_query_rows(),
        "GET",
        "/search/defects_all/42/S",
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    let rows = body.as_array().expect("array");
    assert_eq!(rows.len(), 3);
    assert_eq!(rows[0]["Id"], 7);
    assert_eq!(rows[0]["type"], "auto");
    assert_eq!(rows[1]["Id"], 8);
    assert_eq!(rows[1]["type"], "auto");
    assert_eq!(rows[2]["Id"], 51);
    assert_eq!(rows[2]["type"], "manual");
    assert_eq!(rows[2]["remark"], "人工复核");
}

#[tokio::test]
async fn add_manual_defect_endpoint_inserts_default_python_fields_and_can_be_read() {
    let app = app_with_defect_query_rows();
    let response = request_json_body(
        app.clone(),
        "POST",
        "/manual_defect/add",
        json!({
            "secondaryCoilId": 42,
            "surface": "S",
            "defectName": "新增标注",
            "defectX": 401,
            "defectY": 402,
            "defectW": 43,
            "defectH": 44,
            "remark": "新备注",
            "annotator": "测试员"
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert!(body["Id"].as_i64().expect("id") > 52);
    assert_eq!(body["secondaryCoilId"], 42);
    assert_eq!(body["surface"], "S");
    assert_eq!(body["defectClass"], 0);
    assert_eq!(body["defectName"], "新增标注");
    assert_eq!(body["defectStatus"], 1);
    assert_eq!(body["defectSource"], 0.0);
    assert_eq!(body["remark"], "新备注");
    assert_eq!(body["annotator"], "测试员");

    let (_, read_body) = request_json(app, "GET", "/manual_defects/42/S").await;
    let rows = read_body.as_array().expect("array");
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[1]["Id"], body["Id"]);
    assert_eq!(rows[1]["defectName"], "新增标注");
    assert_eq!(rows[1]["type"], "manual");
}

#[tokio::test]
async fn update_manual_defect_endpoint_updates_existing_row_and_reports_missing_like_python() {
    let app = app_with_defect_query_rows();
    let response = request_json_body(
        app.clone(),
        "PUT",
        "/manual_defect/update/51",
        json!({
            "defectName": "更新标注",
            "defectStatus": 0,
            "defectX": 501,
            "defectY": 502,
            "defectW": 53,
            "defectH": 54,
            "remark": "已更新",
            "annotator": "复核员",
            "defectData": {"reviewed": true}
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["Id"], 51);
    assert_eq!(body["defectName"], "更新标注");
    assert_eq!(body["defectStatus"], 0);
    assert_eq!(body["defectX"], 501);
    assert_eq!(body["defectData"], json!({"reviewed": true}));
    assert_eq!(body["remark"], "已更新");
    assert_eq!(body["annotator"], "复核员");

    let (_, read_body) = request_json(app.clone(), "GET", "/manual_defects/42/S").await;
    assert_eq!(read_body[0]["Id"], 51);
    assert_eq!(read_body[0]["defectName"], "更新标注");

    let missing_response = request_json_body(
        app,
        "PUT",
        "/manual_defect/update/999",
        json!({"defectName": "不存在"}),
    )
    .await;
    assert_eq!(missing_response.status(), StatusCode::OK);
    let missing_body = response_json(missing_response).await;
    assert_eq!(missing_body["success"], false);
    assert_eq!(missing_body["error"], "缺陷不存在");
}

#[tokio::test]
async fn delete_manual_defect_endpoint_removes_row_and_reports_missing_like_python() {
    let app = app_with_defect_query_rows();
    let response = request_response(app.clone(), "DELETE", "/manual_defect/delete/51").await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["success"], true);
    assert_eq!(body["message"], "删除成功");

    let (_, read_body) = request_json(app.clone(), "GET", "/manual_defects/42/S").await;
    assert_eq!(read_body.as_array().expect("array").len(), 0);

    let missing_response = request_response(app, "DELETE", "/manual_defect/delete/51").await;
    assert_eq!(missing_response.status(), StatusCode::OK);
    let missing_body = response_json(missing_response).await;
    assert_eq!(missing_body["success"], false);
    assert_eq!(missing_body["error"], "缺陷不存在");
}

#[tokio::test]
async fn manual_defect_mutation_rejects_non_python_int_converter_paths_like_python() {
    for uri in ["/manual_defect/update/abc", "/manual_defect/update/-1"] {
        let response = request_json_body(
            app_with_defect_query_rows(),
            "PUT",
            uri,
            json!({"defectName": "无效路径"}),
        )
        .await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }

    for uri in ["/manual_defect/delete/abc", "/manual_defect/delete/-1"] {
        let response = request_response(app_with_defect_query_rows(), "DELETE", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn add_manual_defect_syncs_crop_image_xml_and_defect_data_when_source_gray_exists() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 220, 180);
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_defect_query_rows_and_data_config(config);

    let response = request_json_body(
        app.clone(),
        "POST",
        "/manual_defect/add",
        json!({
            "secondaryCoilId": 42,
            "surface": "S",
            "defectName": "边裂",
            "defectX": 20,
            "defectY": 30,
            "defectW": 40,
            "defectH": 50,
            "remark": "资产同步",
            "annotator": "测试员"
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    let defect_data = body["defectData"].as_object().expect("defect data");
    assert_eq!(defect_data["manualCenter"], json!([40.0, 55.0]));
    assert_eq!(defect_data["manualCropBox"], json!([-24, -9, 104, 119]));

    let image_path = PathBuf::from(defect_data["manualImagePath"].as_str().expect("image path"));
    let xml_path = PathBuf::from(defect_data["manualXmlPath"].as_str().expect("xml path"));
    assert!(image_path.exists(), "manual crop image should exist");
    assert!(xml_path.exists(), "manual xml should exist");
    assert!(image_path.starts_with(save_s.join("42").join("manual_defect").join("边裂")));
    assert_eq!(
        image::open(&image_path).expect("crop image").dimensions(),
        (128, 128)
    );

    let xml = fs::read_to_string(&xml_path).expect("xml text");
    assert!(xml.contains("<name>边裂</name>"));
    assert!(xml.contains("<xmin>44</xmin>"));
    assert!(xml.contains("<ymin>39</ymin>"));
    assert!(xml.contains("<xmax>84</xmax>"));
    assert!(xml.contains("<ymax>89</ymax>"));

    let (_, read_body) = request_json(app, "GET", "/manual_defects/42/S").await;
    let rows = read_body.as_array().expect("array");
    assert_eq!(
        rows[1]["defectData"]["manualImagePath"],
        json!(image_path.to_string_lossy())
    );
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn update_manual_defect_refreshes_manual_assets_for_new_shape() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 260, 220);
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_defect_query_rows_and_data_config(config);

    let response = request_json_body(
        app.clone(),
        "PUT",
        "/manual_defect/update/51",
        json!({
            "defectName": "更新边裂",
            "defectX": 60,
            "defectY": 70,
            "defectW": 80,
            "defectH": 20,
            "remark": "刷新资产"
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    let defect_data = body["defectData"].as_object().expect("defect data");
    assert_eq!(defect_data["manualCenter"], json!([100.0, 80.0]));
    assert_eq!(defect_data["manualCropBox"], json!([36, 16, 164, 144]));
    let image_path = PathBuf::from(defect_data["manualImagePath"].as_str().expect("image path"));
    let xml_path = PathBuf::from(defect_data["manualXmlPath"].as_str().expect("xml path"));
    assert!(
        image_path.exists(),
        "updated manual crop image should exist"
    );
    assert!(xml_path.exists(), "updated manual xml should exist");
    assert!(image_path.starts_with(save_s.join("42").join("manual_defect").join("更新边裂")));
    assert_eq!(
        image::open(&image_path).expect("crop image").dimensions(),
        (128, 128)
    );

    let xml = fs::read_to_string(&xml_path).expect("xml text");
    assert!(xml.contains("<name>更新边裂</name>"));
    assert!(xml.contains("<xmin>24</xmin>"));
    assert!(xml.contains("<ymin>54</ymin>"));
    assert!(xml.contains("<xmax>104</xmax>"));
    assert!(xml.contains("<ymax>74</ymax>"));

    let (_, read_body) = request_json(app, "GET", "/manual_defects/42/S").await;
    assert_eq!(
        read_body[0]["defectData"]["manualXmlPath"],
        json!(xml_path.to_string_lossy())
    );
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_returns_python_compatible_errors_for_missing_inputs() {
    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/export_defects",
        json!({
            "defects": [],
            "folder_path": ""
        }),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 0);
    assert_eq!(body["error"], "请指定导出文件夹路径");

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/export_defects",
        json!({
            "defects": [],
            "folder_path": unique_temp_dir().join("exports").to_string_lossy()
        }),
    )
    .await;
    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 0);
    assert_eq!(body["error"], "没有可导出的缺陷数据");
}

#[tokio::test]
async fn export_defects_writes_manual_assets_and_auto_source_crops_by_category() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 220, 180);
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_defect_query_rows_and_data_config(config);

    let add_response = request_json_body(
        app.clone(),
        "POST",
        "/manual_defect/add",
        json!({
            "secondaryCoilId": 42,
            "surface": "S",
            "defectName": "边裂",
            "defectX": 20,
            "defectY": 30,
            "defectW": 40,
            "defectH": 50,
            "remark": "导出手动",
            "annotator": "测试员"
        }),
    )
    .await;
    assert_eq!(add_response.status(), StatusCode::OK);
    let manual_defect = response_json(add_response).await;

    let response = request_json_body(
        app,
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [
                manual_defect,
                {
                    "Id": 7,
                    "secondaryCoilId": 42,
                    "surface": "S",
                    "defectClass": 1,
                    "defectName": "压痕",
                    "defectStatus": 0,
                    "defectX": 11,
                    "defectY": 22,
                    "defectW": 33,
                    "defectH": 44,
                    "defectSource": 0.95,
                    "type": "auto"
                }
            ],
            "group_by_category": true,
            "include_info": true,
            "high_quality": false
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 2);
    assert_eq!(body["errors"], 0);
    assert_eq!(body["categories"], 2);
    assert_eq!(body["total"], 2);
    assert_eq!(
        body["message"],
        json!(format!(
            "成功导出 2 个缺陷图像到 {}",
            export_dir.to_string_lossy()
        ))
    );

    let manual_export = export_dir.join("边裂").join("42_边裂_x20_y30_1.jpg");
    let auto_export = export_dir.join("压痕").join("42_压痕_x11_y22_1.jpg");
    assert!(
        manual_export.exists(),
        "manual defect image should be exported"
    );
    assert!(auto_export.exists(), "auto defect crop should be exported");
    assert_eq!(
        image::open(&manual_export)
            .expect("manual export image")
            .dimensions(),
        (128, 128)
    );
    assert_eq!(
        image::open(&auto_export)
            .expect("auto export image")
            .dimensions(),
        (53, 64)
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_uses_area_source_and_fixed_margin_for_2d_defects() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 42, 240, 220);

    fs::create_dir_all(coil_dir.join("png")).expect("runtime area png dir");
    let area_image = RgbImage::from_pixel(240, 220, Rgb([5, 240, 10]));
    area_image
        .save_with_format(coil_dir.join("png").join("AREA.png"), ImageFormat::Png)
        .expect("write runtime area image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "2D_压痕",
                "defectStatus": 0,
                "defectX": 60,
                "defectY": 70,
                "defectW": 33,
                "defectH": 44,
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let export_path = export_dir.join("2D_压痕").join("42_2D_压痕_x60_y70_1.jpg");
    assert!(
        export_path.exists(),
        "2D auto defect crop should be exported"
    );
    let exported = image::open(&export_path)
        .expect("2D exported source crop")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (113, 124));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] < 40 && pixel[1] > 210 && pixel[2] < 45,
        "2D export should use AREA source image, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_uses_2d_margin_classifier_crop_before_generic_saved_images() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 42, 240, 220);

    let defect_data_image = RgbImage::from_pixel(9, 11, Rgb([240, 5, 10]));
    let defect_data_path = root.join("defect-data.png");
    defect_data_image
        .save_with_format(&defect_data_path, ImageFormat::Png)
        .expect("write defectData image");

    let classifier_dir = coil_dir.join("classifier").join("2D_压痕");
    fs::create_dir_all(&classifier_dir).expect("2D classifier crop dir");
    let generic_classifier_image = RgbImage::from_pixel(13, 15, Rgb([10, 20, 240]));
    generic_classifier_image
        .save_with_format(classifier_dir.join("42_60_70_93_114.png"), ImageFormat::Png)
        .expect("write generic classifier crop");
    let margin_classifier_image = RgbImage::from_pixel(17, 19, Rgb([5, 240, 10]));
    margin_classifier_image
        .save_with_format(
            classifier_dir.join("42_60_70_93_114_m40.png"),
            ImageFormat::Png,
        )
        .expect("write margin classifier crop");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "2D_压痕",
                "defectStatus": 0,
                "defectX": 60,
                "defectY": 70,
                "defectW": 33,
                "defectH": 44,
                "defectData": {
                    "image_path": defect_data_path.to_string_lossy()
                },
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let export_path = export_dir.join("2D_压痕").join("42_2D_压痕_x60_y70_1.jpg");
    assert!(
        export_path.exists(),
        "2D classifier crop should be exported"
    );
    let exported = image::open(&export_path)
        .expect("2D classifier export")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (17, 19));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] < 40 && pixel[1] > 210 && pixel[2] < 45,
        "2D export should use _m40 classifier crop, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_prefers_saved_classifier_crop_before_gray_source() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let classifier_dir = coil_dir.join("classifier").join("压痕");
    fs::create_dir_all(&classifier_dir).expect("classifier crop dir");
    let classifier_image = RgbImage::from_pixel(17, 19, Rgb([250, 5, 10]));
    classifier_image
        .save_with_format(classifier_dir.join("42_11_22_44_66.png"), ImageFormat::Png)
        .expect("classifier crop image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕",
                "defectStatus": 0,
                "defectX": 11,
                "defectY": 22,
                "defectW": 33,
                "defectH": 44,
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let auto_export = export_dir.join("压痕").join("42_压痕_x11_y22_1.jpg");
    assert!(auto_export.exists(), "auto defect crop should be exported");
    let exported = image::open(&auto_export)
        .expect("exported classifier crop")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (17, 19));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] > 220 && pixel[1] < 40 && pixel[2] < 45,
        "export should come from saved classifier crop, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_resolves_relative_defect_data_images_from_configured_save_folders() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let relative_image = RgbImage::from_pixel(9, 11, Rgb([250, 5, 10]));
    relative_image
        .save_with_format(save_s.join("relative-defect.png"), ImageFormat::Png)
        .expect("relative defectData image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕",
                "defectStatus": 0,
                "defectX": 11,
                "defectY": 22,
                "defectW": 33,
                "defectH": 44,
                "defectData": {
                    "image_path": "relative-defect.png"
                },
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let auto_export = export_dir.join("压痕").join("42_压痕_x11_y22_1.jpg");
    assert!(auto_export.exists(), "auto defect image should be exported");
    let exported = image::open(&auto_export)
        .expect("relative defectData export")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (9, 11));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] > 220 && pixel[1] < 40 && pixel[2] < 45,
        "export should come from relative defectData image, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_truncates_float_coordinates_like_python_int_conversion() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let classifier_dir = coil_dir.join("classifier").join("压痕");
    fs::create_dir_all(&classifier_dir).expect("float coordinate classifier crop dir");
    let classifier_image = RgbImage::from_pixel(17, 19, Rgb([250, 5, 10]));
    classifier_image
        .save_with_format(classifier_dir.join("42_11_22_44_66.png"), ImageFormat::Png)
        .expect("float coordinate classifier crop image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕",
                "defectStatus": 0,
                "defectX": 11.8,
                "defectY": 22.2,
                "defectW": 33.9,
                "defectH": 44.1,
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let auto_export = export_dir.join("压痕").join("42_压痕_x11_y22_1.jpg");
    assert!(auto_export.exists(), "auto defect crop should be exported");
    let exported = image::open(&auto_export)
        .expect("float coordinate classifier export")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (17, 19));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] > 220 && pixel[1] < 40 && pixel[2] < 45,
        "export should use Python-truncated float coordinates, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_counts_float_coordinate_strings_as_python_export_errors() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕",
                "defectStatus": 0,
                "defectX": "11.8",
                "defectY": "22.2",
                "defectW": "33.9",
                "defectH": "44.1",
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 0);
    assert_eq!(body["errors"], 1);
    assert_eq!(body["total"], 1);
    assert!(
        !export_dir
            .join("压痕")
            .join("42_压痕_x11_y22_1.jpg")
            .exists(),
        "Python export errors before writing a file for float-like coordinate strings"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_finds_classifier_crop_under_python_normalized_defect_name() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    let coil_dir = write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let classifier_dir = coil_dir.join("classifier").join("压痕");
    fs::create_dir_all(&classifier_dir).expect("normalized classifier crop dir");
    let classifier_image = RgbImage::from_pixel(17, 19, Rgb([250, 5, 10]));
    classifier_image
        .save_with_format(classifier_dir.join("42_11_22_44_66.png"), ImageFormat::Png)
        .expect("normalized classifier crop image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕(轻微)",
                "defectStatus": 0,
                "defectX": 11,
                "defectY": 22,
                "defectW": 33,
                "defectH": 44,
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let auto_export = export_dir
        .join("压痕(轻微)")
        .join("42_压痕(轻微)_x11_y22_1.jpg");
    assert!(auto_export.exists(), "auto defect crop should be exported");
    let exported = image::open(&auto_export)
        .expect("normalized classifier export")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (17, 19));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] > 220 && pixel[1] < 40 && pixel[2] < 45,
        "export should come from normalized classifier crop, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn export_defects_searches_classifier_crops_across_configured_surface_save_folders() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let export_dir = root.join("exports");
    write_runtime_config(&config_path, &save_s, &save_l);
    write_runtime_gray_image_coil(&save_s, 42, 220, 180);

    let l_coil_dir = save_l.join("42");
    let classifier_dir = l_coil_dir.join("classifier").join("压痕");
    fs::create_dir_all(&classifier_dir).expect("cross-surface classifier crop dir");
    let classifier_image = RgbImage::from_pixel(17, 19, Rgb([250, 5, 10]));
    classifier_image
        .save_with_format(classifier_dir.join("42_11_22_44_66.png"), ImageFormat::Png)
        .expect("cross-surface classifier crop image");

    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let response = request_json_body(
        app_with_data_config(config),
        "POST",
        "/export_defects",
        json!({
            "folder_path": export_dir.to_string_lossy(),
            "defects": [{
                "Id": 7,
                "secondaryCoilId": 42,
                "surface": "S",
                "defectClass": 1,
                "defectName": "压痕",
                "defectStatus": 0,
                "defectX": 11,
                "defectY": 22,
                "defectW": 33,
                "defectH": 44,
                "type": "auto"
            }]
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body["exported"], 1);
    assert_eq!(body["errors"], 0);

    let auto_export = export_dir.join("压痕").join("42_压痕_x11_y22_1.jpg");
    assert!(auto_export.exists(), "auto defect crop should be exported");
    let exported = image::open(&auto_export)
        .expect("cross-surface classifier export")
        .to_rgb8();
    assert_eq!(exported.dimensions(), (17, 19));
    let pixel = exported.get_pixel(0, 0);
    assert!(
        pixel[0] > 220 && pixel[1] < 40 && pixel[2] < 45,
        "export should come from classifier crop in another configured save folder, got {pixel:?}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn quick_xlsx_exports_return_python_compatible_attachment_responses() {
    let simple = request_response(app_with_seed_data(), "GET", "/exportDataSimple").await;
    assert_xlsx_export_response(simple, "exportDataSimple").await;

    let get_1h = request_response(app_with_seed_data(), "GET", "/export_1h").await;
    assert_xlsx_export_response(get_1h, "export_1h_").await;

    let post_24h = request_response(app_with_seed_data(), "POST", "/export_24h").await;
    assert_xlsx_export_response(post_24h, "export_24h_").await;

    let get_today = request_response(app_with_seed_data(), "GET", "/export_today").await;
    assert_xlsx_export_response(get_today, "export_today_").await;
}

#[tokio::test]
async fn range_and_config_xlsx_exports_return_python_compatible_attachment_responses() {
    let by_id = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxById/40/42?export_type=3D",
    )
    .await;
    assert_xlsx_export_response(by_id, "example").await;

    let by_datetime = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxByDateTime/202606270000/202606282359?export_type=3D",
    )
    .await;
    assert_xlsx_export_response(by_datetime, "example").await;

    let by_config = request_json_body(
        app_with_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": true,
            "defect_show_info": true,
            "defect_un_show_info": false,
            "area_defect_image": true,
            "export_plc_data": false,
            "startDate": "202606270000",
            "endDate": "202606282359"
        }),
    )
    .await;
    assert_xlsx_export_response(by_config, "example").await;
}

#[tokio::test]
async fn xlsx_exports_use_python_default_worksheet_names() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxById/40/42?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let workbook = xlsx_entry_text(&bytes, "xl/workbook.xml");
    assert!(
        workbook.contains(r#"name="数据报表""#),
        "workbook should include Python data worksheet name: {workbook}"
    );
    assert!(
        workbook.contains(r#"name="缺陷识别_3D""#),
        "workbook should include Python 3D defect worksheet name: {workbook}"
    );
    assert!(
        workbook.contains(r#"name="缺陷识别_2D""#),
        "workbook should include Python 2D defect worksheet name: {workbook}"
    );
}

#[tokio::test]
async fn xlsx_data_report_uses_python_business_headers() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxById/40/42?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");
    for header in [
        "流水号",
        "卷号",
        "钢种",
        "二级厚度",
        "二级宽度",
        "S端 缺陷数",
        "L端 缺陷数量",
    ] {
        assert!(
            sheet.contains(header),
            "数据报表 should include Python business header {header}: {sheet}"
        );
    }
    assert!(
        !sheet.contains("ExportType"),
        "数据报表 should not use Rust metadata rows as the primary report table: {sheet}"
    );
}

#[tokio::test]
async fn xlsx_data_report_includes_python_defect_category_counts() {
    let response = request_response(
        app_with_xlsx_defect_category_seed_data(),
        "GET",
        "/exportXlsxById/44/44?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    for header in [
        "边裂",
        "边裂_报警",
        "刮丝",
        "刮丝_报警",
        "边部褶皱",
        "边部褶皱_报警",
        "折叠",
        "折叠_报警",
        "分层",
        "分层_报警",
    ] {
        assert!(
            sheet.contains(header),
            "数据报表 should include Python defect category header {header}: {sheet}"
        );
    }
    assert!(
        sheet.contains(r#"<c r="Q2" t="inlineStr"><is><t>1</t></is></c>"#),
        "折叠 count should be 1 in the Python category column: {sheet}"
    );
    assert!(
        sheet.contains(r#"<c r="R2" t="inlineStr"><is><t>是</t></is></c>"#),
        "折叠_报警 should be 是 in the Python category column: {sheet}"
    );
}

#[tokio::test]
async fn post_xlsx_data_report_omits_defect_data_when_disabled_like_python() {
    let response = request_json_body(
        app_with_xlsx_defect_category_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": false,
            "defect_show_info": true,
            "defect_un_show_info": false,
            "area_defect_image": true,
            "export_plc_data": false,
            "startDate": "202606270000",
            "endDate": "202606272359"
        }),
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    for omitted in ["S端 缺陷数", "L端 缺陷数量", "折叠", "折叠_报警"] {
        assert!(
            !sheet.contains(omitted),
            "数据报表 should omit Python get_defect_data header {omitted} when defect_info=false: {sheet}"
        );
    }
    for retained in ["流水号", "卷号", "钢种", "二级宽度"] {
        assert!(
            sheet.contains(retained),
            "数据报表 should keep Python base header {retained}: {sheet}"
        );
    }
}

#[tokio::test]
async fn post_xlsx_omits_defect_image_sheets_when_disabled_like_python() {
    let response = request_json_body(
        app_with_2d_xlsx_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": true,
            "defect_show_info": false,
            "defect_un_show_info": false,
            "area_defect_image": false,
            "export_plc_data": false,
            "startDate": "202606270000",
            "endDate": "202606272359"
        }),
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let workbook = xlsx_entry_text(&bytes, "xl/workbook.xml");

    assert!(
        workbook.contains(r#"name="数据报表""#),
        "configured export should retain the data-report worksheet: {workbook}"
    );
    for omitted in ["缺陷识别_3D", "缺陷识别_2D"] {
        assert!(
            !workbook.contains(omitted),
            "configured export should omit Python defect image sheet {omitted} when all defect image switches are false: {workbook}"
        );
    }
}

#[tokio::test]
async fn post_xlsx_data_report_includes_plc_columns_when_requested_like_python() {
    let response = request_json_body(
        app_with_xlsx_plc_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": true,
            "defect_show_info": true,
            "defect_un_show_info": false,
            "area_defect_image": true,
            "export_plc_data": true,
            "startDate": "202606270000",
            "endDate": "202606272359"
        }),
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    for header in ["激光距离", "S端移动位置", "L端移动位置"] {
        assert!(
            sheet.contains(header),
            "数据报表 should include Python PLC header {header}: {sheet}"
        );
    }
    assert!(
        sheet.contains(r#"<c r="I2" t="inlineStr"><is><t>7.25</t></is></c>"#),
        "激光距离 should come from location_laser in the Python PLC column: {sheet}"
    );
    assert!(
        sheet.contains(r#"<c r="J2" t="inlineStr"><is><t>8.5</t></is></c>"#),
        "S端移动位置 should come from Python location_L / Rust location_l: {sheet}"
    );
    assert!(
        sheet.contains(r#"<c r="K2" t="inlineStr"><is><t>9.75</t></is></c>"#),
        "L端移动位置 should come from Python location_S / Rust location_s: {sheet}"
    );
}

#[tokio::test]
async fn xlsx_data_report_includes_python_alarm_columns_by_default() {
    let response = request_response(
        app_with_alarm_rows(),
        "GET",
        "/exportXlsxById/42/42?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    for header in [
        "S端 检测外径",
        "S端 检测内径",
        "S端 检测角度",
        "S端 外圈最大值",
        "S端 外圈最小值",
        "S端 内圈最大值",
        "S端 内圈最小值",
        "S端 松卷检测角度",
        "S端 松卷检测最宽",
    ] {
        assert!(
            sheet.contains(header),
            "数据报表 should include Python alarm header {header}: {sheet}"
        );
    }
    assert!(
        sheet.contains(r#"<c r="K2" t="inlineStr"><is><t>1.5</t></is></c>"#),
        "S端 检测角度 should come from AlarmTaperShape.rotation_angle: {sheet}"
    );
    assert!(
        sheet.contains(r#"<is><t>2.5</t></is>"#),
        "S端 松卷检测角度 should come from AlarmLooseCoil.rotation_angle: {sheet}"
    );
    assert!(
        sheet.contains(r#"<is><t>200</t></is>"#),
        "S端 松卷检测最宽 should come from AlarmLooseCoil.max_width: {sheet}"
    );
}

#[tokio::test]
async fn xlsx_data_report_formats_taper_detail_json_like_python() {
    let response = request_response(
        app_with_xlsx_taper_detail_seed_data(),
        "GET",
        "/exportXlsxById/47/47?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    for header in [
        "S端 塔形最严重类型",
        "S端 塔形最严重角度",
        "S端 塔形判定角度",
        "S端 塔形有效角度覆盖率",
        "S端 塔形分级无效线数量",
    ] {
        assert!(
            sheet.contains(header),
            "数据报表 should include Python taper detail header {header}: {sheet}"
        );
    }
    for value in ["边部突出", "12.5", "0.75", "5"] {
        assert!(
            sheet.contains(value),
            "数据报表 should include Python taper detail value {value}: {sheet}"
        );
    }
    assert!(
        sheet.contains(r#"<is><t>1, 2.5, raw</t></is>"#),
        "S端 塔形判定角度 should format list values like Python _format_taper_angle_filter: {sheet}"
    );
    assert!(
        !sheet.contains("1.0, 2.5, raw"),
        "S端 塔形判定角度 should not retain float-like string precision unlike Python: {sheet}"
    );
}

#[tokio::test]
async fn xlsx_3d_defect_sheet_includes_business_headers_and_defect_text() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxById/40/42?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");
    for text in [
        "流水号",
        "卷号",
        "钢种",
        "缺陷信息",
        "42",
        "LG-20260627-0042",
        "压痕",
    ] {
        assert!(
            sheet.contains(text),
            "缺陷识别_3D should include {text}: {sheet}"
        );
    }
}

#[tokio::test]
async fn xlsx_3d_defect_sheet_uses_actual_defect_rows_like_python() {
    let response = request_response(
        app_with_xlsx_actual_defect_row_seed_data(),
        "GET",
        "/exportXlsxById/46/46?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");

    for text in ["46", "LG-20260627-0046", "真实缺陷行", "11,22,33,44"] {
        assert!(
            sheet.contains(text),
            "缺陷识别_3D should be populated from actual CoilDefect rows even when summary max_defect is empty; missing {text}: {sheet}"
        );
    }
}

#[tokio::test]
async fn post_xlsx_3d_defect_sheets_split_visible_and_hidden_defects_like_python() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect visibility temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {
                "显示缺陷": {
                    "level": 2,
                    "color": "#00FF00",
                    "show": true
                },
                "屏蔽缺陷": {
                    "level": 1,
                    "color": "#666666",
                    "show": false
                }
            },
            "default": {
                "level": 1,
                "color": "#FFA500",
                "show": true
            }
        }))
        .expect("defect visibility json"),
    )
    .expect("write defect visibility config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_json_body(
        app_with_xlsx_visible_and_hidden_defects_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": true,
            "defect_show_info": true,
            "defect_un_show_info": true,
            "area_defect_image": false,
            "export_plc_data": false,
            "startDate": "202606270000",
            "endDate": "202606272359"
        }),
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let workbook = xlsx_entry_text(&bytes, "xl/workbook.xml");
    let show_sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");
    let hidden_sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet3.xml");

    assert!(
        workbook.contains(r#"name="缺陷识别_3D""#)
            && workbook.contains(r#"name="缺陷识别_3D_屏蔽""#),
        "configured export should include separate visible and hidden 3D defect sheets: {workbook}"
    );
    assert!(
        show_sheet.contains("显示缺陷") && !show_sheet.contains("屏蔽缺陷"),
        "visible 3D sheet should include only Python show=true defects: {show_sheet}"
    );
    assert!(
        hidden_sheet.contains("屏蔽缺陷") && !hidden_sheet.contains("显示缺陷"),
        "hidden 3D sheet should include only Python show=false defects: {hidden_sheet}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn post_xlsx_3d_defect_sheet_visibility_uses_defect_name_map_like_python() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect name map temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {
                "边部褶皱": {
                    "level": 2,
                    "color": "#999999",
                    "show": false
                }
            },
            "name_map": {
                "原始别名缺陷": "边部褶皱"
            },
            "default": {
                "level": 1,
                "color": "#FFA500",
                "show": true
            }
        }))
        .expect("defect name map json"),
    )
    .expect("write defect name map config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_json_body(
        app_with_xlsx_name_mapped_defect_seed_data(),
        "POST",
        "/export_xlsx",
        json!({
            "export_type": "3D",
            "detection_3d_info": true,
            "defect_info": true,
            "defect_show_info": true,
            "defect_un_show_info": true,
            "area_defect_image": false,
            "export_plc_data": false,
            "startDate": "202606270000",
            "endDate": "202606272359"
        }),
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let show_sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");
    let hidden_sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet3.xml");

    assert!(
        !show_sheet.contains("原始别名缺陷"),
        "visible 3D sheet should apply Python name_map before show lookup: {show_sheet}"
    );
    assert!(
        hidden_sheet.contains("原始别名缺陷"),
        "hidden 3D sheet should include name-mapped show=false defects: {hidden_sheet}"
    );

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn xlsx_2d_defect_sheet_includes_area_defect_text() {
    let response = request_response(
        app_with_2d_xlsx_seed_data(),
        "GET",
        "/exportXlsxById/43/43?export_type=3D",
    )
    .await;
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet_2d = xlsx_entry_text(&bytes, "xl/worksheets/sheet3.xml");
    for text in [
        "流水号",
        "卷号",
        "缺陷信息",
        "43",
        "LG-20260627-0043",
        "2D边裂",
    ] {
        assert!(
            sheet_2d.contains(text),
            "缺陷识别_2D should include {text}: {sheet_2d}"
        );
    }

    let sheet_3d = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");
    assert!(
        !sheet_3d.contains("2D边裂"),
        "2D defect text should not be placed in 缺陷识别_3D: {sheet_3d}"
    );
}

#[tokio::test]
async fn export_xlsx_by_datetime_rejects_malformed_dates_like_python() {
    for uri in [
        "/exportXlsxByDateTime/2026-06-27/2026-06-28",
        "/exportXlsxByDateTime/abc/202606282359",
        "/exportXlsxByDateTime/202606270000/abc",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;
        let status = response.status();
        let content_type = response
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok())
            .map(str::to_owned);
        let body = response_bytes(response).await;

        assert_eq!(status, StatusCode::INTERNAL_SERVER_ERROR, "{uri}");
        assert_eq!(content_type.as_deref(), Some("text/plain; charset=utf-8"));
        assert_eq!(body.as_ref(), b"export xlsx failed", "{uri}");
    }

    for (start_date, end_date) in [
        ("abc", "202606282359"),
        ("202606270000", "abc"),
        ("2026-06-27", "2026-06-28"),
    ] {
        let response = request_json_body(
            app_with_seed_data(),
            "POST",
            "/export_xlsx",
            json!({
                "export_type": "3D",
                "detection_3d_info": true,
                "defect_info": true,
                "defect_show_info": true,
                "defect_un_show_info": false,
                "area_defect_image": true,
                "export_plc_data": false,
                "startDate": start_date,
                "endDate": end_date
            }),
        )
        .await;
        let status = response.status();
        let content_type = response
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|value| value.to_str().ok())
            .map(str::to_owned);
        let body = response_bytes(response).await;

        assert_eq!(
            status,
            StatusCode::INTERNAL_SERVER_ERROR,
            "{start_date} {end_date}"
        );
        assert_eq!(content_type.as_deref(), Some("text/plain; charset=utf-8"));
        assert_eq!(body.as_ref(), b"export xlsx failed");
    }
}

#[tokio::test]
async fn export_xlsx_by_id_rejects_non_python_int_converter_paths_like_python() {
    for uri in [
        "/exportXlsxById/abc/1",
        "/exportXlsxById/-1/1",
        "/exportXlsxById/1/abc",
        "/exportXlsxById/1/-1",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn export_xlsx_by_id_with_reversed_range_matches_python_empty_span() {
    let response = request_response(
        app_with_seed_data(),
        "GET",
        "/exportXlsxById/44/42?export_type=3D",
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let bytes = assert_xlsx_export_response(response, "example").await;
    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet1.xml");

    assert!(
        !sheet.contains("LG-20260627-0042"),
        "reverse id range should not include the boundary coil under Python semantics: {sheet}"
    );
}

#[tokio::test]
async fn backup_image_task_rejects_non_python_int_converter_paths_like_python() {
    for uri in [
        "/backupImageTask/abc/42/tmp",
        "/backupImageTask/-1/42/tmp",
        "/backupImageTask/40/abc/tmp",
        "/backupImageTask/40/-1/tmp",
    ] {
        let response = request_response(app_with_seed_data(), "GET", uri).await;

        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{uri}");
        assert_eq!(
            response_json(response).await,
            json!({"detail": "Not Found"}),
            "{uri}"
        );
    }
}

#[tokio::test]
async fn backup_image_task_copies_configured_capture_folders_for_half_open_id_range() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let backup_dir = root.join("backup");
    write_backup_runtime_config(&config_path, &save_s, &save_l, &source_s, &source_l);
    write_capture_source_coil(&source_s, 40, "s-40");
    write_capture_source_coil(&source_s, 41, "s-41");
    write_capture_source_coil(&source_s, 42, "s-42");
    write_capture_source_coil(&source_l, 41, "l-41");
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_data_config(config);
    let save_folder = backup_dir.to_string_lossy().replace('\\', "/");

    let response =
        request_response(app, "GET", &format!("/backupImageTask/40/42/{save_folder}")).await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(response_json(response).await, Value::Null);
    assert_eq!(
        fs::read_to_string(
            backup_dir
                .join("Cap_S_D")
                .join("40")
                .join("2D")
                .join("frame.txt")
        )
        .expect("copied s 40"),
        "s-40"
    );
    assert_eq!(
        fs::read_to_string(
            backup_dir
                .join("Cap_S_D")
                .join("41")
                .join("2D")
                .join("frame.txt")
        )
        .expect("copied s 41"),
        "s-41"
    );
    assert!(
        !backup_dir
            .join("Cap_S_D")
            .join("42")
            .join("2D")
            .join("frame.txt")
            .exists(),
        "Python range semantics exclude to_id"
    );
    assert_eq!(
        fs::read_to_string(
            backup_dir
                .join("Cap_L_U")
                .join("41")
                .join("2D")
                .join("frame.txt")
        )
        .expect("copied l 41"),
        "l-41"
    );
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn backup_image_task_compresses_copied_camera_bmp_and_npy_like_python() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let backup_dir = root.join("backup_compress");
    write_backup_runtime_config(&config_path, &save_s, &save_l, &source_s, &source_l);
    write_capture_source_coil_with_compressible_data(&source_s, 60);
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let app = app_with_data_config(config);
    let save_folder = backup_dir.to_string_lossy().replace('\\', "/");

    let response =
        request_response(app, "GET", &format!("/backupImageTask/60/61/{save_folder}")).await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(response_json(response).await, Value::Null);
    let copied_coil_dir = backup_dir.join("Cap_S_D").join("60");
    let copied_bmp = copied_coil_dir.join("2D").join("frame.bmp");
    let copied_jpg = copied_coil_dir.join("2D").join("frame.jpg");
    let copied_npy = copied_coil_dir.join("3D").join("depth.npy");
    let copied_npz = copied_coil_dir.join("3D").join("depth.npz");
    assert!(!copied_bmp.exists(), "Python backup removes compressed bmp");
    assert!(copied_jpg.exists(), "Python backup writes jpg next to bmp");
    assert!(!copied_npy.exists(), "Python backup removes compressed npy");
    assert!(copied_npz.exists(), "Python backup writes compressed npz");

    let image = image::open(&copied_jpg).expect("compressed jpg");
    assert_eq!(image.dimensions(), (2, 2));
    let file = File::open(&copied_npz).expect("open compressed npz");
    let mut npz = NpzReader::new(file).expect("read compressed npz");
    let depth: ndarray::Array2<f64> = npz.by_name("array").expect("array entry");
    assert_eq!(depth, arr2(&[[1.0_f64, 2.0], [3.0, 4.0]]));

    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn backup_image_task_websocket_sends_100_after_copying_capture_folders() {
    let root = unique_temp_dir();
    let config_path = root.join("Server3D.json");
    let save_s = root.join("Save_S");
    let save_l = root.join("Save_L");
    let source_s = root.join("Cap_S_D");
    let source_l = root.join("Cap_L_U");
    let backup_dir = root.join("backup_ws");
    write_backup_runtime_config(&config_path, &save_s, &save_l, &source_s, &source_l);
    write_capture_source_coil(&source_s, 50, "s-50");
    let config = DataRuntimeConfig::load(&config_path).expect("runtime config");
    let ws_url = spawn_ws_server(app_with_data_config(config), "/ws/backupImageTask").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect backup ws");

    socket
        .send(Message::Text(
            json!({
                "from_id": 50,
                "to_id": 51,
                "folder": backup_dir.to_string_lossy()
            })
            .to_string()
            .into(),
        ))
        .await
        .expect("send backup request");
    let message = socket
        .next()
        .await
        .expect("backup ws message")
        .expect("backup ws text");

    assert_eq!(message.into_text().expect("backup ws text"), "100");
    assert_eq!(
        fs::read_to_string(
            backup_dir
                .join("Cap_S_D")
                .join("50")
                .join("2D")
                .join("frame.txt")
        )
        .expect("copied ws s 50"),
        "s-50"
    );
    let _ = fs::remove_dir_all(root);
}

#[tokio::test]
async fn backup_image_task_websocket_rejects_missing_folder_field() {
    let app = app_with_seed_data();
    let ws_url = spawn_ws_server(app, "/ws/backupImageTask").await;
    let (mut socket, _) = connect_async(&ws_url).await.expect("connect backup ws");

    socket
        .send(
            Message::Text(
                json!({
                    "from_id": 50,
                    "to_id": 51,
                })
                .to_string()
                .into(),
            ),
        )
        .await
        .expect("send payload without folder");

    let terminal = tokio::time::timeout(Duration::from_millis(800), socket.next())
        .await
        .expect("missing folder should terminate the connection");
    assert!(
        matches!(terminal, None | Some(Ok(Message::Close(_)))),
        "connection should close after payload missing folder"
    );
}

#[tokio::test]
async fn save_to_sql_writes_sql_and_sqlite_snapshot_files_with_python_state_shape() {
    let _env_lock = lock_test_env();
    let _database_url_guard = set_env_var_guard(
        DATABASE_URL_ENV,
        "mysql+pymysql://test_user:test_pass@127.0.0.1:3306/Coil?charset=utf8mb4",
    );
    let _dump_guard = set_env_var_guard(
        "RUST_API_MYSQLDUMP_EXE",
        "Z:\\missing\\mysqldump-for-rust-api-test.exe",
    );

    let root = unique_temp_dir();
    let sql_path = root.join("snapshot.sql");
    let db_path = root.join("snapshot.db");
    let txt_path = root.join("snapshot.txt");
    let sql_uri = sql_path.to_string_lossy().replace('\\', "/");
    let db_uri = db_path.to_string_lossy().replace('\\', "/");
    let txt_uri = txt_path.to_string_lossy().replace('\\', "/");

    let sql_response = request_response(
        app_with_seed_data(),
        "GET",
        &format!("/save_to_sql/{sql_uri}"),
    )
    .await;
    assert_eq!(sql_response.status(), StatusCode::OK);
    assert_eq!(response_json(sql_response).await, json!({"state": false}));
    if sql_path.exists() {
        assert_eq!(
            fs::metadata(&sql_path).expect("sql metadata").len(),
            0,
            "Python backup_to_sql may create an empty output file before mysqldump fails"
        );
    }

    let db_response = request_response(
        app_with_save_to_sql_seed_data(),
        "GET",
        &format!("/save_to_sql/{db_uri}"),
    )
    .await;
    assert_eq!(db_response.status(), StatusCode::OK);
    assert_eq!(response_json(db_response).await, json!({"state": true}));
    assert!(db_path.exists(), "sqlite snapshot should be created");
    let db_header = fs::read(&db_path).expect("sqlite file");
    assert_eq!(&db_header[..16], b"SQLite format 3\0");
    let sqlite = rusqlite::Connection::open(&db_path).expect("open sqlite snapshot");
    let expected_model_tables = [
        "AlarmFlatRoll",
        "AlarmFlatRollData",
        "AlarmInfo",
        "AlarmLooseCoil",
        "AlarmTaperShape",
        "CapTrueLog",
        "CapTrueLogItem",
        "Coil",
        "CoilAlarmStatus",
        "CoilCheck",
        "CoilDefect",
        "CoilState",
        "DataEllipse",
        "DeepPoint",
        "DefectCheck",
        "DefectClassDict",
        "DefectStatistics",
        "DetectionSpeed",
        "ImageJoinLog",
        "LineData",
        "ManualDefect",
        "NextCodeDict",
        "PlcData",
        "PointData",
        "SecondaryCoil",
        "ServerDetectionError",
        "TaperShapePoint",
        "coil_summary",
        "coil_summary_snapshot",
    ];
    for table in expected_model_tables {
        let table_count: i64 = sqlite
            .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
                row.get(0)
            })
            .unwrap_or_else(|error| panic!("{table} table should exist: {error}"));
        assert!(
            table_count >= 0,
            "{table} table count should be readable from SQLite"
        );
    }
    let secondary_count: i64 = sqlite
        .query_row("SELECT COUNT(*) FROM SecondaryCoil", [], |row| row.get(0))
        .expect("SecondaryCoil count");
    let defect_count: i64 = sqlite
        .query_row("SELECT COUNT(*) FROM CoilDefect", [], |row| row.get(0))
        .expect("CoilDefect count");
    let secondary_coil_no: String = sqlite
        .query_row(
            "SELECT CoilNo FROM SecondaryCoil WHERE Id = 42",
            [],
            |row| row.get(0),
        )
        .expect("seed coil number");
    let secondary_thickness: f64 = sqlite
        .query_row(
            "SELECT Thickness FROM SecondaryCoil WHERE Id = 42",
            [],
            |row| row.get(0),
        )
        .expect("seed secondary thickness");
    let secondary_without_summary_no: String = sqlite
        .query_row(
            "SELECT CoilNo FROM SecondaryCoil WHERE Id = 77",
            [],
            |row| row.get(0),
        )
        .expect("secondary without summary coil number");
    let summary_coil_no: String = sqlite
        .query_row("SELECT CoilNo FROM coil_summary WHERE Id = 42", [], |row| {
            row.get(0)
        })
        .expect("seed coil summary number");
    let summary_grade: i64 = sqlite
        .query_row("SELECT Grade FROM coil_summary WHERE Id = 42", [], |row| {
            row.get(0)
        })
        .expect("seed coil summary grade");
    let summary_s_taper_grad: i64 = sqlite
        .query_row(
            "SELECT S_TaperShapeGrad FROM coil_summary WHERE Id = 42",
            [],
            |row| row.get(0),
        )
        .expect("seed summary s taper grade");
    let coil_secondary_id: i64 = sqlite
        .query_row(
            "SELECT SecondaryCoilId FROM Coil WHERE Id = 902",
            [],
            |row| row.get(0),
        )
        .expect("seed coil child secondary id");
    let coil_detection_time: String = sqlite
        .query_row("SELECT DetectionTime FROM Coil WHERE Id = 902", [], |row| {
            row.get(0)
        })
        .expect("seed coil child detection time");
    let coil_defect_count_s: i64 = sqlite
        .query_row("SELECT DefectCountS FROM Coil WHERE Id = 902", [], |row| {
            row.get(0)
        })
        .expect("seed coil child defect count");
    let coil_grade: i64 = sqlite
        .query_row("SELECT Grade FROM Coil WHERE Id = 902", [], |row| {
            row.get(0)
        })
        .expect("seed coil child grade");
    let coil_msg: String = sqlite
        .query_row("SELECT Msg FROM Coil WHERE Id = 902", [], |row| row.get(0))
        .expect("seed coil child msg");
    let orphan_coil_msg: String = sqlite
        .query_row("SELECT Msg FROM Coil WHERE Id = 903", [], |row| row.get(0))
        .expect("range-outside coil child backup row");
    let defect_name: String = sqlite
        .query_row(
            "SELECT defectName FROM CoilDefect WHERE Id = 7",
            [],
            |row| row.get(0),
        )
        .expect("seed defect name");
    let defect_dict_name: String = sqlite
        .query_row(
            "SELECT defectName FROM DefectClassDict WHERE Id = 100",
            [],
            |row| row.get(0),
        )
        .expect("seed defect class name");
    let defect_dict_level: i64 = sqlite
        .query_row(
            "SELECT defectLevel FROM DefectClassDict WHERE Id = 100",
            [],
            |row| row.get(0),
        )
        .expect("seed defect class level");
    let alarm_info_count: i64 = sqlite
        .query_row(
            "SELECT COUNT(*) FROM AlarmInfo WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("seed alarm info count");
    let s_alarm_grad: i64 = sqlite
        .query_row(
            "SELECT grad FROM AlarmInfo WHERE secondaryCoilId = 42 AND surface = 'S'",
            [],
            |row| row.get(0),
        )
        .expect("seed s alarm info");
    let s_taper_grad: i64 = sqlite
        .query_row(
            "SELECT taperShapeGrad FROM AlarmInfo WHERE secondaryCoilId = 42 AND surface = 'S'",
            [],
            |row| row.get(0),
        )
        .expect("seed s taper alarm info");
    let s_next_code: String = sqlite
        .query_row(
            "SELECT nextCode FROM AlarmInfo WHERE secondaryCoilId = 42 AND surface = 'S'",
            [],
            |row| row.get(0),
        )
        .expect("seed s alarm next code");
    let orphan_alarm_info_msg: String = sqlite
        .query_row("SELECT defectMsg FROM AlarmInfo WHERE Id = 83", [], |row| {
            row.get(0)
        })
        .expect("range-outside alarm info backup row");
    let next_code_dict_count: i64 = sqlite
        .query_row("SELECT COUNT(*) FROM NextCodeDict", [], |row| row.get(0))
        .expect("next code dict count");
    let (next_code_dict_id, next_code_dict_code, next_code_dict_info): (i64, String, String) =
        sqlite
            .query_row(
                "SELECT Id, code, info FROM NextCodeDict WHERE Id = 93",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .expect("seed next code dict row");
    assert_eq!(secondary_count, 2);
    let orphan_defect_name: String = sqlite
        .query_row(
            "SELECT defectName FROM CoilDefect WHERE Id = 8",
            [],
            |row| row.get(0),
        )
        .expect("range-outside defect backup row");
    assert_eq!(defect_count, 2);
    assert_eq!(secondary_coil_no, "REAL-SECONDARY-0042");
    assert_eq!(secondary_thickness, 2.6);
    assert_eq!(secondary_without_summary_no, "SECONDARY-NO-SUMMARY-0077");
    assert_eq!(summary_coil_no, "LG-20260627-0042");
    assert_eq!(summary_grade, 2);
    assert_eq!(summary_s_taper_grad, 2);
    assert_eq!(coil_secondary_id, 42);
    assert_eq!(coil_detection_time, "2026-06-27 12:35:10");
    assert_eq!(coil_defect_count_s, 8);
    assert_eq!(coil_grade, 3);
    assert_eq!(coil_msg, "真实检测备注");
    assert_eq!(orphan_coil_msg, "孤立检测备注");
    assert_eq!(defect_name, "压痕");
    assert_eq!(orphan_defect_name, "孤立缺陷");
    assert_eq!(defect_dict_name, "压痕");
    assert_eq!(defect_dict_level, 2);
    assert_eq!(alarm_info_count, 1);
    assert_eq!(s_alarm_grad, 5);
    assert_eq!(s_taper_grad, 3);
    assert_eq!(s_next_code, "B");
    assert_eq!(orphan_alarm_info_msg, "孤立缺陷报警");
    assert_eq!(next_code_dict_count, 1);
    assert_eq!(next_code_dict_id, 93);
    assert_eq!(next_code_dict_code, "Z");
    assert_eq!(next_code_dict_info, "真实字典工序");
    let coil_state_count: i64 = sqlite
        .query_row(
            "SELECT COUNT(*) FROM CoilState WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("coil state history count");
    let coil_state_first_json: String = sqlite
        .query_row("SELECT jsonData FROM CoilState WHERE Id = 101", [], |row| {
            row.get(0)
        })
        .expect("oldest coil state history");
    let plc_count: i64 = sqlite
        .query_row(
            "SELECT COUNT(*) FROM PlcData WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("plc history count");
    let first_plc_data: String = sqlite
        .query_row("SELECT pclData FROM PlcData WHERE Id = 201", [], |row| {
            row.get(0)
        })
        .expect("oldest plc data");
    assert_eq!(coil_state_count, 3);
    assert_eq!(coil_state_first_json, "{\"history\":1}");
    assert_eq!(plc_count, 2);
    assert_eq!(first_plc_data, "{\"frame\":1}");

    let alarm_db_path = root.join("alarm_snapshot.db");
    let alarm_db_uri = alarm_db_path.to_string_lossy().replace('\\', "/");
    let alarm_db_response = request_response(
        app_with_alarm_rows(),
        "GET",
        &format!("/save_to_sql/{alarm_db_uri}"),
    )
    .await;
    assert_eq!(alarm_db_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(alarm_db_response).await,
        json!({"state": true})
    );
    let alarm_sqlite = rusqlite::Connection::open(&alarm_db_path).expect("open alarm sqlite");
    let flat_err_msg: String = alarm_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmFlatRoll WHERE Id = 81",
            [],
            |row| row.get(0),
        )
        .expect("flat roll backup row");
    let flat_roll_count: i64 = alarm_sqlite
        .query_row(
            "SELECT COUNT(*) FROM AlarmFlatRoll WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("flat roll backup history count");
    let third_flat_roll_msg: String = alarm_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmFlatRoll WHERE Id = 83",
            [],
            |row| row.get(0),
        )
        .expect("third flat roll backup row");
    let taper_value: f64 = alarm_sqlite
        .query_row(
            "SELECT out_taper_max_value FROM AlarmTaperShape WHERE Id = 91",
            [],
            |row| row.get(0),
        )
        .expect("taper shape backup row");
    let loose_width: f64 = alarm_sqlite
        .query_row(
            "SELECT max_width FROM AlarmLooseCoil WHERE Id = 101",
            [],
            |row| row.get(0),
        )
        .expect("loose coil backup row");
    let taper_point_value: f64 = alarm_sqlite
        .query_row(
            "SELECT value FROM TaperShapePoint WHERE Id = 111",
            [],
            |row| row.get(0),
        )
        .expect("taper shape point backup row");
    let orphan_taper_msg: String = alarm_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmTaperShape WHERE Id = 92",
            [],
            |row| row.get(0),
        )
        .expect("range-outside taper shape backup row");
    let orphan_loose_msg: String = alarm_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmLooseCoil WHERE Id = 102",
            [],
            |row| row.get(0),
        )
        .expect("range-outside loose coil backup row");
    let orphan_taper_point_value: f64 = alarm_sqlite
        .query_row(
            "SELECT value FROM TaperShapePoint WHERE Id = 112",
            [],
            |row| row.get(0),
        )
        .expect("range-outside taper shape point backup row");
    assert_eq!(flat_err_msg, "扁卷报警");
    assert_eq!(flat_roll_count, 3);
    assert_eq!(third_flat_roll_msg, "扁卷第三条报警");
    assert_eq!(taper_value, 3.4);
    assert_eq!(loose_width, 200.0);
    assert_eq!(taper_point_value, 12.5);
    assert_eq!(orphan_taper_msg, "孤立塔形报警");
    assert_eq!(orphan_loose_msg, "孤立松卷报警");
    assert_eq!(orphan_taper_point_value, 22.5);

    let full_db_path = root.join("full_snapshot.db");
    let full_db_uri = full_db_path.to_string_lossy().replace('\\', "/");
    let full_app = app_with_process_rows();
    let set_check_response = request_response(
        full_app.clone(),
        "GET",
        "/check/set_coil_status/42/2/needs-review",
    )
    .await;
    assert_eq!(set_check_response.status(), StatusCode::OK);
    let full_db_response =
        request_response(full_app, "GET", &format!("/save_to_sql/{full_db_uri}")).await;
    assert_eq!(full_db_response.status(), StatusCode::OK);
    assert_eq!(
        response_json(full_db_response).await,
        json!({"state": true})
    );
    let full_sqlite = rusqlite::Connection::open(&full_db_path).expect("open full sqlite snapshot");
    let manual_name: String = full_sqlite
        .query_row(
            "SELECT defectName FROM ManualDefect WHERE Id = 51",
            [],
            |row| row.get(0),
        )
        .expect("manual defect name");
    let orphan_manual_name: String = full_sqlite
        .query_row(
            "SELECT defectName FROM ManualDefect WHERE Id = 52",
            [],
            |row| row.get(0),
        )
        .expect("range-outside manual defect backup row");
    let state_surface: String = full_sqlite
        .query_row("SELECT surface FROM CoilState WHERE Id = 9", [], |row| {
            row.get(0)
        })
        .expect("coil state surface");
    let plc_location: f64 = full_sqlite
        .query_row("SELECT location_S FROM PlcData WHERE Id = 12", [], |row| {
            row.get(0)
        })
        .expect("plc location");
    let check_msg: String = full_sqlite
        .query_row(
            "SELECT msg FROM CoilCheck WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("coil check msg");
    let check_status: i64 = full_sqlite
        .query_row(
            "SELECT status FROM CoilCheck WHERE secondaryCoilId = 42",
            [],
            |row| row.get(0),
        )
        .expect("coil check status");
    let orphan_check_msg: String = full_sqlite
        .query_row("SELECT msg FROM CoilCheck WHERE Id = 62", [], |row| {
            row.get(0)
        })
        .expect("range-outside coil check backup row");
    let point_type: String = full_sqlite
        .query_row("SELECT type FROM PointData WHERE Id = 2", [], |row| {
            row.get(0)
        })
        .expect("point type");
    let point_z_mm: f64 = full_sqlite
        .query_row("SELECT z_mm FROM PointData WHERE Id = 2", [], |row| {
            row.get(0)
        })
        .expect("point z_mm");
    let orphan_point_type: String = full_sqlite
        .query_row("SELECT type FROM PointData WHERE Id = 5", [], |row| {
            row.get(0)
        })
        .expect("range-outside point data backup row");
    let line_type: String = full_sqlite
        .query_row("SELECT type FROM LineData WHERE Id = 4", [], |row| {
            row.get(0)
        })
        .expect("line type");
    let line_inner_min: f64 = full_sqlite
        .query_row(
            "SELECT inner_min_value FROM LineData WHERE Id = 4",
            [],
            |row| row.get(0),
        )
        .expect("line inner min");
    let orphan_line_type: String = full_sqlite
        .query_row("SELECT type FROM LineData WHERE Id = 6", [], |row| {
            row.get(0)
        })
        .expect("range-outside line data backup row");
    let server_error_msg: String = full_sqlite
        .query_row(
            "SELECT msg FROM ServerDetectionError WHERE Id = 71",
            [],
            |row| row.get(0),
        )
        .expect("server detection error msg");
    let server_error_type: String = full_sqlite
        .query_row(
            "SELECT errorType FROM ServerDetectionError WHERE Id = 71",
            [],
            |row| row.get(0),
        )
        .expect("server detection error type");
    let orphan_server_error_msg: String = full_sqlite
        .query_row(
            "SELECT msg FROM ServerDetectionError WHERE Id = 171",
            [],
            |row| row.get(0),
        )
        .expect("range-outside server detection error backup row");
    let defect_check_msg: String = full_sqlite
        .query_row("SELECT msg FROM DefectCheck WHERE Id = 72", [], |row| {
            row.get(0)
        })
        .expect("defect check msg");
    let defect_check_status: i64 = full_sqlite
        .query_row("SELECT status FROM DefectCheck WHERE Id = 72", [], |row| {
            row.get(0)
        })
        .expect("defect check status");
    let defect_check_new_name: String = full_sqlite
        .query_row(
            "SELECT newDefectName FROM DefectCheck WHERE Id = 72",
            [],
            |row| row.get(0),
        )
        .expect("defect check new name");
    let orphan_defect_check_msg: String = full_sqlite
        .query_row("SELECT msg FROM DefectCheck WHERE Id = 172", [], |row| {
            row.get(0)
        })
        .expect("range-outside defect check backup row");
    let data_ellipse_type: String = full_sqlite
        .query_row("SELECT type FROM DataEllipse WHERE Id = 73", [], |row| {
            row.get(0)
        })
        .expect("data ellipse type");
    let data_ellipse_level: i64 = full_sqlite
        .query_row("SELECT level FROM DataEllipse WHERE Id = 73", [], |row| {
            row.get(0)
        })
        .expect("data ellipse level");
    let data_ellipse_msg: String = full_sqlite
        .query_row("SELECT err_msg FROM DataEllipse WHERE Id = 73", [], |row| {
            row.get(0)
        })
        .expect("data ellipse msg");
    let orphan_data_ellipse_msg: String = full_sqlite
        .query_row(
            "SELECT err_msg FROM DataEllipse WHERE Id = 173",
            [],
            |row| row.get(0),
        )
        .expect("range-outside data ellipse backup row");
    let deep_point_value_int: i64 = full_sqlite
        .query_row("SELECT value_int FROM DeepPoint WHERE Id = 74", [], |row| {
            row.get(0)
        })
        .expect("deep point value int");
    let deep_point_err_msg: String = full_sqlite
        .query_row("SELECT err_msg FROM DeepPoint WHERE Id = 74", [], |row| {
            row.get(0)
        })
        .expect("deep point err msg");
    let orphan_deep_point_value_int: i64 = full_sqlite
        .query_row(
            "SELECT value_int FROM DeepPoint WHERE Id = 174",
            [],
            |row| row.get(0),
        )
        .expect("range-outside deep point backup row");
    let detection_speed_surface: String = full_sqlite
        .query_row(
            "SELECT surface FROM DetectionSpeed WHERE Id = 75",
            [],
            |row| row.get(0),
        )
        .expect("detection speed surface");
    let detection_speed_all_time: f64 = full_sqlite
        .query_row(
            "SELECT allTime FROM DetectionSpeed WHERE Id = 75",
            [],
            |row| row.get(0),
        )
        .expect("detection speed all time");
    let orphan_detection_speed_all_time: f64 = full_sqlite
        .query_row(
            "SELECT allTime FROM DetectionSpeed WHERE Id = 175",
            [],
            |row| row.get(0),
        )
        .expect("range-outside detection speed backup row");
    let coil_alarm_status_alarm: i64 = full_sqlite
        .query_row(
            "SELECT alarmDefect FROM CoilAlarmStatus WHERE Id = 76",
            [],
            |row| row.get(0),
        )
        .expect("coil alarm status defect flag");
    let coil_alarm_status_data: String = full_sqlite
        .query_row(
            "SELECT data FROM CoilAlarmStatus WHERE Id = 76",
            [],
            |row| row.get(0),
        )
        .expect("coil alarm status data");
    let orphan_coil_alarm_status_data: String = full_sqlite
        .query_row(
            "SELECT data FROM CoilAlarmStatus WHERE Id = 176",
            [],
            |row| row.get(0),
        )
        .expect("range-outside coil alarm status backup row");
    let image_join_rotate: f64 = full_sqlite
        .query_row("SELECT rotate FROM ImageJoinLog WHERE Id = 77", [], |row| {
            row.get(0)
        })
        .expect("image join rotate");
    let image_join_data: String = full_sqlite
        .query_row("SELECT data FROM ImageJoinLog WHERE Id = 77", [], |row| {
            row.get(0)
        })
        .expect("image join data");
    let orphan_image_join_data: String = full_sqlite
        .query_row("SELECT data FROM ImageJoinLog WHERE Id = 177", [], |row| {
            row.get(0)
        })
        .expect("range-outside image join backup row");
    let defect_statistics_surface: String = full_sqlite
        .query_row(
            "SELECT surface FROM DefectStatistics WHERE Id = 78",
            [],
            |row| row.get(0),
        )
        .expect("defect statistics surface");
    let orphan_defect_statistics_surface: String = full_sqlite
        .query_row(
            "SELECT surface FROM DefectStatistics WHERE Id = 178",
            [],
            |row| row.get(0),
        )
        .expect("range-outside defect statistics backup row");
    let alarm_flat_roll_data_msg: String = full_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmFlatRollData WHERE Id = 79",
            [],
            |row| row.get(0),
        )
        .expect("alarm flat roll data msg");
    let alarm_flat_roll_data_level: i64 = full_sqlite
        .query_row(
            "SELECT level FROM AlarmFlatRollData WHERE Id = 79",
            [],
            |row| row.get(0),
        )
        .expect("alarm flat roll data level");
    let orphan_alarm_flat_roll_data_msg: String = full_sqlite
        .query_row(
            "SELECT err_msg FROM AlarmFlatRollData WHERE Id = 179",
            [],
            |row| row.get(0),
        )
        .expect("range-outside alarm flat roll data backup row");
    let cap_true_log_camera_name: String = full_sqlite
        .query_row(
            "SELECT cameraName FROM CapTrueLog WHERE Id = 80",
            [],
            |row| row.get(0),
        )
        .expect("cap true log camera name");
    let orphan_cap_true_log_camera_name: String = full_sqlite
        .query_row(
            "SELECT cameraName FROM CapTrueLog WHERE Id = 180",
            [],
            |row| row.get(0),
        )
        .expect("range-outside cap true log backup row");
    let cap_true_log_item_index: i64 = full_sqlite
        .query_row(
            "SELECT imageIndex FROM CapTrueLogItem WHERE Id = 81",
            [],
            |row| row.get(0),
        )
        .expect("cap true log item index");
    let orphan_cap_true_log_item_index: i64 = full_sqlite
        .query_row(
            "SELECT imageIndex FROM CapTrueLogItem WHERE Id = 181",
            [],
            |row| row.get(0),
        )
        .expect("range-outside cap true log item backup row");
    let alarm_info_flat_roll_msg: String = full_sqlite
        .query_row(
            "SELECT flatRollMsg FROM AlarmInfo WHERE Id = 82",
            [],
            |row| row.get(0),
        )
        .expect("alarm info flat roll msg");
    let alarm_info_defect_grad: i64 = full_sqlite
        .query_row(
            "SELECT defectGrad FROM AlarmInfo WHERE Id = 82",
            [],
            |row| row.get(0),
        )
        .expect("alarm info defect grad");
    let alarm_info_data: String = full_sqlite
        .query_row("SELECT data FROM AlarmInfo WHERE Id = 82", [], |row| {
            row.get(0)
        })
        .expect("alarm info data");
    assert_eq!(manual_name, "手动压痕");
    assert_eq!(orphan_manual_name, "孤立手动缺陷");
    assert_eq!(state_surface, "S");
    assert_eq!(plc_location, 123.4000015258789);
    assert_eq!(check_msg, "needs-review");
    assert_eq!(check_status, 2);
    assert_eq!(orphan_check_msg, "孤立检查记录");
    assert_eq!(point_type, "inner");
    assert_eq!(point_z_mm, 16.5);
    assert_eq!(orphan_point_type, "orphan-point");
    assert_eq!(line_type, "diameter");
    assert_eq!(line_inner_min, 12.0);
    assert_eq!(orphan_line_type, "orphan-line");
    assert_eq!(server_error_msg, "拼接失败");
    assert_eq!(server_error_type, "ImageMosaic");
    assert_eq!(orphan_server_error_msg, "孤立服务错误");
    assert_eq!(defect_check_msg, "人工复核改判");
    assert_eq!(defect_check_status, 2);
    assert_eq!(defect_check_new_name, "划伤");
    assert_eq!(orphan_defect_check_msg, "孤立缺陷复核");
    assert_eq!(data_ellipse_type, "inner");
    assert_eq!(data_ellipse_level, 2);
    assert_eq!(data_ellipse_msg, "椭圆偏移");
    assert_eq!(orphan_data_ellipse_msg, "孤立椭圆偏移");
    assert_eq!(deep_point_value_int, -35);
    assert_eq!(deep_point_err_msg, "深度异常");
    assert_eq!(orphan_deep_point_value_int, -95);
    assert_eq!(detection_speed_surface, "S");
    assert_eq!(detection_speed_all_time, 8.25);
    assert_eq!(orphan_detection_speed_all_time, 18.75);
    assert_eq!(coil_alarm_status_alarm, 1);
    assert_eq!(coil_alarm_status_data, "{\"alarm\":true}");
    assert_eq!(
        orphan_coil_alarm_status_data,
        "{\"orphanAlarmStatus\":true}"
    );
    assert_eq!(image_join_rotate, 1.5);
    assert_eq!(image_join_data, "{\"join\":true}");
    assert_eq!(orphan_image_join_data, "{\"orphanJoin\":true}");
    assert_eq!(defect_statistics_surface, "L");
    assert_eq!(orphan_defect_statistics_surface, "S");
    assert_eq!(alarm_flat_roll_data_msg, "扁卷明细报警");
    assert_eq!(alarm_flat_roll_data_level, 4);
    assert_eq!(orphan_alarm_flat_roll_data_msg, "孤立扁卷明细报警");
    assert_eq!(cap_true_log_camera_name, "S端深度");
    assert_eq!(cap_true_log_item_index, 7);
    assert_eq!(orphan_cap_true_log_camera_name, "孤立相机");
    assert_eq!(orphan_cap_true_log_item_index, 17);
    assert_eq!(alarm_info_flat_roll_msg, "真实扁卷报警");
    assert_eq!(alarm_info_defect_grad, 4);
    assert_eq!(alarm_info_data, "{\"alarmInfo\":true}");

    let txt_response = request_response(
        app_with_seed_data(),
        "GET",
        &format!("/save_to_sql/{txt_uri}"),
    )
    .await;
    assert_eq!(txt_response.status(), StatusCode::OK);
    assert_eq!(response_json(txt_response).await, json!({"state": false}));
    assert!(!txt_path.exists());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn normalizes_python_mysql_url_for_sqlx() {
    let normalized =
        normalize_database_url("mysql+pymysql://root:nercar@127.0.0.1:3306/Coil?charset=utf8mb4")
            .expect("normalized");

    assert_eq!(normalized, "mysql://root:nercar@127.0.0.1:3306/Coil");
}
