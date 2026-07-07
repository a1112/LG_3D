use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::collections::hash_map::DefaultHasher;
use std::fs::{self, File};
use std::io::{Cursor, Write};
use std::hash::{Hash, Hasher};
use std::path::{Path as FsPath, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use axum::body::Bytes;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{DefaultBodyLimit, Path, Query, State};
use axum::http::{HeaderMap, StatusCode, header};
use axum::response::{IntoResponse, Response};
use axum::routing::{delete, get, post, put};
use axum::{Json, Router};
use chrono::{Datelike, Local, NaiveDateTime, Timelike};
use image::codecs::jpeg::JpegEncoder;
use image::{
    DynamicImage, ExtendedColorType, GrayImage, ImageFormat, Rgb, RgbImage, Rgba, RgbaImage,
    imageops,
};
use rusqlite::{Connection, params};
use serde::Deserialize;
use serde_json::{Map, Value, json};
use sysinfo::{Disks, System};
use tower_http::cors::CorsLayer;
use tower_http::trace::{DefaultOnResponse, TraceLayer};
use tracing::{Level, info};
use url::Url;
use zip::CompressionMethod;
use zip::ZipWriter;
use zip::write::SimpleFileOptions;

use crate::config::DATABASE_URL_ENV;
use crate::data_config::{DataRuntimeConfig, default_api_info, default_server_config_path};
use crate::depth_data::{DepthMap, load_depth_map_from_dir};
use crate::models::{
    AlarmFlatRollRow, AlarmInfoSummaryRow, AlarmLooseCoilRow, AlarmTaperShapeRow, CoilDefectRow,
    CoilStateRow, CoilSummaryRow, ManualDefectRow, ManualDefectWrite, PlcDataRow,
    alarm_flat_roll_to_python_json, alarm_info_to_python_json, alarm_loose_coil_to_python_json,
    alarm_taper_shape_to_python_json, auto_defect_to_python_json, coil_check_to_python_json,
    coil_detail_to_python_json, coil_state_to_python_json, coil_summary_to_python_json,
    default_coil_check_json, defect_class_dict_to_python_json, defect_to_python_json,
    detail_alarm_flat_roll_to_python_json, detail_alarm_info_to_python_json,
    detail_alarm_loose_coil_to_python_json, detail_alarm_taper_shape_to_python_json,
    detail_defect_alias_to_python_json, detail_defect_to_python_json, grader_to_python_json,
    latest_coil_to_python_json, line_data_to_python_json, manual_defect_to_python_json,
    plc_curve_all_item_to_python_json, plc_curve_item_to_python_json, plc_data_to_python_json,
    point_data_to_python_json, round_mysql_float_for_python_json, taper_shape_point_to_python_json,
};
use crate::repository::CoilRepository;

const DEFAULT_SCAN3D_SCALE_X: f64 = 0.33693358302116394;
const DEFAULT_SCAN3D_SCALE_Y: f64 = 0.33693358302116394;
const DEFAULT_SCAN3D_SCALE_Z: f64 = 0.016229506582021713;
const MAX_RE_DETECTION_MESSAGE_COUNT: usize = 50;
const DEFAULT_COIL_INFO_DB_TIMEOUT_MS: u64 = 500;
const RUNTIME_INFO_CACHE_TTL: Duration = Duration::from_secs(30);
const HARDWARE_CACHE_TTL: Duration = Duration::from_secs(2);
const CAPTURE_STATUS_CACHE_TTL: Duration = Duration::from_millis(800);
const CAMERA_STATUS_CACHE_TTL: Duration = Duration::from_millis(800);
const CAPTURE_STATUS_TIMEOUT: Duration = Duration::from_millis(1200);
const CAMERA_STATUS_TIMEOUT: Duration = Duration::from_millis(800);
const XLSX_FLAT_ROLL_PIXEL_SCALE: f64 = 0.3415023386478424;
const API_BODY_LIMIT_BYTES: usize = 512 * 1024 * 1024;
const PYTHON_DETAIL_ROOT_KEYS: &[&str] = &[
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
];

#[derive(Clone, Debug)]
struct MaxDefectJsonFields {
    name: String,
    level: i32,
    surface: String,
}

impl Default for MaxDefectJsonFields {
    fn default() -> Self {
        Self {
            name: String::new(),
            level: 0,
            surface: String::new(),
        }
    }
}

#[derive(Clone, Debug)]
struct ReDetectionState {
    running: bool,
    total: i64,
    done: i64,
    pending: i64,
    progress: f64,
    error: String,
    queue: Vec<i64>,
    messages: Vec<Value>,
    generation: u64,
}

impl Default for ReDetectionState {
    fn default() -> Self {
        Self {
            running: false,
            total: 0,
            done: 0,
            pending: 0,
            progress: 0.0,
            error: String::new(),
            queue: Vec::new(),
            messages: Vec::new(),
            generation: 0,
        }
    }
}

impl ReDetectionState {
    fn started(
        from_id: i64,
        to_id: i64,
        queue: Vec<i64>,
        mut messages: Vec<Value>,
        generation: u64,
    ) -> Self {
        let start_id = from_id.min(to_id);
        let end_id = from_id.max(to_id);
        let total = i64::try_from(queue.len()).unwrap_or(i64::MAX);
        messages.push(re_detection_message(format!(
            "set_re_detection_by_coil_id start={start_id} end={end_id} count={total}"
        )));
        Self::trim_messages(&mut messages);
        Self {
            running: false,
            total,
            done: 0,
            pending: total,
            progress: 0.0,
            error: String::new(),
            queue,
            messages,
            generation,
        }
    }

    fn trim_messages(messages: &mut Vec<Value>) {
        if messages.len() > MAX_RE_DETECTION_MESSAGE_COUNT {
            let extra = messages.len() - MAX_RE_DETECTION_MESSAGE_COUNT;
            messages.drain(0..extra);
        }
    }

    fn append_message(&mut self, message: String) {
        self.messages.push(re_detection_message(message));
        Self::trim_messages(&mut self.messages);
    }

    fn refresh_progress(&mut self) {
        if self.total > 0 {
            self.done = self.done.clamp(0, self.total);
            self.pending = (self.total - self.done).max(0);
            self.progress = self.done as f64 / self.total as f64;
        } else {
            self.done = 0;
            self.pending = 0;
            self.progress = 0.0;
        }
    }

    fn consume_next_coil(&mut self) -> Option<i64> {
        if self.queue.is_empty() {
            self.running = false;
            self.refresh_progress();
            return None;
        }

        Some(self.queue.remove(0))
    }


    fn mark_done(&mut self) {
        if self.total > 0 {
            self.done = (self.done + 1).min(self.total);
        }
        self.pending = (self.total - self.done).max(0);
        self.progress = if self.total > 0 {
            self.done as f64 / self.total as f64
        } else {
            0.0
        };
        if self.queue.is_empty() || self.done >= self.total {
            self.running = false;
        }
    }

    fn to_json(&self) -> Value {
        json!({
            "total": self.total,
            "done": self.done,
            "pending": self.pending,
            "running": self.running,
            "error": self.error,
            "queue": self.queue,
            "messages": self.messages,
            "progress": self.progress,
        })
    }
}
fn re_detection_message(message: String) -> Value {
    json!({
        "Base": "ImageMosaicThread",
        "time": Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
        "msg": message,
        "level": "DEBUG",
    })
}

#[derive(Clone, Debug)]
struct ExternalCommandInvocation {
    executable: String,
    args: Vec<String>,
}

impl ExternalCommandInvocation {
    fn display(&self) -> String {
        if self.args.is_empty() {
            self.executable.clone()
        } else {
            format!("{} {}", self.executable, self.args.join(" "))
        }
    }
}

fn parse_command_invocation(raw_command: &str) -> Option<ExternalCommandInvocation> {
    let mut tokens = raw_command.split_whitespace().collect::<Vec<_>>();
    if tokens.is_empty() {
        return None;
    }
    let executable = tokens.remove(0).to_string();
    let args = tokens.into_iter().map(str::to_string).collect();
    Some(ExternalCommandInvocation { executable, args })
}

fn external_re_detection_command(start_id: i64, end_id: i64) -> Option<ExternalCommandInvocation> {
    if let Ok(raw_command) = std::env::var("RUST_API_REDETECTION_CMD") {
        let mut command = parse_command_invocation(&raw_command)?;
        command.args.push("--start-id".to_string());
        command.args.push(start_id.to_string());
        command.args.push("--end-id".to_string());
        command.args.push(end_id.to_string());
        return Some(command);
    }

    let Ok(script) = std::env::var("RUST_API_REDETECTION_SCRIPT") else {
        return None;
    };
    let script = script.trim().to_string();
    if script.is_empty() {
        return None;
    }
    if !FsPath::new(&script).exists() {
        return None;
    }

    Some(ExternalCommandInvocation {
        executable: std::env::var("RUST_API_PYTHON")
            .unwrap_or_else(|_| "python".to_string()),
        args: vec![
            "-u".to_string(),
            script,
            "--start-id".to_string(),
            start_id.to_string(),
            "--end-id".to_string(),
            end_id.to_string(),
        ],
    })
}

fn external_alg_test_command(
    target_path: &FsPath,
    output_path: &FsPath,
    run_options: &AlgTestRunOptions,
) -> Option<ExternalCommandInvocation> {
    if let Ok(raw_command) = std::env::var("RUST_API_ALG_TEST_CMD") {
        let mut command = parse_command_invocation(&raw_command)?;
        command.args.push("--model".to_string());
        command.args.push(run_options.model.clone());
        command.args.push("--target".to_string());
        command.args.push(target_path.to_string_lossy().to_string());
        command.args.push("--output".to_string());
        command.args.push(output_path.to_string_lossy().to_string());
        command.args.push("--threshold".to_string());
        command.args.push(run_options.threshold.to_string());
        command.args.push("--mode".to_string());
        command.args.push(run_options.mode.clone());
        command.args.push("--classify-save".to_string());
        command.args.push(run_options.classify_save.to_string());
        command.args.push("--save-label".to_string());
        command.args.push(run_options.save_label.to_string());
        command.args.push("--prioritize".to_string());
        command.args.push(run_options.prioritize.to_string());
        return Some(command);
    }

    let Ok(script) = std::env::var("RUST_API_ALG_TEST_SCRIPT") else {
        return None;
    };
    let script = script.trim().to_string();
    if script.is_empty() || !FsPath::new(&script).exists() {
        return None;
    }

    Some(ExternalCommandInvocation {
        executable: std::env::var("RUST_API_PYTHON")
            .unwrap_or_else(|_| "python".to_string()),
        args: vec![
            "-u".to_string(),
            script,
            "--model".to_string(),
            run_options.model.clone(),
            "--target".to_string(),
            target_path.to_string_lossy().to_string(),
            "--output".to_string(),
            output_path.to_string_lossy().to_string(),
            "--threshold".to_string(),
            run_options.threshold.to_string(),
            "--mode".to_string(),
            run_options.mode.clone(),
            "--classify-save".to_string(),
            run_options.classify_save.to_string(),
            "--save-label".to_string(),
            run_options.save_label.to_string(),
            "--prioritize".to_string(),
            run_options.prioritize.to_string(),
        ],
    })
}

#[derive(Clone, Debug)]
struct AlgTestRunOptions {
    model: String,
    model_type: String,
    mode: String,
    threshold: f64,
    classify_save: bool,
    save_label: bool,
    prioritize: bool,
}

impl AlgTestRunOptions {
    fn to_payload_metadata(&self) -> Value {
        json!({
            "model": &self.model,
            "model_type": &self.model_type,
            "mode": &self.mode,
            "threshold": self.threshold,
            "options": {
                "classify_save": self.classify_save,
                "save_label": self.save_label,
                "prioritize": self.prioritize,
            },
        })
    }
}

#[derive(Clone, Debug)]
struct AlgTestSummary {
    normal: usize,
    abnormal: usize,
    skipped: usize,
    empty: usize,
}

impl Default for AlgTestSummary {
    fn default() -> Self {
        Self {
            normal: 0,
            abnormal: 0,
            skipped: 0,
            empty: 0,
        }
    }
}

impl AlgTestSummary {
    fn add_normal(&mut self, empty: bool) {
        self.normal = self.normal.saturating_add(1);
        if empty {
            self.empty = self.empty.saturating_add(1);
        }
    }

    fn add_abnormal(&mut self) {
        self.abnormal = self.abnormal.saturating_add(1);
    }

    fn add_skipped(&mut self) {
        self.skipped = self.skipped.saturating_add(1);
    }
}

#[derive(Clone, Debug)]
struct AlgTestState {
    current_task_id: Option<String>,
    stop_requested: bool,
    last_payload: Value,
}

impl Default for AlgTestState {
    fn default() -> Self {
        Self {
            current_task_id: None,
            stop_requested: false,
            last_payload: json!({
                "task_id": null,
                "status": "idle",
            }),
        }
    }
}

impl AlgTestState {
    fn start(&mut self) -> Result<String, String> {
        if self.current_task_id.is_some() {
            return Err("已有算法测试任务在执行".to_string());
        }

        let task_id = new_alg_task_id();
        self.current_task_id = Some(task_id.clone());
        self.stop_requested = false;
        let summary = AlgTestSummary::default();
        self.last_payload = alg_test_progress_payload(
            Some(&task_id),
            "初始化",
            0,
            0,
            0,
            0,
            "任务已启动",
            false,
            Instant::now(),
            None,
            &summary,
        );
        Ok(task_id)
    }

    fn stop(&mut self, task_id: Option<&str>) -> Result<Value, String> {
        let Some(current_task_id) = self.current_task_id.clone() else {
            return Ok(json!({"ok": true, "message": "当前无任务"}));
        };
        if let Some(task_id) = task_id {
            if task_id != current_task_id {
                return Err("任务 ID 不匹配".to_string());
            }
        }
        self.stop_requested = true;
        let summary = AlgTestSummary::default();
        self.last_payload = alg_test_progress_payload(
            Some(&current_task_id),
            "已请求停止",
            0,
            0,
            0,
            0,
            "停止指令已发送",
            false,
            Instant::now(),
            None,
            &summary,
        );
        Ok(json!({"ok": true, "message": "停止指令已发送"}))
    }

    fn should_stop(&self, task_id: &str) -> bool {
        self.current_task_id.as_deref() == Some(task_id) && self.stop_requested
    }

    fn update(&mut self, task_id: &str, payload: Value, finished: bool) {
        if self.current_task_id.as_deref() != Some(task_id) && !finished {
            return;
        }
        self.last_payload = payload;
        if finished {
            self.current_task_id = None;
            self.stop_requested = false;
        }
    }
}

#[derive(Clone, Debug)]
struct Area2dState {
    clip_configs: serde_json::Map<String, Value>,
    queued: Vec<(i64, String)>,
    last_scan_time: f64,
    last_scan_start_time: f64,
    last_scan_error: String,
    last_candidates: Vec<i64>,
    last_scan_queued: Vec<(i64, String)>,
    skipped_processed: usize,
    skipped_incomplete: usize,
    skipped_queue_full: usize,
    queue_failures: Vec<i64>,
}

impl Default for Area2dState {
    fn default() -> Self {
        Self {
            clip_configs: serde_json::Map::new(),
            queued: Vec::new(),
            last_scan_time: 0.0,
            last_scan_start_time: 0.0,
            last_scan_error: String::new(),
            last_candidates: Vec::new(),
            last_scan_queued: Vec::new(),
            skipped_processed: 0,
            skipped_incomplete: 0,
            skipped_queue_full: 0,
            queue_failures: Vec::new(),
        }
    }
}

#[derive(Clone, Debug)]
struct AreaScanSettings {
    scan_interval: usize,
    scan_limit: usize,
    max_queue_depth: usize,
    min_images_per_camera: usize,
    max_camera_count_skew: usize,
}

#[derive(Clone, Debug)]
struct AreaScanCamera {
    folder: PathBuf,
    loss_num: usize,
    max_len: usize,
}

#[derive(Clone, Debug)]
struct AreaScanSurface {
    key: String,
    cameras: Vec<AreaScanCamera>,
    save_folder: PathBuf,
    clip_mode: String,
    clip_fixed: u32,
    clip_dynamic_a: f64,
    clip_dynamic_b: f64,
    clip_dynamic_c: f64,
    clip_dynamic_offset: u32,
}

impl AreaScanSurface {
    fn clip_config_json(&self) -> Value {
        json!({
            "mode": self.clip_mode.clone(),
            "fixed": self.clip_fixed,
            "a": self.clip_dynamic_a,
            "b": self.clip_dynamic_b,
            "c": self.clip_dynamic_c,
            "offset": self.clip_dynamic_offset,
        })
    }
}

impl Area2dState {
    fn set_clip_config(&mut self, surface_key: String, clip_config: Value) {
        self.clip_configs.insert(surface_key, clip_config);
    }

    fn enqueue(&mut self, coil_id: i64, surface_keys: &[String]) {
        for surface_key in surface_keys {
            self.queued.push((coil_id, surface_key.clone()));
        }
    }

    fn complete(&mut self, coil_id: i64, surface_keys: &[String]) {
        self.queued = self
            .queued
            .iter()
            .filter_map(|(queued_coil_id, queued_surface)| {
                if *queued_coil_id != coil_id {
                    return Some((*queued_coil_id, queued_surface.clone()));
                }
                let remaining = area_queue_entry_remaining_surfaces(queued_surface, surface_keys);
                (!remaining.is_empty()).then_some((*queued_coil_id, remaining.join(",")))
            })
            .collect();
    }

    fn scan(&mut self) {
        let settings = area_scan_settings();
        let now = unix_timestamp_f64();
        self.last_scan_start_time = now;
        self.last_scan_error.clear();
        self.last_candidates.clear();
        self.last_scan_queued.clear();
        self.skipped_processed = 0;
        self.skipped_incomplete = 0;
        self.skipped_queue_full = 0;
        self.queue_failures.clear();

        if let Some(config_path) = area_join_config_path() {
            match read_area_scan_surfaces(&config_path) {
                Ok(surfaces) => {
                    let candidates = area_source_coil_ids(&surfaces, settings.scan_limit);
                    self.last_candidates = candidates.iter().copied().take(20).collect();
                    for coil_id in candidates {
                        if self.queued.len() >= settings.max_queue_depth {
                            self.skipped_queue_full += 1;
                            break;
                        }

                        let mut incomplete = Vec::new();
                        let mut missing_output = Vec::new();
                        for surface in &surfaces {
                            if !area_surface_complete(surface, coil_id, &settings) {
                                incomplete.push(surface.key.clone());
                                continue;
                            }
                            if !area_surface_processed(surface, coil_id) {
                                missing_output.push(surface.key.clone());
                            }
                        }

                        if missing_output.is_empty() {
                            if incomplete.is_empty() {
                                self.skipped_processed += 1;
                            } else {
                                self.skipped_incomplete += 1;
                            }
                            continue;
                        }

                        let reason = missing_output.join(",");
                        self.queued.push((coil_id, reason.clone()));
                        self.last_scan_queued.push((coil_id, reason));
                    }
                }
                Err(error) => {
                    self.last_scan_error = error;
                }
            }
        }

        self.last_scan_time = unix_timestamp_f64();
    }

    fn status_json(
        &self,
        surface_keys: &[String],
        configured_clip_configs: &serde_json::Map<String, Value>,
    ) -> Value {
        let settings = area_scan_settings();
        let join_queue_size = self.queued.len();
        let mut queue_depths = serde_json::Map::new();
        queue_depths.insert("join".to_string(), json!(join_queue_size));
        let mut surfaces = serde_json::Map::new();
        for surface_key in surface_keys {
            let queue_size = self
                .queued
                .iter()
                .filter(|(_, key)| area_queue_entry_contains_surface(key, surface_key))
                .count();
            let last_coil_id = self
                .queued
                .iter()
                .rev()
                .find(|(_, key)| area_queue_entry_contains_surface(key, surface_key))
                .map(|(coil_id, _)| *coil_id);
            queue_depths.insert(surface_key.clone(), json!(queue_size));
            let mut surface_status = serde_json::Map::new();
            surface_status.insert("queueSize".to_string(), json!(queue_size));
            surface_status.insert("lastCoilId".to_string(), json!(last_coil_id));
            if let Some(clip_config) = self
                .clip_configs
                .get(surface_key)
                .cloned()
                .or_else(|| configured_clip_configs.get(surface_key).cloned())
            {
                surface_status.insert("clipConfig".to_string(), clip_config);
            }
            surfaces.insert(surface_key.clone(), Value::Object(surface_status));
        }

        json!({
            "status": "ok",
            "scanner": {
                "enabled": true,
                "scanInterval": settings.scan_interval,
                "scanLimit": settings.scan_limit,
                "maxQueueDepth": settings.max_queue_depth,
                "minImagesPerCamera": settings.min_images_per_camera,
                "maxCameraCountSkew": settings.max_camera_count_skew,
                "scanRunning": false,
                "lastScanStartTime": self.last_scan_start_time,
                "lastScanTime": self.last_scan_time,
                "lastScanError": self.last_scan_error.clone(),
                "lastCandidates": self.last_candidates.clone(),
                "queued": self.last_scan_queued.iter().take(20).map(|(coil_id, reason)| {
                    json!({"coil_id": coil_id, "reason": reason})
                }).collect::<Vec<_>>(),
                "skippedProcessed": self.skipped_processed,
                "skippedIncomplete": self.skipped_incomplete,
                "skippedQueueFull": self.skipped_queue_full,
                "queueFailures": self.queue_failures.iter().copied().take(20).collect::<Vec<_>>(),
            },
            "joinQueueSize": join_queue_size,
            "queueDepths": Value::Object(queue_depths),
            "surfaces": Value::Object(surfaces),
        })
    }
}

fn area_queue_entry_contains_surface(entry: &str, surface_key: &str) -> bool {
    entry
        .split(',')
        .map(str::trim)
        .any(|part| part.eq_ignore_ascii_case(surface_key))
}

fn area_queue_entry_surface_keys(entry: &str) -> Vec<String> {
    entry
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .map(|part| part.to_ascii_uppercase())
        .collect()
}

fn area_queue_entry_remaining_surfaces(
    entry: &str,
    completed_surface_keys: &[String],
) -> Vec<String> {
    entry
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .filter(|part| {
            !completed_surface_keys
                .iter()
                .any(|surface_key| part.eq_ignore_ascii_case(surface_key))
        })
        .map(str::to_string)
        .collect()
}

#[derive(Clone)]
pub struct ApiState {
    repository: Arc<dyn CoilRepository>,
    test_mode: Option<TestModeConfig>,
    data_config: Option<DataRuntimeConfig>,
    control_config: Arc<Mutex<Option<Value>>>,
    re_detection: Arc<Mutex<ReDetectionState>>,
    server_state: Arc<Mutex<Vec<Value>>>,
    alg_test: Arc<Mutex<AlgTestState>>,
    area_2d: Arc<Mutex<Area2dState>>,
    plc_runtime: Arc<Mutex<PlcRuntimeState>>,
    runtime_info_cache: Arc<Mutex<Option<TimedJson>>>,
    hardware_cache: Arc<Mutex<Option<TimedJson>>>,
    capture_status_cache: Arc<Mutex<Option<TimedJson>>>,
    camera_adjust_cache: Arc<Mutex<Option<TimedJson>>>,
    camera_alarm_cache: Arc<Mutex<Option<TimedJson>>>,
}

#[derive(Clone, Debug)]
struct PlcRuntimeState {
    ip: String,
    rack: i64,
    slot: i64,
    connected: bool,
}

#[derive(Clone, Debug)]
struct TimedJson {
    value: Value,
    expires_at: Instant,
}

fn cached_json_get(cache: &Arc<Mutex<Option<TimedJson>>>) -> Option<Value> {
    let Ok(guard) = cache.lock() else {
        return None;
    };
    let cached = guard.as_ref()?;
    if Instant::now() <= cached.expires_at {
        Some(cached.value.clone())
    } else {
        None
    }
}

fn cached_json_put(cache: &Arc<Mutex<Option<TimedJson>>>, value: Value, ttl: Duration) {
    if let Ok(mut guard) = cache.lock() {
        *guard = Some(TimedJson {
            value,
            expires_at: Instant::now() + ttl,
        });
    }
}

fn cached_json<F>(cache: &Arc<Mutex<Option<TimedJson>>>, ttl: Duration, compute: F) -> Value
where
    F: FnOnce() -> Value,
{
    if let Some(value) = cached_json_get(cache) {
        return value;
    }
    let value = compute();
    cached_json_put(cache, value.clone(), ttl);
    value
}

fn profiling_enabled() -> bool {
    runtime_env_flag("RUST_API_PROFILE_ALL")
}

fn profile_slow_threshold() -> Duration {
    std::env::var("RUST_API_PROFILE_SLOW_MS")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .map(Duration::from_millis)
        .unwrap_or_else(|| Duration::from_millis(50))
}

fn profile_stage(endpoint: &str, stage: &str, started: Instant, context: &str) {
    let elapsed = started.elapsed();
    if profiling_enabled() || elapsed >= profile_slow_threshold() {
        info!(
            target: "rust_api_service::profile",
            endpoint = endpoint,
            stage = stage,
            elapsed_ms = elapsed.as_secs_f64() * 1000.0,
            context = context,
            "api stage elapsed"
        );
    }
}

impl ApiState {
    pub fn new(repository: Arc<dyn CoilRepository>) -> Self {
        Self {
            repository,
            test_mode: None,
            data_config: None,
            control_config: Arc::new(Mutex::new(None)),
            re_detection: Arc::new(Mutex::new(ReDetectionState::default())),
            server_state: Arc::new(Mutex::new(Vec::new())),
            alg_test: Arc::new(Mutex::new(AlgTestState::default())),
            area_2d: Arc::new(Mutex::new(Area2dState::default())),
            plc_runtime: Arc::new(Mutex::new(read_plc_runtime_state())),
            runtime_info_cache: Arc::new(Mutex::new(None)),
            hardware_cache: Arc::new(Mutex::new(None)),
            capture_status_cache: Arc::new(Mutex::new(None)),
            camera_adjust_cache: Arc::new(Mutex::new(None)),
            camera_alarm_cache: Arc::new(Mutex::new(None)),
        }
    }

    pub fn with_test_mode(mut self, test_mode: TestModeConfig) -> Self {
        self.test_mode = Some(test_mode);
        self
    }

    pub fn with_data_config(mut self, data_config: DataRuntimeConfig) -> Self {
        cleanup_legacy_area_tile_cache_on_startup(&data_config);
        self.data_config = Some(data_config);
        self
    }

    fn control_config_snapshot(&self) -> Value {
        match self.control_config.lock() {
            Ok(mut config) => {
                if config.is_none() {
                    *config = Some(read_control_config());
                }
                config.clone().unwrap_or_else(|| json!({}))
            }
            Err(_) => json!({}),
        }
    }

    fn merge_control_config(&self, payload: Value) {
        let Value::Object(payload) = payload else {
            return;
        };
        if let Ok(mut config) = self.control_config.lock() {
            if config.is_none() {
                *config = Some(read_control_config());
            }
            if !matches!(config.as_ref(), Some(Value::Object(_))) {
                *config = Some(json!({}));
            }
            if let Some(Value::Object(current)) = config.as_mut() {
                current.extend(payload);
            }
        }
    }

    fn set_control_property(&self, key: String, value: String) {
        if let Ok(mut config) = self.control_config.lock() {
            if config.is_none() {
                *config = Some(read_control_config());
            }
            if !matches!(config.as_ref(), Some(Value::Object(_))) {
                *config = Some(json!({}));
            }
            if let Some(Value::Object(current)) = config.as_mut() {
                current.insert(key, Value::String(value));
            }
        }
    }

    fn re_detection_status(&self) -> Value {
        self.re_detection
            .lock()
            .map(|status| status.to_json())
            .unwrap_or_else(|_| json!({"error": "reDetection status lock poisoned"}))
    }

    fn plc_info_body(&self) -> Value {
        let Ok(state) = self.plc_runtime.lock() else {
            return plc_info_body_default();
        };
        plc_info_body_from_state(&state)
    }

    fn set_plc_connection(&self, ip: String, rack: i64, slot: i64) {
        if let Ok(mut state) = self.plc_runtime.lock() {
            state.ip = ip;
            state.rack = rack;
            state.slot = slot;
            state.connected = true;
        }
    }

    fn plc_value_read(&self, addr: &str, type_str: &str, length: i64) -> Result<Value, Response> {
        if length < 0 {
            return Err(python_internal_server_error_response());
        }
        let requested = usize::try_from(length).map_err(|_| python_internal_server_error_response())?;
        let Ok(state) = self.plc_runtime.lock() else {
            return Err(python_internal_server_error_response());
        };
        let raw = plc_fake_read_bytes(&state, addr, requested, type_str);
        plc_parse_plc_value(type_str, &raw).ok_or_else(python_internal_server_error_response)
    }

    fn runtime_info_value(&self) -> Value {
        cached_json(&self.runtime_info_cache, RUNTIME_INFO_CACHE_TTL, runtime_info_uncached)
    }

    fn hardware_value(&self) -> Value {
        cached_json(&self.hardware_cache, HARDWARE_CACHE_TTL, hardware_info_uncached)
    }

    async fn capture_status_value(&self) -> Value {
        if let Some(value) = cached_json_get(&self.capture_status_cache) {
            return value;
        }
        let value = capture_status_value_uncached().await;
        cached_json_put(&self.capture_status_cache, value.clone(), CAPTURE_STATUS_CACHE_TTL);
        value
    }

    async fn camera_adjust_value(&self) -> Value {
        if let Some(value) = cached_json_get(&self.camera_adjust_cache) {
            return value;
        }
        let value = camera_adjust_value_uncached().await;
        cached_json_put(&self.camera_adjust_cache, value.clone(), CAMERA_STATUS_CACHE_TTL);
        value
    }

    async fn camera_alarm_value(&self) -> Value {
        if let Some(value) = cached_json_get(&self.camera_alarm_cache) {
            return value;
        }
        let value = camera_alarm_value_uncached().await;
        cached_json_put(&self.camera_alarm_cache, value.clone(), CAMERA_STATUS_CACHE_TTL);
        value
    }

    async fn start_re_detection(&self, from_id: i64, to_id: i64) -> Value {
        let start_id = from_id.min(to_id);
        let end_id = from_id.max(to_id);
        let queue = match self
            .repository
            .search_coils_by_id_range(start_id, end_id)
            .await
        {
            Ok(rows) => rows.into_iter().map(|row| row.id).collect::<Vec<_>>(),
            Err(error) => {
                return json!({
                    "error": error.to_string(),
                    "running": false,
                    "total": 0,
                    "done": 0,
                    "pending": 0,
                    "queue": [],
                    "messages": [],
                    "progress": 0.0,
                });
            }
        };
        match self.re_detection.lock() {
            Ok(mut status) => {
                let generation = status.generation.saturating_add(1);
                *status = ReDetectionState::started(start_id, end_id, queue, status.messages.clone(), generation);
                let response = status.to_json();
                let repository = self.repository.clone();
                let re_detection = self.re_detection.clone();
                tokio::spawn(async move {
                    run_re_detection_worker(repository, re_detection, generation, start_id, end_id).await;
                });
                response
            }
            Err(_) => json!({"error": "reDetection status lock poisoned"}),
        }
    }

    async fn queue_re_detection(&self, from_id: i64, to_id: i64) -> Value {
        let start_id = from_id.min(to_id);
        let end_id = from_id.max(to_id);
        let queue = match self
            .repository
            .search_coils_by_id_range(start_id, end_id)
            .await
        {
            Ok(rows) => rows.into_iter().map(|row| row.id).collect::<Vec<_>>(),
            Err(error) => {
                return json!({
                    "error": error.to_string(),
                    "running": false,
                    "total": 0,
                    "done": 0,
                    "pending": 0,
                    "queue": [],
                    "messages": [],
                    "progress": 0.0,
                });
            }
        };
        match self.re_detection.lock() {
            Ok(mut status) => {
                let generation = status.generation.saturating_add(1);
                *status = ReDetectionState::started(
                    start_id,
                    end_id,
                    queue,
                    status.messages.clone(),
                    generation,
                );
                status.to_json()
            }
            Err(_) => json!({"error": "reDetection status lock poisoned"}),
        }
    }

    fn server_state_snapshot(&self) -> Value {
        let mut items = self
            .server_state
            .lock()
            .map(|items| items.clone())
            .unwrap_or_else(|_| Vec::new());

        if let Ok(re_detection) = self.re_detection.lock() {
            if re_detection.total > 0 || re_detection.running {
                let level = if re_detection.error.is_empty() {
                    if re_detection.running { 2 } else { 1 }
                } else {
                    3
                };

                let value = if re_detection.running {
                    "重识别处理中"
                } else if re_detection.done >= re_detection.total && re_detection.total > 0 {
                    "重识别完成"
                } else if re_detection.total > 0 {
                    "重识别待处理"
                } else {
                    "重识别空闲"
                };

                items.push(json!({
                    "key": "reDetection",
                    "title": "重识别",
                    "value": value,
                    "msg": format!(
                        "total={} done={} pending={}",
                        re_detection.total,
                        re_detection.done,
                        re_detection.pending
                    ),
                    "level": level,
                }));
            }
        }

        Value::Array(items)
    }
    fn alg_test_snapshot(&self) -> Value {
        self.alg_test
            .lock()
            .map(|state| state.last_payload.clone())
            .unwrap_or_else(|_| json!({"task_id": null, "status": "idle"}))
    }

    fn test_mode_coil_fallback(&self) -> Option<Value> {
        let test_mode = self.test_mode.as_ref()?;
        if !test_mode.enabled || !test_mode.data_available() {
            return None;
        }
        Some(test_mode.coil_item())
    }

    fn test_mode_for_coil(&self, coil_id: i64) -> Option<&TestModeConfig> {
        let test_mode = self.test_mode.as_ref()?;
        if test_mode.enabled && test_mode.coil_id == coil_id && test_mode.data_available() {
            return Some(test_mode);
        }
        None
    }

    fn test_mode_data_fallback(&self) -> Option<&TestModeConfig> {
        let test_mode = self.test_mode.as_ref()?;
        if test_mode.enabled && test_mode.data_available() {
            return Some(test_mode);
        }
        None
    }
}

#[derive(Clone, Debug)]
pub struct TestModeConfig {
    pub enabled: bool,
    pub coil_id: i64,
    pub data_dir: PathBuf,
    pub project_root: PathBuf,
}

impl TestModeConfig {
    pub fn from_env() -> Self {
        let project_root = default_project_root();
        let coil_id = std::env::var("API_TESTDATA_COIL_ID")
            .ok()
            .and_then(|value| value.parse::<i64>().ok())
            .unwrap_or(193113);
        let data_dir = std::env::var("API_TESTDATA_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| default_testdata_dir(&project_root, coil_id));

        Self {
            enabled: env_flag("API_DEVELOPER_MODE") || config_file_test_mode_enabled(&project_root),
            coil_id,
            data_dir,
            project_root,
        }
    }

    fn data_available(&self) -> bool {
        if !self.data_dir.exists() {
            return false;
        }
        if has_any_file(&self.data_dir, &["3D.npz", "3D.npy"]) {
            return true;
        }
        ["S", "L"]
            .iter()
            .any(|surface| has_any_file(&self.data_dir.join(surface), &["3D.npz", "3D.npy"]))
    }

    fn data_has(&self) -> Option<Value> {
        if !self.enabled || !self.data_available() {
            return None;
        }

        let mut result = serde_json::Map::new();
        for surface in ["S", "L"] {
            let surface_dir = self.surface_asset_dir(surface);
            result.insert(
                surface.to_string(),
                json!({
                    "3D": has_any_file(&surface_dir, &["3D.npz", "3D.npy"]),
                    "MESH": has_python_default_mesh(&surface_dir),
                    "JPG": has_named_image(&surface_dir, "GRAY"),
                    "2D": has_named_image(&surface_dir, "AREA"),
                }),
            );
        }

        Some(Value::Object(result))
    }

    fn coil_info(&self, surface: &str) -> Option<Value> {
        let surface = surface.to_ascii_uppercase();
        let surface_dir = self.surface_asset_dir(&surface);
        if !surface_dir.exists() {
            return None;
        }

        let mut info = read_json_object(&surface_dir.join("data.json")).unwrap_or_default();
        let depth_map = self.depth_map(&surface);
        let (height, width) = depth_map
            .as_ref()
            .map(|map| (map.height(), map.width()))
            .unwrap_or_else(|| shape_from_info(&info));
        let median_3d = depth_map
            .as_ref()
            .map(|depth_map| depth_map.median_nonzero())
            .unwrap_or(0.0);
        let circle_config = info.get("circleConfig").cloned().unwrap_or_else(|| {
            json!({
                "inner_circle": {
                    "circlex": [width / 2, height / 2],
                    "ellipse": []
                }
            })
        });

        info.insert(
            "coilId".to_string(),
            info.get("coilId")
                .cloned()
                .unwrap_or_else(|| Value::String(self.coil_id.to_string())),
        );
        info.insert("surface".to_string(), Value::String(surface));
        info.insert("width".to_string(), json!(width));
        info.insert("height".to_string(), json!(height));
        info.insert(
            "scan3dCoordinateScaleX".to_string(),
            json!(DEFAULT_SCAN3D_SCALE_X),
        );
        info.insert(
            "scan3dCoordinateScaleY".to_string(),
            json!(DEFAULT_SCAN3D_SCALE_Y),
        );
        info.insert(
            "scan3dCoordinateScaleZ".to_string(),
            json!(DEFAULT_SCAN3D_SCALE_Z),
        );
        info.insert("scan3dCoordinateOffsetZ".to_string(), json!(0));
        info.insert("median_3d".to_string(), json!(median_3d));
        info.insert(
            "median_3d_mm".to_string(),
            json!(median_3d * DEFAULT_SCAN3D_SCALE_Z),
        );
        info.insert("colorFromValue_mm".to_string(), json!(-30));
        info.insert("colorToValue_mm".to_string(), json!(30));
        info.insert("circleConfig".to_string(), circle_config);

        Some(Value::Object(info))
    }

    fn height_segments(&self, surface: &str, x1: i32, y1: i32, x2: i32, y2: i32) -> Option<Value> {
        if let Some(depth_map) = self.depth_map(surface) {
            let surface_dir = self.surface_asset_dir(surface);
            let mask = load_mask_image(&surface_dir);
            return Some(real_height_segments(
                &depth_map,
                mask.as_ref(),
                x1,
                y1,
                x2,
                y2,
            ));
        }

        let (height, width) = self.surface_dimensions(surface)?;
        if height <= 0 || width <= 0 {
            return Some(Value::Array(Vec::new()));
        }

        let start = clamp_point(x1, y1, width, height);
        let end = clamp_point(x2, y2, width, height);
        let dx = end.0 - start.0;
        let dy = end.1 - start.1;
        let steps = dx.abs().max(dy.abs()).max(1);
        let mut points = Vec::new();

        for index in 0..=steps {
            let x = start.0 + div_round(dx * index, steps);
            let y = start.1 + div_round(dy * index, steps);
            points.push(json!([x, y, synthetic_height_value(x, y)]));
        }

        Some(json!([{
            "pointL": [start.0, start.1],
            "pointR": [end.0, end.1],
            "points": points,
        }]))
    }

    fn height_point(&self, surface: &str, x: i32, y: i32) -> Option<Value> {
        if let Some(depth_map) = self.depth_map(surface) {
            return Some(
                depth_map
                    .value_i32(x, y)
                    .map_or_else(|| json!("error"), |value| json!(value)),
            );
        }

        let (height, width) = self.surface_dimensions(surface)?;
        if x < 0 || y < 0 || x >= width || y >= height {
            return Some(json!("error"));
        }
        Some(json!(synthetic_height_value(x, y)))
    }

    fn render_image(&self, surface: &str, query: &RenderQuery) -> Option<RenderedImage> {
        let surface_dir = self.surface_asset_dir(surface);
        render_image_from_surface_dir(&surface_dir, query)
    }

    fn surface_dimensions(&self, surface: &str) -> Option<(i32, i32)> {
        let surface_dir = self.surface_asset_dir(surface);
        if !surface_dir.exists() {
            return None;
        }
        let info = read_json_object(&surface_dir.join("data.json")).unwrap_or_default();
        Some(shape_from_info(&info))
    }

    fn depth_map(&self, surface: &str) -> Option<Arc<DepthMap>> {
        load_depth_map_from_dir(&self.surface_asset_dir(surface))
    }

    fn surface_asset_dir(&self, surface: &str) -> PathBuf {
        let surface_dir = self.data_dir.join(surface.to_ascii_uppercase());
        if surface_dir.exists() {
            return surface_dir;
        }
        self.data_dir.clone()
    }

    fn coil_item(&self) -> Value {
        let now = Local::now();
        let date_value = json!({
            "year": now.year(),
            "month": now.month(),
            "day": now.day(),
            "weekday": now.weekday().num_days_from_monday(),
            "hour": now.hour(),
            "minute": now.minute(),
            "second": now.second(),
        });
        let msg = relative_path_text(&self.data_dir, &self.project_root);
        let alarm_info = json!({
            "S": test_mode_alarm("S"),
            "L": test_mode_alarm("L"),
        });

        json!({
            "Id": self.coil_id,
            "SecondaryCoilId": self.coil_id,
            "CoilNo": self.coil_id.to_string(),
            "CoilType": "TestData",
            "CoilInside": "",
            "CoilDia": "",
            "Thickness": "",
            "Width": "",
            "Weight": "",
            "ActWidth": "",
            "CheckStatus": 0,
            "DefectCountS": 0,
            "DefectCountL": 0,
            "Status_L": 0,
            "Status_S": 0,
            "Grade": 0,
            "Msg": msg,
            "NextInfo": "测试模式",
            "NextCode": "",
            "hasCoil": true,
            "hasAlarmInfo": true,
            "AlarmInfo": alarm_info,
            "defects": {},
            "childrenCoilCheck": [],
            "CreateTime": date_value,
            "DetectionTime": date_value,
            "DateTime": date_value,
        })
    }
}

pub fn build_app(state: ApiState) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/currentCoil", get(current_coil))
        .route("/openapi.json", get(openapi_json))
        .route("/docs", get(swagger_docs))
        .route("/docs/oauth2-redirect", get(swagger_oauth2_redirect))
        .route("/docs/oauth2-redirect.html", get(swagger_oauth2_redirect))
        .route("/redoc", get(redoc_docs))
        .route("/static/swagger-ui-bundle.js", get(swagger_ui_bundle_js))
        .route("/static/swagger-ui.css", get(swagger_ui_css))
        .route("/static/redoc.standalone.js", get(redoc_standalone_js))
        .route("/info", get(info))
        .route("/plc/info", get(plc_info))
        .route("/plc/info/", get(plc_info))
        .route("/plc/connect/{plc_ip}/{rack}/{slot}", get(plc_connect))
        .route("/plc/get/{addr}/{type_str}/{length}", get(plc_get))
        .route("/database_info", get(database_info))
        .route("/defectDict", get(defect_dict))
        .route("/defectDictAll", get(defect_dict_all))
        .route("/defectClasses", get(defect_dict))
        .route("/setDefectDict", post(set_defect_dict))
        .route("/grader_list", get(grader_list))
        .route(
            "/coil_list_value_change_keys",
            get(coil_list_value_change_keys),
        )
        .route("/health", get(health))
        .route("/version", get(version))
        .route("/delay", get(delay))
        .route("/software_update/manifest", get(software_update_manifest))
        .route("/updates/{file_name}", get(software_update_package))
        .route("/download_test", get(download_test))
        .route("/speedtest/download", get(speedtest_download))
        .route("/speedtest/upload", post(speedtest_upload))
        .route("/runtime_info", get(runtime_info))
        .route("/control/config", get(control_config))
        .route("/control/set_config", post(set_control_config))
        .route("/control/set_property", get(set_control_property))
        .route("/hardware", get(hardware))
        .route("/capture_status", get(capture_status))
        .route("/camera_adjust", get(camera_adjust))
        .route("/camera_adjust/{camera_key}", post(set_camera_adjustment))
        .route(
            "/camera_adjust/{camera_key}/reconnect",
            post(reconnect_camera_adjustment),
        )
        .route("/camera/status", get(capture_camera_status_default))
        .route("/camera/params", post(capture_camera_set_params))
        .route("/camera/reconnect", post(capture_camera_reconnect))
        .route("/cameras", get(cameras_status))
        .route("/cameras/{camera_key}/status", get(capture_camera_status))
        .route("/cameras/{camera_key}/files", get(capture_camera_files))
        .route("/cameras/{camera_key}/params", post(cameras_set_params))
        .route("/cameras/{camera_key}/reconnect", post(cameras_reconnect))
        .route("/capture/status", get(capture_status_proxy))
        .route("/capture/files", get(capture_files))
        .route("/getListenerAddFile", get(capture_listener_add_file))
        .route("/cameraAlarm", get(camera_alarm))
        .route("/cameraData/{coil_id}/{camera_key}", get(camera_data))
        .route(
            "/settings/test_mode",
            get(settings_test_mode).post(update_settings_test_mode),
        )
        .route("/settings/test_mode_status", get(settings_test_mode_status))
        .route("/data_has/{coil_id}", get(data_has))
        .route("/coilInfo/{coil_id}/{surface_key}", get(coil_info))
        .route("/coilData/heightData/{surface_key}/{coil_id}", get(height_data))
        .route(
            "/coilData/heightPoint/{surface_key}/{coil_id}",
            get(height_point),
        )
        .route("/coilData/Render/{surfaceKey}/{coil_id}", get(render_image))
        .route("/coilData/Area/{surface_key}/{coil_id}", get(area_image))
        .route("/coilData/Error/{surface_key}/{coil_id}", get(error_image))
        .route(
            "/image/preview/{surface_key}/{coil_id}/{type_}",
            get(image_preview),
        )
        .route(
            "/image/source/{surface_key}/{coil_id}/{type_}",
            get(image_source),
        )
        .route("/image/area/{surface_key}/{coil_id}", get(image_area))
        .route(
            "/image/area/{surface_key}/{coil_id}/{type_}",
            get(image_area_typed),
        )
        .route(
            "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
            get(classifier_image),
        )
        .route(
            "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
            get(defect_image),
        )
        .route("/clipMaxImage/{coil_id}/{key}", get(clip_max_image))
        .route("/ws/coilData/heightPoint", get(ws_height_point))
        .route("/reDetection/status", get(re_detection_status))
        .route(
            "/reDetection/start/{from_id}/{to_id}",
            get(re_detection_start),
        )
        .route("/ws/reDetection", get(ws_re_detection))
        .route("/getServerState", get(get_server_state))
        .route("/ws/DetectionState", get(ws_detection_state))
        .route("/alg_2d/models", get(alg_2d_models))
        .route("/alg_2d/test/start", post(alg_2d_test_start))
        .route("/alg_2d/test/stop", post(alg_2d_test_stop))
        .route("/ws/alg_2d/test/progress", get(ws_alg_2d_test_progress))
        .route("/clip_config", post(set_area_clip_config))
        .route("/area/rejoin", post(rejoin_area))
        .route("/area/status", get(area_status))
        .route("/area/scan", post(area_scan))
        .route("/save_to_sql/{*sql_file}", get(save_to_sql))
        .route(
            "/backupImageTask/{from_id}/{to_id}/{*save_folder}",
            get(backup_image_task),
        )
        .route("/ws/backupImageTask", get(ws_backup_image_task))
        .route("/coilList/{number}", get(coil_list))
        .route("/flush/{coil_id}", get(flush_coil_list))
        .route("/search/coilNo/{coil_no}", get(search_coil_no))
        .route("/search/coilId/{coil_id}", get(search_coil_id))
        .route("/search/DateTime/{start}/{end}", get(search_datetime))
        .route("/detail/{coil_id}", get(coil_detail))
        .route("/sync_summaries", post(sync_summaries))
        .route("/sync_summaries_range", post(sync_summaries_range))
        .route("/coilAlarm/get_info", get(coil_alarm_get_info))
        .route("/coilAlarm/{coil_id}", get(coil_alarm))
        .route("/search/defects/{coil_id}/{direction}", get(search_defects))
        .route(
            "/search/getDefectAll/{start_coil_id}/{end_coil_id}",
            get(search_defect_all),
        )
        .route(
            "/search/defects_all/{coil_id}/{direction}",
            get(search_defects_all),
        )
        .route("/manual_defects/{coil_id}/{direction}", get(manual_defects))
        .route("/manual_defect/add", post(add_manual_defect))
        .route(
            "/manual_defect/update/{defect_id}",
            put(update_manual_defect),
        )
        .route(
            "/manual_defect/delete/{defect_id}",
            delete(delete_manual_defect),
        )
        .route("/export_defects", post(export_defects))
        .route("/exportXlsxById/{start}/{end}", get(export_xlsx_by_id))
        .route(
            "/exportXlsxByDateTime/{start}/{end}",
            get(export_xlsx_by_datetime),
        )
        .route("/export_xlsx", post(export_xlsx_post))
        .route("/exportDataSimple", get(export_data_simple))
        .route("/export_1h", get(export_last_1h).post(export_last_1h))
        .route("/export_24h", get(export_last_24h).post(export_last_24h))
        .route("/export_today", get(export_today).post(export_today))
        .route("/search/CoilState/{coil_id}", get(search_coil_state))
        .route("/search/PlcData/{coil_id}", get(search_plc_data))
        .route("/plc_curve/{field}", get(plc_curve))
        .route("/plc_curve_all", get(plc_curve_all))
        .route("/get_point_data/{coil_id}/{surface_key}", get(get_point_data))
        .route("/get_line_data/{coil_id}/{surface_key}", get(get_line_data))
        .route("/check/get_coil_status/{coil_id}", get(get_coil_status))
        .route(
            "/check/set_coil_status/{coil_id}/{status}",
            get(set_coil_status_without_msg),
        )
        .route(
            "/check/set_coil_status/{coil_id}/{status}/{msg}",
            get(set_coil_status_with_msg),
        )
        .layer(DefaultBodyLimit::max(API_BODY_LIMIT_BYTES))
        .layer(CorsLayer::permissive())
        .layer(
            TraceLayer::new_for_http()
                .on_response(DefaultOnResponse::new().level(Level::INFO)),
        )
        .with_state(state)
}

#[derive(Clone, Deserialize)]
struct RenderQuery {
    thumbnail: Option<bool>,
    grayscale: Option<bool>,
    scale: Option<f64>,
    mask: Option<bool>,
    min_value: Option<i32>,
    max_value: Option<i32>,
    #[serde(rename = "minValue")]
    min_value_compat: Option<i32>,
    #[serde(rename = "maxValue")]
    max_value_compat: Option<i32>,
}

#[derive(Deserialize)]
struct AreaQuery {
    scale: Option<f64>,
    mask: Option<bool>,
    #[serde(rename = "valueFrom")]
    value_from: Option<f64>,
    #[serde(rename = "valueTo")]
    value_to: Option<f64>,
    r: Option<u8>,
    g: Option<u8>,
    b: Option<u8>,
}

#[derive(Deserialize)]
struct ErrorImageQuery {
    scale: Option<f64>,
    #[serde(rename = "minValue")]
    min_value: Option<f64>,
    #[serde(rename = "maxValue")]
    max_value: Option<f64>,
    force_cache: Option<bool>,
}

struct ImageFileQuery {
    width: Option<u32>,
    height: Option<u32>,
    quality: Option<u8>,
    format: Option<ImageFileFormat>,
    mask: Option<bool>,
}

#[derive(Copy, Clone)]
enum ImageFileFormat {
    Jpeg,
    Png,
}

impl ImageFileFormat {
    fn content_type(&self) -> &'static str {
        match self {
            Self::Jpeg => "image/jpeg",
            Self::Png => "image/png",
        }
    }
}

#[derive(Deserialize)]
struct ClipMaxImageQuery {
    save_url: Option<String>,
}

#[derive(Deserialize)]
struct ImageAreaQuery {
    row: Option<i32>,
    col: Option<i32>,
    count: Option<i32>,
    level: Option<i32>,
}

#[derive(Deserialize)]
struct TestModeRequest {
    enabled: bool,
}

#[derive(Deserialize)]
struct PlcCurveQuery {
    start_id: Option<i64>,
    end_id: Option<i64>,
    limit: Option<u32>,
}

#[derive(Deserialize)]
struct SyncSummariesRangeRequest {
    coil_ids: Option<Vec<i64>>,
}

#[derive(Deserialize)]
struct ManualDefectPayload {
    #[serde(rename = "secondaryCoilId")]
    secondary_coil_id: Option<i64>,
    surface: Option<String>,
    #[serde(rename = "defectName")]
    defect_name: Option<String>,
    #[serde(rename = "defectStatus")]
    defect_status: Option<i32>,
    #[serde(rename = "defectX")]
    defect_x: Option<i32>,
    #[serde(rename = "defectY")]
    defect_y: Option<i32>,
    #[serde(rename = "defectW")]
    defect_w: Option<i32>,
    #[serde(rename = "defectH")]
    defect_h: Option<i32>,
    #[serde(rename = "defectData")]
    defect_data: Option<Value>,
    remark: Option<String>,
    annotator: Option<String>,
}

#[derive(Deserialize)]
struct ExportDefectsRequest {
    defects: Option<Vec<Value>>,
    folder_path: Option<String>,
}

#[derive(Deserialize)]
struct ExportXlsxQuery {
    export_type: Option<String>,
}

#[derive(Deserialize)]
struct ExportXlsxConfigRequest {
    export_type: String,
    detection_3d_info: bool,
    defect_info: bool,
    defect_show_info: bool,
    defect_un_show_info: bool,
    area_defect_image: Option<bool>,
    export_plc_data: bool,
    #[serde(rename = "startDate")]
    start_date: String,
    #[serde(rename = "endDate")]
    end_date: String,
}

#[derive(Deserialize)]
struct BackupImageTaskRequest {
    from_id: i64,
    to_id: i64,
    folder: String,
}

#[derive(Deserialize)]
struct ClipConfigPayload {
    surface_key: String,
    mode: Option<String>,
    fixed: Option<i64>,
    a: Option<f64>,
    b: Option<f64>,
    c: Option<f64>,
    offset: Option<i64>,
}

#[derive(Deserialize)]
struct RejoinPayload {
    coil_id: i64,
    surface_key: Option<String>,
}

impl ManualDefectPayload {
    fn validate_add(&self) -> Result<(), String> {
        if self.secondary_coil_id.is_none() {
            return Err("secondaryCoilId is required".to_string());
        }
        if self
            .surface
            .as_deref()
            .unwrap_or_default()
            .trim()
            .is_empty()
        {
            return Err("surface is required".to_string());
        }
        if self.defect_x.is_none() {
            return Err("defectX is required".to_string());
        }
        if self.defect_y.is_none() {
            return Err("defectY is required".to_string());
        }
        if self.defect_w.is_none() {
            return Err("defectW is required".to_string());
        }
        if self.defect_h.is_none() {
            return Err("defectH is required".to_string());
        }
        Ok(())
    }

    fn into_write(self) -> ManualDefectWrite {
        ManualDefectWrite {
            secondary_coil_id: self.secondary_coil_id,
            surface: self.surface,
            defect_name: self.defect_name,
            defect_status: self.defect_status,
            defect_x: self.defect_x,
            defect_y: self.defect_y,
            defect_w: self.defect_w,
            defect_h: self.defect_h,
            defect_data: self.defect_data,
            remark: self.remark,
            annotator: self.annotator,
        }
    }
}

impl RenderQuery {
    fn thumbnail(&self) -> bool {
        self.thumbnail.unwrap_or(false)
    }

    fn grayscale(&self) -> bool {
        self.grayscale.unwrap_or(false)
    }

    fn colormap(&self) -> &'static str {
        if self.grayscale() { "GRAY" } else { "JET" }
    }

    fn mask(&self) -> bool {
        self.mask.unwrap_or(true)
    }

    fn scale(&self) -> f64 {
        self.scale
            .filter(|value| value.is_finite() && *value > 0.0)
            .unwrap_or(1.0)
    }

    fn min_max(&self) -> (i32, i32) {
        let min_value = self.min_value_compat.or(self.min_value).unwrap_or(0);
        let mut max_value = self.max_value_compat.or(self.max_value).unwrap_or(255);
        if max_value <= min_value {
            max_value = min_value + 1;
        }
        (min_value, max_value)
    }

    fn with_thumbnail(&self, thumbnail: bool) -> Self {
        let mut query = self.clone();
        query.thumbnail = Some(thumbnail);
        query
    }
}

async fn root() -> Json<Value> {
    Json(json!({"/docs": "请访问 /docs 查看文档"}))
}

async fn current_coil(State(state): State<ApiState>) -> Json<Value> {
    let body = match state.repository.latest_coil().await {
        Ok(Some(row)) => {
            let mut body = latest_coil_to_python_json(&row);
            let mut compatible_coil_no: Option<String> = None;
            let mut compatible_act_width: Option<f64> = None;

            if let Ok(secondary_rows) = state.repository.secondary_coils(row.secondary_coil_id).await {
                if let Some(secondary_row) = secondary_rows.into_iter().next() {
                    if !secondary_row.coil_no.trim().is_empty() {
                        compatible_coil_no = Some(secondary_row.coil_no);
                    }
                    if compatible_act_width.is_none() {
                        compatible_act_width = secondary_row.act_width;
                    }
                }
            }

            if compatible_coil_no.is_none() || compatible_act_width.is_none() {
                if let Ok(Some(detail_row)) = state
                    .repository
                    .coil_detail(row.secondary_coil_id)
                    .await
                {
                    if compatible_coil_no.is_none() {
                        let coil_no = detail_row.coil_no.trim().to_string();
                        if !coil_no.is_empty() {
                            compatible_coil_no = Some(coil_no);
                        }
                    }
                    if compatible_act_width.is_none() {
                        compatible_act_width = detail_row.act_width;
                    }
                }
            }

            if let Value::Object(ref mut object) = body {
                object.insert(
                    "DetectionTime".to_string(),
                    json!(row.detection_time.as_deref().unwrap_or("")),
                );
                if let Some(coil_no) = compatible_coil_no {
                    object.insert("Coil_ID".to_string(), json!(coil_no));
                }
                if let Some(act_width) = compatible_act_width {
                    let width = json!(act_width);
                    object.insert("ActWidth".to_string(), width.clone());
                    object.insert("act_w".to_string(), width.clone());
                    object.insert("ACT_W".to_string(), width.clone());
                    object.insert("width".to_string(), width);
                }
            }

            body
        }
        _ => json!({}),
    };

    Json(body)
}

async fn plc_info(State(state): State<ApiState>) -> Json<Value> {
    Json(state.plc_info_body())
}

async fn plc_connect(
    State(state): State<ApiState>,
    Path((plc_ip, rack, slot)): Path<(String, i64, i64)>,
) -> Json<bool> {
    state.set_plc_connection(plc_ip, rack, slot);
    Json(true)
}

async fn plc_get(
    State(state): State<ApiState>,
    Path((addr, type_str, length)): Path<(String, String, i64)>,
) -> Response {
    match state.plc_value_read(&addr, &type_str, length) {
        Ok(value) => Json(value).into_response(),
        Err(response) => response,
    }
}

#[derive(Clone, Copy)]
struct OpenApiRoute {
    method: &'static str,
    path: &'static str,
}

const OPENAPI_ROUTES: &[OpenApiRoute] = &[
    OpenApiRoute {
        method: "get",
        path: "/",
    },
    OpenApiRoute {
        method: "get",
        path: "/currentCoil",
    },
    OpenApiRoute {
        method: "get",
        path: "/version",
    },
    OpenApiRoute {
        method: "get",
        path: "/delay",
    },
    OpenApiRoute {
        method: "get",
        path: "/info",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc/info/",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc/info",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc/connect/{plc_ip}/{rack}/{slot}",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc/get/{addr}/{type_str}/{length}",
    },
    OpenApiRoute {
        method: "get",
        path: "/runtime_info",
    },
    OpenApiRoute {
        method: "get",
        path: "/software_update/manifest",
    },
    OpenApiRoute {
        method: "get",
        path: "/updates/{file_name}",
    },
    OpenApiRoute {
        method: "get",
        path: "/grader_list",
    },
    OpenApiRoute {
        method: "get",
        path: "/database_info",
    },
    OpenApiRoute {
        method: "get",
        path: "/health",
    },
    OpenApiRoute {
        method: "get",
        path: "/coil_list_value_change_keys",
    },
    OpenApiRoute {
        method: "get",
        path: "/data_has/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/defectDict",
    },
    OpenApiRoute {
        method: "get",
        path: "/defectClasses",
    },
    OpenApiRoute {
        method: "get",
        path: "/defectDictAll",
    },
    OpenApiRoute {
        method: "post",
        path: "/setDefectDict",
    },
    OpenApiRoute {
        method: "get",
        path: "/control/config",
    },
    OpenApiRoute {
        method: "post",
        path: "/control/set_config",
    },
    OpenApiRoute {
        method: "get",
        path: "/control/set_property",
    },
    OpenApiRoute {
        method: "get",
        path: "/download_test",
    },
    OpenApiRoute {
        method: "get",
        path: "/speedtest/download",
    },
    OpenApiRoute {
        method: "post",
        path: "/speedtest/upload",
    },
    OpenApiRoute {
        method: "get",
        path: "/hardware",
    },
    OpenApiRoute {
        method: "get",
        path: "/capture_status",
    },
    OpenApiRoute {
        method: "get",
        path: "/camera/status",
    },
    OpenApiRoute {
        method: "post",
        path: "/camera/params",
    },
    OpenApiRoute {
        method: "post",
        path: "/camera/reconnect",
    },
    OpenApiRoute {
        method: "get",
        path: "/cameras",
    },
    OpenApiRoute {
        method: "get",
        path: "/cameras/{camera_key}/status",
    },
    OpenApiRoute {
        method: "get",
        path: "/cameras/{camera_key}/files",
    },
    OpenApiRoute {
        method: "post",
        path: "/cameras/{camera_key}/params",
    },
    OpenApiRoute {
        method: "post",
        path: "/cameras/{camera_key}/reconnect",
    },
    OpenApiRoute {
        method: "get",
        path: "/capture/status",
    },
    OpenApiRoute {
        method: "get",
        path: "/capture/files",
    },
    OpenApiRoute {
        method: "get",
        path: "/getListenerAddFile",
    },
    OpenApiRoute {
        method: "get",
        path: "/camera_adjust",
    },
    OpenApiRoute {
        method: "post",
        path: "/camera_adjust/{camera_key}",
    },
    OpenApiRoute {
        method: "post",
        path: "/camera_adjust/{camera_key}/reconnect",
    },
    OpenApiRoute {
        method: "get",
        path: "/cameraAlarm",
    },
    OpenApiRoute {
        method: "get",
        path: "/cameraData/{coil_id}/{camera_key}",
    },
    OpenApiRoute {
        method: "get",
        path: "/settings/test_mode",
    },
    OpenApiRoute {
        method: "post",
        path: "/settings/test_mode",
    },
    OpenApiRoute {
        method: "get",
        path: "/settings/test_mode_status",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilInfo/{coil_id}/{surface_key}",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilData/heightData/{surface_key}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilData/heightPoint/{surface_key}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilData/Render/{surfaceKey}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilData/Area/{surface_key}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilData/Error/{surface_key}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/image/preview/{surface_key}/{coil_id}/{type_}",
    },
    OpenApiRoute {
        method: "get",
        path: "/image/source/{surface_key}/{coil_id}/{type_}",
    },
    OpenApiRoute {
        method: "get",
        path: "/image/area/{surface_key}/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/image/area/{surface_key}/{coil_id}/{type_}",
    },
    OpenApiRoute {
        method: "get",
        path: "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
    },
    OpenApiRoute {
        method: "get",
        path: "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
    },
    OpenApiRoute {
        method: "get",
        path: "/clipMaxImage/{coil_id}/{key}",
    },
    OpenApiRoute {
        method: "get",
        path: "/reDetection/status",
    },
    OpenApiRoute {
        method: "get",
        path: "/reDetection/start/{from_id}/{to_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/getServerState",
    },
    OpenApiRoute {
        method: "get",
        path: "/ws/alg_2d/test/progress",
    },
    OpenApiRoute {
        method: "post",
        path: "/clip_config",
    },
    OpenApiRoute {
        method: "post",
        path: "/area/rejoin",
    },
    OpenApiRoute {
        method: "get",
        path: "/area/status",
    },
    OpenApiRoute {
        method: "post",
        path: "/area/scan",
    },
    OpenApiRoute {
        method: "get",
        path: "/save_to_sql/{sql_file}",
    },
    OpenApiRoute {
        method: "get",
        path: "/backupImageTask/{from_id}/{to_id}/{save_folder}",
    },
    OpenApiRoute {
        method: "get",
        path: "/ws/backupImageTask",
    },
    OpenApiRoute {
        method: "get",
        path: "/ws/coilData/heightPoint",
    },
    OpenApiRoute {
        method: "get",
        path: "/ws/DetectionState",
    },
    OpenApiRoute {
        method: "get",
        path: "/ws/reDetection",
    },
    OpenApiRoute {
        method: "get",
        path: "/alg_2d/models",
    },
    OpenApiRoute {
        method: "post",
        path: "/alg_2d/test/start",
    },
    OpenApiRoute {
        method: "post",
        path: "/alg_2d/test/stop",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilList/{number}",
    },
    OpenApiRoute {
        method: "get",
        path: "/flush/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/coilNo/{coil_no}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/coilId/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/DateTime/{start}/{end}",
    },
    OpenApiRoute {
        method: "get",
        path: "/detail/{coil_id}",
    },
    OpenApiRoute {
        method: "post",
        path: "/sync_summaries",
    },
    OpenApiRoute {
        method: "post",
        path: "/sync_summaries_range",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilAlarm/get_info",
    },
    OpenApiRoute {
        method: "get",
        path: "/coilAlarm/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/defects/{coil_id}/{direction}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/getDefectAll/{start_coil_id}/{end_coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/defects_all/{coil_id}/{direction}",
    },
    OpenApiRoute {
        method: "get",
        path: "/manual_defects/{coil_id}/{direction}",
    },
    OpenApiRoute {
        method: "post",
        path: "/manual_defect/add",
    },
    OpenApiRoute {
        method: "put",
        path: "/manual_defect/update/{defect_id}",
    },
    OpenApiRoute {
        method: "delete",
        path: "/manual_defect/delete/{defect_id}",
    },
    OpenApiRoute {
        method: "post",
        path: "/export_defects",
    },
    OpenApiRoute {
        method: "get",
        path: "/exportXlsxById/{start}/{end}",
    },
    OpenApiRoute {
        method: "get",
        path: "/exportXlsxByDateTime/{start}/{end}",
    },
    OpenApiRoute {
        method: "post",
        path: "/export_xlsx",
    },
    OpenApiRoute {
        method: "get",
        path: "/exportDataSimple",
    },
    OpenApiRoute {
        method: "get",
        path: "/export_1h",
    },
    OpenApiRoute {
        method: "post",
        path: "/export_1h",
    },
    OpenApiRoute {
        method: "get",
        path: "/export_24h",
    },
    OpenApiRoute {
        method: "post",
        path: "/export_24h",
    },
    OpenApiRoute {
        method: "get",
        path: "/export_today",
    },
    OpenApiRoute {
        method: "post",
        path: "/export_today",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/CoilState/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/search/PlcData/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc_curve/{field}",
    },
    OpenApiRoute {
        method: "get",
        path: "/plc_curve_all",
    },
    OpenApiRoute {
        method: "get",
        path: "/get_point_data/{coil_id}/{surface_key}",
    },
    OpenApiRoute {
        method: "get",
        path: "/get_line_data/{coil_id}/{surface_key}",
    },
    OpenApiRoute {
        method: "get",
        path: "/check/get_coil_status/{coil_id}",
    },
    OpenApiRoute {
        method: "get",
        path: "/check/set_coil_status/{coil_id}/{status}",
    },
    OpenApiRoute {
        method: "get",
        path: "/check/set_coil_status/{coil_id}/{status}/{msg}",
    },
];

async fn openapi_json() -> Json<Value> {
    let mut paths = Map::new();
    for route in OPENAPI_ROUTES {
        let methods = paths
            .entry(route.path.to_string())
            .or_insert_with(|| Value::Object(Map::new()));
        if let Value::Object(methods) = methods {
            methods.insert(route.method.to_string(), openapi_operation(route));
        }
    }

    Json(json!({
        "openapi": "3.1.0",
        "info": {
            "title": "FastAPI",
            "version": "0.1.0",
        },
        "paths": paths,
        "components": {
            "schemas": openapi_component_schemas(),
        },
    }))
}

fn openapi_operation(route: &OpenApiRoute) -> Value {
    let mut operation = Map::new();
    if let Some(tags) = openapi_tags(route) {
        operation.insert("tags".to_string(), json!(tags));
    }
    operation.insert("summary".to_string(), json!(openapi_summary(route)));
    if let Some(description) = openapi_description(route) {
        operation.insert("description".to_string(), json!(description));
    }
    operation.insert(
        "operationId".to_string(),
        json!(openapi_operation_id(route.method, route.path)),
    );

    let mut parameters = openapi_parameters(route);
    if route.path == "/sync_summaries" {
        parameters.push(json!({
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
                "type": "integer",
                "default": 1000,
                "title": "Limit",
            },
        }));
    }
    let has_parameters = !parameters.is_empty();
    if has_parameters {
        operation.insert("parameters".to_string(), Value::Array(parameters));
    }

    let request_body = openapi_request_body(route);
    let has_request_body = request_body.is_some();
    if let Some(request_body) = request_body {
        operation.insert("requestBody".to_string(), request_body);
    }

    operation.insert(
        "responses".to_string(),
        openapi_responses(route, has_parameters || has_request_body),
    );
    Value::Object(operation)
}

fn openapi_request_body(route: &OpenApiRoute) -> Option<Value> {
    let request_body = match (route.method, route.path) {
        ("post", "/sync_summaries_range") => openapi_required_object_request_body("Request"),
        ("post", "/alg_2d/test/start") => openapi_required_object_request_body("Payload"),
        ("post", "/control/set_config") | ("post", "/setDefectDict") => {
            openapi_required_object_request_body("Data")
        }
        ("post", "/export_defects") | ("post", "/manual_defect/add") => {
            openapi_required_object_request_body("Request")
        }
        ("post", "/alg_2d/test/stop") => json!({
            "content": {
                "application/json": {
                    "schema": {
                        "anyOf": [
                            {"additionalProperties": true, "type": "object"},
                            {"type": "null"},
                        ],
                        "title": "Payload",
                    },
                },
            },
        }),
        ("post", "/camera_adjust/{camera_key}") => {
            openapi_required_schema_ref_request_body("CameraAdjustmentPayload")
        }
        ("post", "/camera/params") | ("post", "/cameras/{camera_key}/params") => {
            openapi_required_schema_ref_request_body("CameraAdjustmentPayload")
        }
        ("post", "/export_xlsx") => {
            openapi_required_schema_ref_request_body("ExportXlsxConfigModel")
        }
        ("post", "/settings/test_mode") => {
            openapi_required_schema_ref_request_body("TestModeRequest")
        }
        ("post", "/clip_config") => openapi_required_schema_ref_request_body("ClipConfigPayload"),
        ("post", "/area/rejoin") => openapi_required_schema_ref_request_body("AreaRejoinPayload"),
        ("post", "/speedtest/upload") => json!({
            "content": {
                "multipart/form-data": {
                    "schema": {"$ref": "#/components/schemas/Body_upload_test_speedtest_upload_post"},
                },
            },
            "required": true,
        }),
        ("put", "/manual_defect/update/{defect_id}") => {
            openapi_required_object_request_body("Request")
        }
        _ => return None,
    };
    Some(request_body)
}

fn openapi_tags(route: &OpenApiRoute) -> Option<&'static [&'static str]> {
    match (route.method, route.path) {
        ("get", "/info")
        | ("get", "/runtime_info")
        | ("get", "/grader_list")
        | ("get", "/coil_list_value_change_keys")
        | ("get", "/database_info")
        | ("get", "/data_has/{coil_id}") => Some(&["参数服务"]),
        ("get", "/hardware") => Some(&["数据库服务"]),
        ("get", "/control/config")
        | ("post", "/control/set_config")
        | ("get", "/control/set_property") => Some(&["参数控制服务"]),
        ("post", "/setDefectDict")
        | ("get", "/settings/test_mode")
        | ("post", "/settings/test_mode")
        | ("get", "/settings/test_mode_status") => Some(&["参数设置"]),
        ("get", "/coilList/{number}")
        | ("get", "/flush/{coil_id}")
        | ("get", "/detail/{coil_id}")
        | ("get", "/defectDict")
        | ("get", "/defectClasses")
        | ("get", "/defectDictAll")
        | ("get", "/coilInfo/{coil_id}/{surface_key}")
        | ("get", "/search/coilNo/{coil_no}")
        | ("get", "/search/coilId/{coil_id}")
        | ("get", "/search/DateTime/{start}/{end}")
        | ("get", "/search/CoilState/{coil_id}")
        | ("get", "/search/PlcData/{coil_id}")
        | ("get", "/search/defects/{coil_id}/{direction}")
        | ("get", "/search/getDefectAll/{start_coil_id}/{end_coil_id}")
        | ("get", "/search/defects_all/{coil_id}/{direction}")
        | ("get", "/manual_defects/{coil_id}/{direction}")
        | ("post", "/manual_defect/add")
        | ("put", "/manual_defect/update/{defect_id}")
        | ("delete", "/manual_defect/delete/{defect_id}")
        | ("post", "/export_defects")
        | ("get", "/get_point_data/{coil_id}/{surface_key}")
        | ("get", "/get_line_data/{coil_id}/{surface_key}")
        | ("get", "/plc_curve/{field}")
        | ("get", "/plc_curve_all")
        | ("get", "/check/get_coil_status/{coil_id}")
        | ("get", "/check/set_coil_status/{coil_id}/{status}")
        | ("get", "/check/set_coil_status/{coil_id}/{status}/{msg}")
        | ("get", "/camera_adjust")
        | ("post", "/camera_adjust/{camera_key}")
        | ("post", "/camera_adjust/{camera_key}/reconnect")
        | ("get", "/capture_status")
        | ("get", "/camera/status")
        | ("post", "/camera/params")
        | ("post", "/camera/reconnect")
        | ("get", "/cameras")
        | ("get", "/cameras/{camera_key}/status")
        | ("get", "/cameras/{camera_key}/files")
        | ("post", "/cameras/{camera_key}/params")
        | ("post", "/cameras/{camera_key}/reconnect")
        | ("get", "/capture/status")
        | ("get", "/capture/files")
        | ("get", "/getListenerAddFile")
        | ("get", "/cameraAlarm")
        | ("get", "/cameraData/{coil_id}/{camera_key}")
        | ("get", "/backupImageTask/{from_id}/{to_id}/{save_folder}")
        | ("post", "/sync_summaries")
        | ("post", "/sync_summaries_range") => Some(&["数据库服务"]),
        ("get", "/save_to_sql/{sql_file}")
        | ("get", "/exportXlsxById/{start}/{end}")
        | ("get", "/exportXlsxByDateTime/{start}/{end}")
        | ("post", "/export_xlsx")
        | ("get", "/exportDataSimple")
        | ("get", "/export_1h")
        | ("post", "/export_1h")
        | ("get", "/export_24h")
        | ("post", "/export_24h")
        | ("get", "/export_today")
        | ("post", "/export_today") => Some(&["备份服务"]),
        ("get", "/download_test")
        | ("get", "/speedtest/download")
        | ("post", "/speedtest/upload") => Some(&["测试服务"]),
        ("get", "/coilAlarm/get_info") | ("get", "/coilAlarm/{coil_id}") => Some(&["报警、判级"]),
        ("get", "/alg_2d/models")
        | ("post", "/alg_2d/test/start")
        | ("post", "/alg_2d/test/stop")
        | ("get", "/ws/alg_2d/test/progress") => Some(&["算法测试"]),
        ("get", "/reDetection/start/{from_id}/{to_id}")
        | ("get", "/reDetection/status")
        | ("get", "/getServerState")
        | ("get", "/ws/reDetection")
        | ("get", "/ws/DetectionState") => Some(&["算法服务-与算法同步运行"]),
        ("get", "/coilData/heightData/{surface_key}/{coil_id}")
        | ("get", "/coilData/heightPoint/{surface_key}/{coil_id}")
        | ("get", "/ws/coilData/heightPoint")
        | ("get", "/coilData/Render/{surfaceKey}/{coil_id}")
        | ("get", "/coilData/Area/{surface_key}/{coil_id}")
        | ("get", "/coilData/Error/{surface_key}/{coil_id}")
        | ("get", "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}") => {
            Some(&["深度数据访问服务"])
        }
        ("get", "/image/preview/{surface_key}/{coil_id}/{type_}")
        | ("get", "/image/source/{surface_key}/{coil_id}/{type_}")
        | ("get", "/image/area/{surface_key}/{coil_id}")
        | ("get", "/image/area/{surface_key}/{coil_id}/{type_}")
        | ("get", "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}") => {
            Some(&["图像访问服务"])
        }
        ("get", "/ws/backupImageTask") => Some(&["备份服务"]),
        _ => None,
    }
}

fn openapi_description(route: &OpenApiRoute) -> Option<&'static str> {
    match (route.method, route.path) {
        ("get", "/database_info") => Some("获取数据库信息。"),
        ("get", "/runtime_info") => Some(
            "运行环境信息：Python 版本、缓存模式、CPU/GPU 型号等，\n以及当前 3D 服务的运行模式（本地 / 开发者模式）。",
        ),
        ("get", "/control/config") => Some("控制配置获取"),
        ("post", "/control/set_config") | ("get", "/control/set_property") => Some("控制配置设置"),
        ("post", "/setDefectDict") => Some("设置缺陷字典"),
        ("get", "/settings/test_mode") => Some("获取测试模式状态"),
        ("post", "/settings/test_mode") => Some("设置测试模式状态"),
        ("get", "/settings/test_mode_status") => Some("获取详细的测试模式状态信息"),
        ("get", "/coilList/{number}") => Some(
            "获取 n 条数据（优先查询摘要表，快速返回）\n\n摘要表由算法检测结束时自动更新，确保数据一致性",
        ),
        ("get", "/flush/{coil_id}") => Some("向上刷新（仅查询摘要表，快速返回）"),
        ("get", "/detail/{coil_id}") => Some(
            "获取卷材详情（完整数据）\n包括：基本信息、报警详情、缺陷列表、塔形点数据、松卷/扁卷报警等\n用于点击查看详情时调用",
        ),
        ("get", "/defectDictAll") => Some("获取全部的表面缺陷数据字段"),
        ("get", "/get_point_data/{coil_id}/{surface_key}") => Some("获取点数据"),
        ("get", "/cameraAlarm") => Some("获取相机报警信息\nReturns:"),
        ("post", "/sync_summaries") => Some("手动触发批量同步摘要数据\n用于初始化摘要表"),
        ("post", "/sync_summaries_range") => Some(
            "快速同步指定 ID 范围的摘要数据\n只更新已存在的记录，不创建新记录\n主要用于更新 DefectCountS/L 和 MaxDefect 字段",
        ),
        ("get", "/search/defects_all/{coil_id}/{direction}") => Some(
            "获取所有缺陷（包括自动检测和手动标注）\n\nArgs:\n    coil_id: 二级卷ID\n    direction: 表面标识（S/L）\n\nReturns:\n    包含自动检测缺陷和手动标注缺陷的列表",
        ),
        ("get", "/manual_defects/{coil_id}/{direction}") => Some(
            "获取手动标注的缺陷列表\n\nArgs:\n    coil_id: 二级卷ID\n    direction: 表面标识（S/L）\n\nReturns:\n    手动标注缺陷列表",
        ),
        ("post", "/manual_defect/add") => Some(
            "添加手动标注的缺陷\n\nArgs:\n    request: 缺陷数据字典，包含：\n        - secondaryCoilId: 二级卷ID\n        - surface: 表面标识（S/L）\n        - defectName: 缺陷名称\n        - defectX: X坐标\n        - defectY: Y坐标\n        - defectW: 宽度\n        - defectH: 高度\n        - remark: 备注（可选）\n        - annotator: 标注人（可选）\n\nReturns:\n    创建的缺陷数据",
        ),
        ("put", "/manual_defect/update/{defect_id}") => Some(
            "更新手动标注的缺陷\n\nArgs:\n    defect_id: 缺陷ID\n    request: 更新的数据字典\n\nReturns:\n    更新后的缺陷数据，如果不存在返回错误",
        ),
        ("delete", "/manual_defect/delete/{defect_id}") => {
            Some("删除手动标注的缺陷\n\nArgs:\n    defect_id: 缺陷ID\n\nReturns:\n    删除结果")
        }
        ("post", "/export_defects") => Some(
            "导出当前显示的缺陷图像到本地文件夹\n\nArgs:\n    request: 包含 defects（缺陷列表）和 folder_path（导出路径）的字典\n\nReturns:\n    导出结果统计",
        ),
        ("get", "/speedtest/download") => {
            Some("生成一个指定大小的文件流，单位是MB（默认为10MB）\n访问此接口可测试下载速度。")
        }
        ("post", "/speedtest/upload") => {
            Some("接收文件并记录上传时间。\n访问此接口上传文件可测试上传速度。")
        }
        ("get", "/coilAlarm/get_info") => Some("获取报警信息\nReturns:"),
        ("get", "/coilAlarm/{coil_id}") => {
            Some("返回全部的警告数据\nArgs:\n    coil_id:\n\nReturns:")
        }
        ("get", "/alg_2d/models") => Some("获取可用的算法模型列表"),
        ("get", "/ws/alg_2d/test/progress") => {
            Some("读取 2D 算法测试进度 WebSocket 通道。客户端可监听 JSON 任务状态推送。")
        }
        ("get", "/reDetection/start/{from_id}/{to_id}") => {
            Some("通过 HTTP 启动重新识别任务，指定起止 SecondaryCoilId。")
        }
        ("get", "/reDetection/status") => Some("获取当前重新识别任务进度。"),
        ("get", "/ws/reDetection") => {
            Some("通过 WebSocket 启动并监听重新识别任务状态。发送开始参数后接收任务快照。")
        }
        ("get", "/ws/DetectionState") => {
            Some("通过 WebSocket 订阅算法服务检测状态消息。收到文本后返回当前状态快照。")
        }
        ("get", "/ws/backupImageTask") => {
            Some("图片备份 WebSocket 通道。发送备份请求后接收进度消息。")
        }
        ("get", "/ws/coilData/heightPoint") => {
            Some("通过 WebSocket 查询点位高度。发送 JSON 请求并返回 surface / coil / x/y / value 或错误。")
        }
        ("get", "/coilData/heightData/{surface_key}/{coil_id}") => Some(
            "Return line segments for curve display.\n\nThe UI expects:\n[\n  {\n    \"pointL\": [x0, y0],\n    \"pointR\": [x1, y1],\n    \"points\": [[x, y, z], ...]\n  },\n  ...\n]",
        ),
        ("get", "/coilData/Render/{surfaceKey}/{coil_id}") => Some(
            "获取渲染图像（支持伪彩色 JET 和灰度 GRAY）\n\n参数:\n- thumbnail=true: 返回缓存的缩略图（快速加载）\n- thumbnail=false: 返回完整渲染图像\n- grayscale=true: 返回灰度图像（GRAY.jpg 缓存）\n- grayscale=false: 返回伪彩色图像（JET.jpg 缓存）",
        ),
        ("get", "/coilData/Error/{surface_key}/{coil_id}") => Some(
            "获取 Error 塔形报警图像\n\n计算方法（与预生成缓存一致）：\n- 蓝色：低于 中位数 - minValue mm（塔形过小，远离侧）\n- 红色：高于 中位数 + maxValue mm（塔形过大，靠近侧）\n\n优先从 AlgServer 预生成的缓存读取 (png/Error.png)\n如果缓存不存在且 force_cache=False，则动态生成",
        ),
        ("get", "/image/source/{surface_key}/{coil_id}/{type_}") => Some("增加 2D 影像"),
        ("get", "/image/area/{surface_key}/{coil_id}")
        | ("get", "/image/area/{surface_key}/{coil_id}/{type_}") => Some(
            "多级瓦片加载接口\n\n参数说明:\n- row=-1: 返回完整图像\n- row=-2: 返回预览图像\n- count=0: 返回图像宽高信息\n- level: 瓦片质量等级 (0=缩略图 1/16, 1=1/8, 2=1/4, 3=1/2, 4=原图)\n\n瓦片等级:\n- Level 0: 340x340, JPEG 60 (~20KB)\n- Level 1: 682x682, JPEG 70 (~50KB)\n- Level 2: 1364x1364, JPEG 80 (~120KB)\n- Level 3: 2728x2728, JPEG 90 (~250KB)\n- Level 4: 5460x5460, JPEG 95 (~500KB)\n\n缓存策略:\n- 优先从缓存读取对应级别的瓦片（直接返回，速度最快）\n- 缓存不存在时，生成所有级别的瓦片并保存",
        ),
        _ => None,
    }
}

fn openapi_required_object_request_body(title: &str) -> Value {
    json!({
        "content": {
            "application/json": {
                "schema": {
                    "additionalProperties": true,
                    "type": "object",
                    "title": title,
                },
            },
        },
        "required": true,
    })
}

fn openapi_required_schema_ref_request_body(schema_name: &str) -> Value {
    json!({
        "content": {
            "application/json": {
                "schema": {"$ref": format!("#/components/schemas/{schema_name}")},
            },
        },
        "required": true,
    })
}

fn openapi_summary(route: &OpenApiRoute) -> String {
    match (route.method, route.path) {
        ("get", "/currentCoil") => return "Read Root".to_string(),
        ("get", "/health") => return "Health".to_string(),
        ("get", "/version") => return "Read Version".to_string(),
        ("get", "/delay") => return "Get Delay".to_string(),
        ("get", "/info") => return "Info".to_string(),
        ("get", "/plc/info/") => return "Info Plc".to_string(),
        ("get", "/plc/info") => return "Info Plc".to_string(),
        ("get", "/plc/connect/{plc_ip}/{rack}/{slot}") => return "Connect Plc".to_string(),
        ("get", "/plc/get/{addr}/{type_str}/{length}") => return "Get Plc Value".to_string(),
        ("get", "/runtime_info") => return "Runtime Info".to_string(),
        ("get", "/grader_list") => return "Grader List".to_string(),
        ("get", "/coil_list_value_change_keys") => {
            return "Coil List Value Change Keys".to_string();
        }
        ("get", "/hardware") => return "Get Hardware".to_string(),
        ("get", "/control/config") => return "Get Config".to_string(),
        ("post", "/control/set_config") => return "Set Config".to_string(),
        ("get", "/control/set_property") => return "Set Property".to_string(),
        ("post", "/setDefectDict") => return "Set Defect Dict".to_string(),
        ("get", "/settings/test_mode") => return "Get Test Mode".to_string(),
        ("post", "/settings/test_mode") => return "Set Test Mode".to_string(),
        ("get", "/settings/test_mode_status") => return "Get Test Mode Status".to_string(),
        ("get", "/coilList/{number}") => return "Get Coil".to_string(),
        ("get", "/flush/{coil_id}") => return "Get Flush".to_string(),
        ("get", "/detail/{coil_id}") => return "Get Coil Detail Api".to_string(),
        ("get", "/defectDict") => return "Get Defect Dict".to_string(),
        ("get", "/defectClasses") => return "Get Defect Dict".to_string(),
        ("get", "/defectDictAll") => return "Get Defect Dict All".to_string(),
        ("get", "/data_has/{coil_id}") => return "Get Daa Has".to_string(),
        ("get", "/coilInfo/{coil_id}/{surface_key}") => return "Get Info".to_string(),
        ("get", "/search/coilNo/{coil_no}") => return "Search By Coil No".to_string(),
        ("get", "/search/coilId/{coil_id}") => return "Search By Coil Id".to_string(),
        ("get", "/search/DateTime/{start}/{end}") => return "Search By Date Time".to_string(),
        ("get", "/search/CoilState/{coil_id}") => return "Get Coil State".to_string(),
        ("get", "/search/PlcData/{coil_id}") => return "Get Plc Data".to_string(),
        ("get", "/search/defects/{coil_id}/{direction}") => return "Get Defects".to_string(),
        ("get", "/search/getDefectAll/{start_coil_id}/{end_coil_id}") => {
            return "Get Defect All".to_string();
        }
        ("get", "/search/defects_all/{coil_id}/{direction}") => {
            return "Get Defects All Including Manual".to_string();
        }
        ("get", "/manual_defects/{coil_id}/{direction}") => {
            return "Get Manual Defects Api".to_string();
        }
        ("post", "/manual_defect/add") => return "Add Manual Defect Api".to_string(),
        ("put", "/manual_defect/update/{defect_id}") => {
            return "Update Manual Defect Api".to_string();
        }
        ("delete", "/manual_defect/delete/{defect_id}") => {
            return "Delete Manual Defect Api".to_string();
        }
        ("post", "/export_defects") => return "Export Defects".to_string(),
        ("get", "/get_point_data/{coil_id}/{surface_key}") => return "Get Point Data".to_string(),
        ("get", "/get_line_data/{coil_id}/{surface_key}") => return "Get Line Data".to_string(),
        ("get", "/plc_curve/{field}") => return "Get Plc Curve".to_string(),
        ("get", "/plc_curve_all") => return "Get Plc Curve All".to_string(),
        ("get", "/check/get_coil_status/{coil_id}") => return "Get Coil Status".to_string(),
        ("get", "/check/set_coil_status/{coil_id}/{status}")
        | ("get", "/check/set_coil_status/{coil_id}/{status}/{msg}") => {
            return "Set Coil Status".to_string();
        }
        ("get", "/camera_adjust") => return "Get Camera Adjustments".to_string(),
        ("post", "/camera_adjust/{camera_key}") => return "Set Camera Adjustment".to_string(),
        ("post", "/camera_adjust/{camera_key}/reconnect") => {
            return "Reconnect Camera Adjustment".to_string();
        }
        ("get", "/capture_status") => return "Get Capture Status".to_string(),
        ("get", "/cameraAlarm") => return "Get Camera Alarm".to_string(),
        ("get", "/cameraData/{coil_id}/{camera_key}") => return "Get Camera Data".to_string(),
        ("get", "/backupImageTask/{from_id}/{to_id}/{save_folder}") => {
            return "Backup Image Task".to_string();
        }
        ("post", "/sync_summaries") => return "Sync Summaries Api".to_string(),
        ("post", "/sync_summaries_range") => return "Sync Summaries Range Api".to_string(),
        ("get", "/save_to_sql/{sql_file}") => return "Save To Sql".to_string(),
        ("get", "/exportXlsxById/{start}/{end}") => return "Export Xlsx By Id".to_string(),
        ("get", "/exportXlsxByDateTime/{start}/{end}") => {
            return "Export Xlsx By Datetime".to_string();
        }
        ("post", "/export_xlsx") => return "Export Xlsx Post".to_string(),
        ("get", "/exportDataSimple") => return "Export Data Simple".to_string(),
        ("get", "/export_1h") => return "Export Last 1H".to_string(),
        ("post", "/export_1h") => return "Export Last 1H Post".to_string(),
        ("get", "/export_24h") => return "Export Last 24H".to_string(),
        ("post", "/export_24h") => return "Export Last 24H Post".to_string(),
        ("get", "/export_today") => return "Export Today".to_string(),
        ("post", "/export_today") => return "Export Today Post".to_string(),
        ("get", "/download_test") => return "Download File".to_string(),
        ("get", "/speedtest/download") => return "Download Test".to_string(),
        ("post", "/speedtest/upload") => return "Upload Test".to_string(),
        ("get", "/camera/status") => return "Get First Camera Status".to_string(),
        ("post", "/camera/params") => return "Set First Camera Params".to_string(),
        ("post", "/camera/reconnect") => return "Reconnect First Camera".to_string(),
        ("get", "/cameras") => return "Get Cameras Status".to_string(),
        ("get", "/cameras/{camera_key}/status") => return "Get Camera Status".to_string(),
        ("get", "/cameras/{camera_key}/files") => return "Get Camera Files".to_string(),
        ("post", "/cameras/{camera_key}/params") => return "Set Camera Params".to_string(),
        ("post", "/cameras/{camera_key}/reconnect") => return "Reconnect Camera".to_string(),
        ("get", "/capture/status") => return "Get Capture Status".to_string(),
        ("get", "/capture/files") => return "Get Capture Files".to_string(),
        ("get", "/getListenerAddFile") => return "Get Listener Add File".to_string(),
        ("get", "/coilAlarm/get_info") => return "Get Info".to_string(),
        ("get", "/coilAlarm/{coil_id}") => return "Get Coil Alarm".to_string(),
        ("get", "/alg_2d/models") => return "List Alg Models".to_string(),
        ("post", "/alg_2d/test/start") => return "Start Alg Test".to_string(),
        ("post", "/alg_2d/test/stop") => return "Stop Alg Test".to_string(),
        ("get", "/ws/alg_2d/test/progress") => {
            return "Get Alg 2D Test Progress".to_string();
        }
        ("get", "/reDetection/start/{from_id}/{to_id}") => {
            return "Http Re Detection Start".to_string();
        }
        ("get", "/reDetection/status") => return "Http Re Detection Status".to_string(),
        ("get", "/ws/reDetection") => return "WebSocket Re Detection".to_string(),
        ("get", "/ws/DetectionState") => return "WebSocket Detection State".to_string(),
        ("get", "/ws/backupImageTask") => return "WebSocket Backup Image Task".to_string(),
        ("get", "/ws/coilData/heightPoint") => return "WebSocket Height Point".to_string(),
        ("get", "/getServerState") => return "Get Server State".to_string(),
        ("get", "/coilData/heightData/{surface_key}/{coil_id}") => {
            return "Get Height Data".to_string();
        }
        ("get", "/coilData/heightPoint/{surface_key}/{coil_id}") => {
            return "Get Height Point".to_string();
        }
        ("get", "/coilData/Render/{surfaceKey}/{coil_id}") => return "Getrender".to_string(),
        ("get", "/coilData/Area/{surface_key}/{coil_id}") => return "Get Area".to_string(),
        ("get", "/coilData/Error/{surface_key}/{coil_id}") => return "Get Error".to_string(),
        ("get", "/image/preview/{surface_key}/{coil_id}/{type_}") => {
            return "Get Preview Image".to_string();
        }
        ("get", "/image/source/{surface_key}/{coil_id}/{type_}") => return "Get Image".to_string(),
        ("get", "/image/area/{surface_key}/{coil_id}")
        | ("get", "/image/area/{surface_key}/{coil_id}/{type_}") => {
            return "Get Area Tiled".to_string();
        }
        ("get", "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}") => {
            return "Get Classifier Image".to_string();
        }
        ("get", "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}") => {
            return "Get Defect Image".to_string();
        }
        _ => {}
    }

    let cleaned = route
        .path
        .trim_matches('/')
        .replace(['/', '{', '}'], " ")
        .replace('_', " ");
    if cleaned.is_empty() {
        "Read Root".to_string()
    } else {
        cleaned
            .split_whitespace()
            .map(|word| {
                let mut chars = word.chars();
                match chars.next() {
                    Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                    None => String::new(),
                }
            })
            .collect::<Vec<_>>()
            .join(" ")
    }
}

fn openapi_operation_id(method: &str, path: &str) -> String {
    match (method, path) {
        ("get", "/") => return "read_root__get".to_string(),
        ("get", "/currentCoil") => return "read_root_currentCoil_get".to_string(),
        ("get", "/health") => return "health_health_get".to_string(),
        ("get", "/version") => return "read_version_version_get".to_string(),
        ("get", "/delay") => return "get_delay_delay_get".to_string(),
        ("get", "/info") => return "info_info_get".to_string(),
        ("get", "/plc/info/") => return "info_plc_plc_info__get".to_string(),
        ("get", "/plc/info") => return "info_plc_info_get".to_string(),
        ("get", "/plc/connect/{plc_ip}/{rack}/{slot}") => {
            return "connect_plc_plc_connect__plc_ip__rack__slot_get".to_string();
        }
        ("get", "/plc/get/{addr}/{type_str}/{length}") => {
            return "forward_request_plc_get__addr___type_str___length__get".to_string();
        }
        ("get", "/runtime_info") => return "runtime_info_runtime_info_get".to_string(),
        ("get", "/grader_list") => return "grader_list_grader_list_get".to_string(),
        ("get", "/coil_list_value_change_keys") => {
            return "coil_list_value_change_keys_coil_list_value_change_keys_get".to_string();
        }
        ("get", "/database_info") => return "database_info_database_info_get".to_string(),
        ("get", "/control/config") => return "get_config_control_config_get".to_string(),
        ("post", "/control/set_config") => return "set_config_control_set_config_post".to_string(),
        ("get", "/control/set_property") => {
            return "set_property_control_set_property_get".to_string();
        }
        ("post", "/setDefectDict") => return "set_defect_dict_setDefectDict_post".to_string(),
        ("get", "/settings/test_mode") => {
            return "get_test_mode_settings_test_mode_get".to_string();
        }
        ("post", "/settings/test_mode") => {
            return "set_test_mode_settings_test_mode_post".to_string();
        }
        ("get", "/settings/test_mode_status") => {
            return "get_test_mode_status_settings_test_mode_status_get".to_string();
        }
        ("get", "/coilList/{number}") => return "get_coil_coilList__number__get".to_string(),
        ("get", "/flush/{coil_id}") => return "get_flush_flush__coil_id__get".to_string(),
        ("get", "/detail/{coil_id}") => {
            return "get_coil_detail_api_detail__coil_id__get".to_string();
        }
        ("get", "/defectDict") => return "get_defect_dict_defectDict_get".to_string(),
        ("get", "/defectDictAll") => return "get_defect_dict_all_defectDictAll_get".to_string(),
        ("get", "/data_has/{coil_id}") => return "get_daa_has_data_has__coil_id__get".to_string(),
        ("get", "/coilInfo/{coil_id}/{surface_key}") => {
            return "get_info_coilInfo__coil_id___surface_key__get".to_string();
        }
        ("get", "/search/coilNo/{coil_no}") => {
            return "search_by_coil_no_search_coilNo__coil_no__get".to_string();
        }
        ("get", "/search/coilId/{coil_id}") => {
            return "search_by_coil_id_search_coilId__coil_id__get".to_string();
        }
        ("get", "/search/DateTime/{start}/{end}") => {
            return "search_by_date_time_search_DateTime__start___end__get".to_string();
        }
        ("get", "/search/CoilState/{coil_id}") => {
            return "get_coil_state_search_CoilState__coil_id__get".to_string();
        }
        ("get", "/search/PlcData/{coil_id}") => {
            return "get_plc_data_search_PlcData__coil_id__get".to_string();
        }
        ("get", "/search/defects/{coil_id}/{direction}") => {
            return "get_defects_search_defects__coil_id___direction__get".to_string();
        }
        ("get", "/search/getDefectAll/{start_coil_id}/{end_coil_id}") => {
            return "get_defect_all_search_getDefectAll__start_coil_id___end_coil_id__get"
                .to_string();
        }
        ("get", "/search/defects_all/{coil_id}/{direction}") => {
            return "get_defects_all_including_manual_search_defects_all__coil_id___direction__get"
                .to_string();
        }
        ("get", "/manual_defects/{coil_id}/{direction}") => {
            return "get_manual_defects_api_manual_defects__coil_id___direction__get".to_string();
        }
        ("post", "/manual_defect/add") => {
            return "add_manual_defect_api_manual_defect_add_post".to_string();
        }
        ("put", "/manual_defect/update/{defect_id}") => {
            return "update_manual_defect_api_manual_defect_update__defect_id__put".to_string();
        }
        ("delete", "/manual_defect/delete/{defect_id}") => {
            return "delete_manual_defect_api_manual_defect_delete__defect_id__delete".to_string();
        }
        ("post", "/export_defects") => {
            return "export_defects_export_defects_post".to_string();
        }
        ("get", "/hardware") => return "get_hardware_hardware_get".to_string(),
        ("get", "/camera_adjust") => {
            return "get_camera_adjustments_camera_adjust_get".to_string();
        }
        ("post", "/camera_adjust/{camera_key}") => {
            return "set_camera_adjustment_camera_adjust__camera_key__post".to_string();
        }
        ("post", "/camera_adjust/{camera_key}/reconnect") => {
            return "reconnect_camera_adjustment_camera_adjust__camera_key__reconnect_post"
                .to_string();
        }
        ("get", "/camera/status") => return "get_camera_status_camera_status_get".to_string(),
        ("post", "/camera/params") => {
            return "set_camera_params_camera_params_post".to_string();
        }
        ("post", "/camera/reconnect") => {
            return "reconnect_camera_camera_reconnect_post".to_string();
        }
        ("get", "/cameras") => return "get_cameras_cameras_get".to_string(),
        ("get", "/cameras/{camera_key}/status") => {
            return "get_camera_status_by_key_cameras__camera_key__status_get".to_string();
        }
        ("get", "/cameras/{camera_key}/files") => {
            return "get_camera_files_by_key_cameras__camera_key__files_get".to_string();
        }
        ("post", "/cameras/{camera_key}/params") => {
            return "set_camera_params_by_key_cameras__camera_key__params_post".to_string();
        }
        ("post", "/cameras/{camera_key}/reconnect") => {
            return "reconnect_camera_by_key_cameras__camera_key__reconnect_post".to_string();
        }
        ("get", "/capture/status") => return "get_capture_status_compat_capture_status_get".to_string(),
        ("get", "/capture/files") => return "get_capture_files_capture_files_get".to_string(),
        ("get", "/getListenerAddFile") => {
            return "get_listener_add_file_get_listener_add_file_get".to_string();
        }
        ("get", "/capture_status") => return "get_capture_status_capture_status_get".to_string(),
        ("get", "/cameraAlarm") => return "get_camera_alarm_cameraAlarm_get".to_string(),
        ("get", "/cameraData/{coil_id}/{camera_key}") => {
            return "get_camera_data_cameraData__coil_id___camera_key__get".to_string();
        }
        ("get", "/backupImageTask/{from_id}/{to_id}/{save_folder}") => {
            return "backup_image_task_backupImageTask__from_id___to_id___save_folder__get"
                .to_string();
        }
        ("post", "/sync_summaries") => {
            return "sync_summaries_api_sync_summaries_post".to_string();
        }
        ("post", "/sync_summaries_range") => {
            return "sync_summaries_range_api_sync_summaries_range_post".to_string();
        }
        ("get", "/get_point_data/{coil_id}/{surface_key}") => {
            return "get_point_data_get_point_data__coil_id___surface_key__get".to_string();
        }
        ("get", "/get_line_data/{coil_id}/{surface_key}") => {
            return "get_line_data_get_line_data__coil_id___surface_key__get".to_string();
        }
        ("get", "/plc_curve/{field}") => return "get_plc_curve_plc_curve__field__get".to_string(),
        ("get", "/plc_curve_all") => return "get_plc_curve_all_plc_curve_all_get".to_string(),
        ("get", "/check/get_coil_status/{coil_id}") => {
            return "get_coil_status_check_get_coil_status__coil_id__get".to_string();
        }
        ("get", "/check/set_coil_status/{coil_id}/{status}") => {
            return "set_coil_status_check_set_coil_status__coil_id___status__get".to_string();
        }
        ("get", "/check/set_coil_status/{coil_id}/{status}/{msg}") => {
            return "set_coil_status_check_set_coil_status__coil_id___status___msg__get"
                .to_string();
        }
        ("get", "/save_to_sql/{sql_file}") => {
            return "save_to_sql_save_to_sql__sql_file__get".to_string();
        }
        ("get", "/exportXlsxById/{start}/{end}") => {
            return "export_xlsx_by_id_exportXlsxById__start___end__get".to_string();
        }
        ("get", "/exportXlsxByDateTime/{start}/{end}") => {
            return "export_xlsx_by_datetime_exportXlsxByDateTime__start___end__get".to_string();
        }
        ("post", "/export_xlsx") => return "export_xlsx_post_export_xlsx_post".to_string(),
        ("get", "/exportDataSimple") => {
            return "export_data_simple_exportDataSimple_get".to_string();
        }
        ("get", "/export_1h") => return "export_last_1h_export_1h_get".to_string(),
        ("post", "/export_1h") => return "export_last_1h_post_export_1h_post".to_string(),
        ("get", "/export_24h") => return "export_last_24h_export_24h_get".to_string(),
        ("post", "/export_24h") => return "export_last_24h_post_export_24h_post".to_string(),
        ("get", "/export_today") => return "export_today_export_today_get".to_string(),
        ("post", "/export_today") => return "export_today_post_export_today_post".to_string(),
        ("get", "/download_test") => return "download_file_download_test_get".to_string(),
        ("get", "/speedtest/download") => {
            return "download_test_speedtest_download_get".to_string();
        }
        ("post", "/speedtest/upload") => {
            return "upload_test_speedtest_upload_post".to_string();
        }
        ("get", "/coilAlarm/get_info") => return "get_info_coilAlarm_get_info_get".to_string(),
        ("get", "/coilAlarm/{coil_id}") => {
            return "get_coil_alarm_coilAlarm__coil_id__get".to_string();
        }
        ("get", "/alg_2d/models") => return "list_alg_models_alg_2d_models_get".to_string(),
        ("post", "/alg_2d/test/start") => {
            return "start_alg_test_alg_2d_test_start_post".to_string();
        }
        ("post", "/alg_2d/test/stop") => {
            return "stop_alg_test_alg_2d_test_stop_post".to_string();
        }
        ("get", "/ws/alg_2d/test/progress") => {
            return "websocket_alg_2d_test_progress_ws_alg_2d_test_progress_get".to_string();
        }
        ("get", "/reDetection/start/{from_id}/{to_id}") => {
            return "http_re_detection_start_reDetection_start__from_id___to_id__get".to_string();
        }
        ("get", "/reDetection/status") => {
            return "http_re_detection_status_reDetection_status_get".to_string();
        }
        ("get", "/ws/reDetection") => {
            return "websocket_re_detection_ws_reDetection_get".to_string();
        }
        ("get", "/ws/DetectionState") => {
            return "websocket_detection_state_ws_DetectionState_get".to_string();
        }
        ("get", "/ws/backupImageTask") => {
            return "websocket_backup_image_task_ws_backupImageTask_get".to_string();
        }
        ("get", "/ws/coilData/heightPoint") => {
            return "websocket_coil_data_heightPoint_ws_coilData_heightPoint_get".to_string();
        }
        ("get", "/getServerState") => return "get_server_state_getServerState_get".to_string(),
        ("get", "/coilData/heightData/{surface_key}/{coil_id}") => {
            return "get_height_data_coilData_heightData__surface_key___coil_id__get".to_string();
        }
        ("get", "/coilData/heightPoint/{surface_key}/{coil_id}") => {
            return "get_height_point_coilData_heightPoint__surface_key___coil_id__get".to_string();
        }
        ("get", "/coilData/Render/{surfaceKey}/{coil_id}") => {
            return "getRender_coilData_Render__surfaceKey___coil_id__get".to_string();
        }
        ("get", "/coilData/Area/{surface_key}/{coil_id}") => {
            return "get_area_coilData_Area__surface_key___coil_id__get".to_string();
        }
        ("get", "/coilData/Error/{surface_key}/{coil_id}") => {
            return "get_error_coilData_Error__surface_key___coil_id__get".to_string();
        }
        ("get", "/image/preview/{surface_key}/{coil_id}/{type_}") => {
            return "get_preview_image_image_preview__surface_key___coil_id___type___get"
                .to_string();
        }
        ("get", "/image/source/{surface_key}/{coil_id}/{type_}") => {
            return "get_image_image_source__surface_key___coil_id___type___get".to_string();
        }
        ("get", "/image/area/{surface_key}/{coil_id}") => {
            return "get_area_tiled_image_area__surface_key___coil_id__get".to_string();
        }
        ("get", "/image/area/{surface_key}/{coil_id}/{type_}") => {
            return "get_area_tiled_image_area__surface_key___coil_id___type___get".to_string();
        }
        ("get", "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}") => {
            return "get_classifier_image_classifier_image__coil_id___surface_key___class_name___x___y___w___h__get".to_string();
        }
        ("get", "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}") => {
            return "get_defect_image_defect_image__surface_key___coil_id___type____x___y___w___h__get".to_string();
        }
        _ => {}
    }

    let mut output = method.to_string();
    for ch in path.chars() {
        if ch.is_ascii_alphanumeric() {
            output.push('_');
            output.push(ch.to_ascii_lowercase());
        } else if !output.ends_with('_') {
            output.push('_');
        }
    }
    output.trim_matches('_').to_string()
}

fn openapi_path_parameters(path: &str) -> Vec<Value> {
    let mut parameters = Vec::new();
    for segment in path.split('{').skip(1) {
        let Some(name) = segment.split('}').next() else {
            continue;
        };
        if name.is_empty() {
            continue;
        }
        parameters.push(json!({
            "name": name,
            "in": "path",
            "required": true,
            "schema": {
                "type": openapi_path_parameter_type(name),
                "title": openapi_parameter_title(name),
            },
        }));
    }
    parameters
}

fn openapi_parameters(route: &OpenApiRoute) -> Vec<Value> {
    match route.path {
        "/plc/connect/{plc_ip}/{rack}/{slot}" => vec![
            openapi_path_parameter_without_type("plc_ip"),
            openapi_path_parameter("rack", "integer"),
            openapi_path_parameter("slot", "integer"),
        ],
        "/plc/get/{addr}/{type_str}/{length}" => vec![
            openapi_path_parameter_without_type("addr"),
            openapi_path_parameter_without_type("type_str"),
            openapi_path_parameter("length", "integer"),
        ],
        "/coilData/heightData/{surface_key}/{coil_id}" => vec![
            openapi_path_parameter_without_type("surface_key"),
            openapi_path_parameter("coil_id", "string"),
            openapi_integer_query_parameter("x1", 0),
            openapi_integer_query_parameter("y1", 0),
            openapi_integer_query_parameter("x2", 0),
            openapi_integer_query_parameter("y2", 0),
        ],
        "/coilData/heightPoint/{surface_key}/{coil_id}" => vec![
            openapi_path_parameter_without_type("surface_key"),
            openapi_path_parameter("coil_id", "string"),
            openapi_integer_query_parameter("x", 0),
            openapi_integer_query_parameter("y", 0),
        ],
        "/coilData/Render/{surfaceKey}/{coil_id}" => openapi_render_query_parameters(),
        "/coilData/Area/{surface_key}/{coil_id}" => openapi_area_query_parameters(),
        "/coilData/Error/{surface_key}/{coil_id}" => openapi_error_query_parameters(),
        "/image/preview/{surface_key}/{coil_id}/{type_}" => openapi_image_file_query_parameters(),
        "/image/source/{surface_key}/{coil_id}/{type_}" => openapi_image_file_query_parameters(),
        "/image/area/{surface_key}/{coil_id}" => openapi_image_area_query_parameters(false),
        "/image/area/{surface_key}/{coil_id}/{type_}" => openapi_image_area_query_parameters(true),
        "/check/get_coil_status/{coil_id}" => {
            vec![openapi_path_parameter_without_type("coil_id")]
        }
        "/check/set_coil_status/{coil_id}/{status}" => openapi_set_coil_status_query_parameters(),
        "/check/set_coil_status/{coil_id}/{status}/{msg}" => {
            openapi_set_coil_status_path_parameters()
        }
        "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}" => {
            openapi_defect_image_query_parameters()
        }
        "/exportXlsxByDateTime/{start}/{end}" | "/exportXlsxById/{start}/{end}" => {
            openapi_export_xlsx_query_parameters()
        }
        "/search/getDefectAll/{start_coil_id}/{end_coil_id}" => vec![
            openapi_path_parameter_without_type("start_coil_id"),
            openapi_path_parameter_without_type("end_coil_id"),
        ],
        "/coilList/{number}" => vec![
            openapi_path_parameter("number", "integer"),
            openapi_query_parameter_without_type("coil_id"),
            openapi_query_parameter_with_default("rev", json!(true)),
        ],
        "/clipMaxImage/{coil_id}/{key}" => vec![
            openapi_path_parameter("coil_id", "integer"),
            openapi_path_parameter("key", "string"),
            openapi_query_parameter_without_type("save_url"),
        ],
        "/grader_list" => vec![openapi_integer_query_parameter("count", 100)],
        "/speedtest/download" => vec![openapi_integer_query_parameter("size_in_mb", 10)],
        "/plc_curve_all" => openapi_plc_curve_query_parameters(),
        "/plc_curve/{field}" => {
            let mut parameters = openapi_path_parameters(route.path);
            parameters.extend(openapi_plc_curve_query_parameters());
            parameters
        }
        "/control/set_property" => vec![
            openapi_required_query_parameter_without_type("key"),
            openapi_required_query_parameter_without_type("value"),
        ],
        "/capture/files" | "/getListenerAddFile" => {
            vec![openapi_typed_query_parameter_with_default(
                "clear",
                "boolean",
                json!(false),
                "Clear",
            )]
        }
        "/cameras/{camera_key}/files" => {
            vec![openapi_typed_query_parameter_with_default(
                "clear",
                "boolean",
                json!(false),
                "Clear",
            )]
        }
        _ => openapi_path_parameters(route.path),
    }
}

fn openapi_path_parameter(name: &str, type_name: &str) -> Value {
    json!({
        "name": name,
        "in": "path",
        "required": true,
        "schema": {
            "type": type_name,
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_path_parameter_without_type(name: &str) -> Value {
    json!({
        "name": name,
        "in": "path",
        "required": true,
        "schema": {
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_integer_query_parameter(name: &str, default: i32) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "type": "integer",
            "default": default,
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_query_parameter_without_type(name: &str) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_required_query_parameter_without_type(name: &str) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": true,
        "schema": {
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_query_parameter_with_default(name: &str, default: Value) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "default": default,
            "title": openapi_parameter_title(name),
        },
    })
}

fn openapi_plc_curve_query_parameters() -> Vec<Value> {
    vec![
        openapi_integer_query_parameter("start_id", 0),
        openapi_integer_query_parameter("end_id", 0),
        openapi_integer_query_parameter("limit", 200),
    ]
}

fn openapi_render_query_parameters() -> Vec<Value> {
    vec![
        json!({
            "name": "surfaceKey",
            "in": "path",
            "required": true,
            "schema": {"type": "string", "title": "Surfacekey"},
        }),
        openapi_path_parameter("coil_id", "string"),
        openapi_described_query_parameter("scale", "number", json!(1.0), "Scale", "缩放比例"),
        openapi_described_query_parameter("mask", "boolean", json!(true), "Mask", "是否应用掩码"),
        openapi_described_query_parameter("min_value", "integer", json!(0), "Min Value", "最小值"),
        openapi_described_query_parameter(
            "max_value",
            "integer",
            json!(255),
            "Max Value",
            "最大值",
        ),
        openapi_nullable_integer_query_parameter("minValue", "Minvalue", "兼容 QML 旧参数：最小值"),
        openapi_nullable_integer_query_parameter("maxValue", "Maxvalue", "兼容 QML 旧参数：最大值"),
        openapi_described_query_parameter(
            "thumbnail",
            "boolean",
            json!(false),
            "Thumbnail",
            "是否返回缩略图（1024x1024）",
        ),
        openapi_described_query_parameter(
            "grayscale",
            "boolean",
            json!(false),
            "Grayscale",
            "是否使用灰度模式（GRAY）而非伪彩色（JET）",
        ),
    ]
}

fn openapi_area_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("surface_key"),
        openapi_path_parameter("coil_id", "string"),
        openapi_query_parameter_with_default("scale", json!(1)),
        openapi_typed_query_parameter_with_default("mask", "boolean", json!(true), "Mask"),
        openapi_query_parameter_with_default_and_title("valueFrom", json!(0), "Valuefrom"),
        openapi_query_parameter_with_default_and_title("valueTo", json!(255), "Valueto"),
        openapi_query_parameter_with_default("r", json!(255)),
        openapi_query_parameter_with_default("g", json!(0)),
        openapi_query_parameter_with_default("b", json!(0)),
    ]
}

fn openapi_error_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter("surface_key", "string"),
        openapi_path_parameter("coil_id", "string"),
        openapi_typed_query_parameter_with_default("scale", "number", json!(1.0), "Scale"),
        openapi_typed_query_parameter_with_default("mask", "boolean", json!(true), "Mask"),
        openapi_typed_query_parameter_with_default("minValue", "number", json!(0), "Minvalue"),
        openapi_typed_query_parameter_with_default("maxValue", "number", json!(255), "Maxvalue"),
        openapi_typed_query_parameter_with_default(
            "force_cache",
            "boolean",
            json!(false),
            "Force Cache",
        ),
    ]
}

fn openapi_image_file_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("surface_key"),
        openapi_path_parameter("coil_id", "string"),
        openapi_path_parameter_with_title("type_", "string", "Type "),
        openapi_typed_query_parameter_with_default("mask", "boolean", json!(false), "Mask"),
    ]
}

fn openapi_image_area_query_parameters(has_path_type: bool) -> Vec<Value> {
    let mut parameters = vec![
        openapi_path_parameter("surface_key", "string"),
        openapi_path_parameter("coil_id", "string"),
    ];
    if has_path_type {
        parameters.push(openapi_path_parameter_with_title(
            "type_", "string", "Type ",
        ));
    } else {
        parameters.push(openapi_typed_query_parameter_with_default(
            "type_",
            "string",
            json!("AREA"),
            "Type ",
        ));
    }
    parameters.extend([
        openapi_ranged_tile_query_parameter("row", -2, 2, 0, "Row", "瓦片行索引"),
        openapi_ranged_tile_query_parameter("col", 0, 2, 0, "Col", "瓦片列索引"),
        openapi_ranged_tile_query_parameter("count", 0, 3, 0, "Count", "瓦片行列数"),
        openapi_ranged_tile_query_parameter("level", 0, 4, 4, "Level", "瓦片质量等级 0-4"),
    ]);
    parameters
}

fn openapi_set_coil_status_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("coil_id"),
        openapi_path_parameter_without_type("status"),
        openapi_query_parameter_with_default("msg", json!("")),
    ]
}

fn openapi_set_coil_status_path_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("coil_id"),
        openapi_path_parameter_without_type("status"),
        openapi_path_parameter_without_type("msg"),
    ]
}

fn openapi_defect_image_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("surface_key"),
        openapi_path_parameter("coil_id", "integer"),
        openapi_path_parameter_with_title("type_", "string", "Type "),
        openapi_path_parameter("x", "string"),
        openapi_path_parameter("y", "string"),
        openapi_path_parameter("w", "string"),
        openapi_path_parameter("h", "string"),
    ]
}

fn openapi_export_xlsx_query_parameters() -> Vec<Value> {
    vec![
        openapi_path_parameter_without_type("start"),
        openapi_path_parameter_without_type("end"),
        openapi_query_parameter_with_default("export_type", json!("3D")),
        openapi_query_parameter_without_type("export_config"),
    ]
}

fn openapi_described_query_parameter(
    name: &str,
    type_name: &str,
    default: Value,
    title: &str,
    description: &str,
) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "type": type_name,
            "description": description,
            "default": default,
            "title": title,
        },
        "description": description,
    })
}

fn openapi_path_parameter_with_title(name: &str, type_name: &str, title: &str) -> Value {
    json!({
        "name": name,
        "in": "path",
        "required": true,
        "schema": {
            "type": type_name,
            "title": title,
        },
    })
}

fn openapi_query_parameter_with_default_and_title(
    name: &str,
    default: Value,
    title: &str,
) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "default": default,
            "title": title,
        },
    })
}

fn openapi_typed_query_parameter_with_default(
    name: &str,
    type_name: &str,
    default: Value,
    title: &str,
) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "type": type_name,
            "default": default,
            "title": title,
        },
    })
}

fn openapi_ranged_tile_query_parameter(
    name: &str,
    minimum: i32,
    maximum: i32,
    default: i32,
    title: &str,
    description: &str,
) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "type": "integer",
            "maximum": maximum,
            "minimum": minimum,
            "description": description,
            "default": default,
            "title": title,
        },
        "description": description,
    })
}

fn openapi_nullable_integer_query_parameter(name: &str, title: &str, description: &str) -> Value {
    json!({
        "name": name,
        "in": "query",
        "required": false,
        "schema": {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "description": description,
            "title": title,
        },
        "description": description,
    })
}

fn openapi_responses(route: &OpenApiRoute, include_validation_error: bool) -> Value {
    let mut responses = Map::new();
    let content = openapi_success_response_content(route);
    responses.insert(
        "200".to_string(),
        json!({
            "description": "Successful Response",
            "content": content,
        }),
    );
    if include_validation_error {
        responses.insert("422".to_string(), openapi_validation_error_response());
    }
    Value::Object(responses)
}

fn openapi_success_response_content(route: &OpenApiRoute) -> Value {
    match (route.method, route.path) {
        ("get", "/ws/alg_2d/test/progress") => {
            json!({"application/json": {"schema": {"type": "object", "additionalProperties": true}}})
        }
        ("get", "/ws/coilData/heightPoint") => {
            json!({"application/json": {"schema": {"type": "object", "additionalProperties": true}}})
        }
        ("get", "/ws/DetectionState") => {
            json!({"application/json": {"schema": {"$ref": "#/components/schemas/ServerStateResponse"}}})
        }
        ("get", "/ws/reDetection") => {
            json!({"application/json": {"schema": {"$ref": "#/components/schemas/ReDetectionStatusResponse"}}})
        }
        ("get", "/ws/backupImageTask") => {
            json!({"text/plain": {"schema": {"type": "string"}}})
        }
        ("get", "/updates/{file_name}") => {
            openapi_binary_response_content(&["application/octet-stream"])
        }
        ("get", "/download_test") => {
            json!({
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"},
                },
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorMessageResponse"},
                },
            })
        }
        ("get", "/speedtest/download") => {
            openapi_binary_response_content(&["application/octet-stream"])
        }
        ("get", "/coilData/Area/{surface_key}/{coil_id}")
        | ("get", "/coilData/Error/{surface_key}/{coil_id}") => {
            openapi_binary_response_content(&["image/png"])
        }
        ("get", "/coilData/Render/{surfaceKey}/{coil_id}")
        | ("get", "/image/preview/{surface_key}/{coil_id}/{type_}")
        | ("get", "/image/source/{surface_key}/{coil_id}/{type_}")
        | ("get", "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}")
        | ("get", "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}") => {
            openapi_binary_response_content(&["image/jpeg", "image/png"])
        }
        ("get", "/image/area/{surface_key}/{coil_id}")
        | ("get", "/image/area/{surface_key}/{coil_id}/{type_}") => {
            json!({
                "image/jpeg": {
                    "schema": {"type": "string", "format": "binary"},
                },
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AreaImageMetadataResponse"},
                },
            })
        }
        ("get", "/exportXlsxById/{start}/{end}")
        | ("get", "/exportXlsxByDateTime/{start}/{end}")
        | ("post", "/export_xlsx")
        | ("get", "/exportDataSimple")
        | ("get", "/export_1h")
        | ("post", "/export_1h")
        | ("get", "/export_24h")
        | ("post", "/export_24h")
        | ("get", "/export_today")
        | ("post", "/export_today") => json!({
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                "schema": {"type": "string", "format": "binary"},
            },
        }),
        _ => json!({
            "application/json": {
                "schema": openapi_success_response_schema(route),
            },
        }),
    }
}

fn openapi_binary_response_content(content_types: &[&str]) -> Value {
    let mut content = Map::new();
    for content_type in content_types {
        content.insert(
            (*content_type).to_string(),
            json!({"schema": {"type": "string", "format": "binary"}}),
        );
    }
    Value::Object(content)
}

fn openapi_success_response_schema(route: &OpenApiRoute) -> Value {
    match (route.method, route.path) {
        ("get", "/") => {
            json!({"$ref": "#/components/schemas/RootResponse"})
        }
        ("get", "/version") => {
            json!({"type": "string", "title": "Version"})
        }
        ("get", "/delay") => {
            json!({"type": "integer", "title": "Delay"})
        }
        ("get", "/database_info") => {
            json!({"$ref": "#/components/schemas/DatabaseInfoResponse"})
        }
        ("get", "/info") => {
            json!({"$ref": "#/components/schemas/InfoResponse"})
        }
        ("get", "/plc/info/") | ("get", "/plc/info") => {
            json!({"$ref": "#/components/schemas/PlcInfoResponse"})
        }
        ("get", "/plc/connect/{plc_ip}/{rack}/{slot}") => {
            json!({"type": "boolean", "title": "PlcConnectionResponse"})
        }
        ("get", "/plc/get/{addr}/{type_str}/{length}") => {
            json!({"$ref": "#/components/schemas/PlcGetValueResponse"})
        }
        ("get", "/defectDict") => {
            json!({"$ref": "#/components/schemas/DefectDictionaryResponse"})
        }
        ("get", "/defectClasses") => {
            json!({"$ref": "#/components/schemas/DefectDictionaryResponse"})
        }
        ("get", "/defectDictAll") => {
            json!({
                "items": {"$ref": "#/components/schemas/DefectDictionaryRow"},
                "type": "array",
                "title": "Response Get Defect Dict All Defectdictall Get",
            })
        }
        ("post", "/setDefectDict") => {
            json!({"$ref": "#/components/schemas/SetDefectDictionaryResponse"})
        }
        ("get", "/coilList/{number}") => {
            json!({
                "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
                "type": "array",
                "title": "Response Get Coil Coillist  Number  Get",
            })
        }
        ("get", "/flush/{coil_id}") => {
            json!({"$ref": "#/components/schemas/FlushCoilListResponse"})
        }
        ("get", "/search/coilId/{coil_id}")
        | ("get", "/search/coilNo/{coil_no}")
        | ("get", "/search/DateTime/{start}/{end}") => {
            json!({
                "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
                "type": "array",
                "title": "Response Coil Summary List",
            })
        }
        ("get", "/detail/{coil_id}") => {
            json!({
                "anyOf": [
                    {"$ref": "#/components/schemas/CoilDetailResponse"},
                    {"$ref": "#/components/schemas/ErrorMessageResponse"},
                ],
                "title": "Response Get Coil Detail Api Detail  Coil Id  Get",
            })
        }
        ("get", "/grader_list") => {
            json!({
                "items": {"$ref": "#/components/schemas/GraderListItem"},
                "type": "array",
                "title": "Response Grader List",
            })
        }
        ("post", "/sync_summaries") | ("post", "/sync_summaries_range") => {
            json!({"$ref": "#/components/schemas/SyncSummariesResponse"})
        }
        ("get", "/coilInfo/{coil_id}/{surface_key}") => {
            json!({
                "anyOf": [
                    {"$ref": "#/components/schemas/CoilInfoResponse"},
                    {"type": "null"},
                ],
                "title": "Response Get Info Coilinfo  Coil Id   Surface Key  Get",
            })
        }
        ("get", "/coilData/heightData/{surface_key}/{coil_id}") => {
            json!({
                "items": {"$ref": "#/components/schemas/HeightDataSegment"},
                "type": "array",
                "title": "Response Height Data Segments",
            })
        }
        ("get", "/coilData/heightPoint/{surface_key}/{coil_id}") => {
            json!({"$ref": "#/components/schemas/HeightPointResponse"})
        }
        ("get", "/search/CoilState/{coil_id}") => {
            json!({
                "items": {"$ref": "#/components/schemas/CoilStateItem"},
                "type": "array",
                "title": "Response Coil State List",
            })
        }
        ("get", "/search/PlcData/{coil_id}") => {
            json!({
                "anyOf": [
                    {"$ref": "#/components/schemas/PlcDataItem"},
                    {"type": "null"},
                ],
                "title": "Response Get Plc Data Search Plcdata  Coil Id  Get",
            })
        }
        ("get", "/get_point_data/{coil_id}/{surface_key}") => {
            json!({
                "items": {"$ref": "#/components/schemas/PointDataItem"},
                "type": "array",
                "title": "Response Point Data List",
            })
        }
        ("get", "/get_line_data/{coil_id}/{surface_key}") => {
            json!({
                "items": {"$ref": "#/components/schemas/LineDataItem"},
                "type": "array",
                "title": "Response Line Data List",
            })
        }
        ("get", "/search/defects/{coil_id}/{direction}")
        | ("get", "/search/getDefectAll/{start_coil_id}/{end_coil_id}") => {
            json!({
                "items": {"$ref": "#/components/schemas/DefectItem"},
                "type": "array",
                "title": "Response Defect List",
            })
        }
        ("get", "/search/defects_all/{coil_id}/{direction}") => {
            json!({
                "items": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/AutoDefectItem"},
                        {"$ref": "#/components/schemas/ManualDefectItem"},
                    ],
                },
                "type": "array",
                "title": "Response Defect List Including Manual",
            })
        }
        ("get", "/manual_defects/{coil_id}/{direction}") => {
            json!({
                "items": {"$ref": "#/components/schemas/ManualDefectItem"},
                "type": "array",
                "title": "Response Manual Defect List",
            })
        }
        ("post", "/manual_defect/add") | ("put", "/manual_defect/update/{defect_id}") => {
            json!({"$ref": "#/components/schemas/ManualDefectMutationResponse"})
        }
        ("delete", "/manual_defect/delete/{defect_id}") => {
            json!({"$ref": "#/components/schemas/DeleteManualDefectResponse"})
        }
        ("post", "/export_defects") => {
            json!({"$ref": "#/components/schemas/ExportDefectsResponse"})
        }
        ("get", "/control/config") => {
            json!({"$ref": "#/components/schemas/ControlConfigResponse"})
        }
        ("post", "/control/set_config") | ("get", "/control/set_property") => {
            json!({"type": "null"})
        }
        ("post", "/speedtest/upload") => {
            json!({"$ref": "#/components/schemas/SpeedTestUploadResponse"})
        }
        ("get", "/cameraData/{coil_id}/{camera_key}") => {
            json!({"$ref": "#/components/schemas/CameraDataResponse"})
        }
        ("get", "/check/get_coil_status/{coil_id}") => {
            json!({"$ref": "#/components/schemas/CoilCheckResponse"})
        }
        ("get", "/check/set_coil_status/{coil_id}/{status}")
        | ("get", "/check/set_coil_status/{coil_id}/{status}/{msg}") => {
            json!({"type": "null"})
        }
        ("get", "/coil_list_value_change_keys") => {
            json!({
                "items": {"type": "string"},
                "type": "array",
                "title": "Response Coil List Value Change Keys Coil List Value Change Keys Get",
            })
        }
        ("get", "/data_has/{coil_id}") => {
            json!({"$ref": "#/components/schemas/DataHasResponse"})
        }
        ("get", "/coilAlarm/get_info") => {
            json!({"type": "null"})
        }
        ("get", "/cameras") | ("get", "/capture/status") => {
            json!({"$ref": "#/components/schemas/CaptureStatusResponse"})
        }
        ("get", "/coilAlarm/{coil_id}") => {
            json!({"$ref": "#/components/schemas/CoilAlarmResponse"})
        }
        ("get", "/plc_curve/{field}") => {
            json!({"$ref": "#/components/schemas/PlcCurveResponse"})
        }
        ("get", "/plc_curve_all") => {
            json!({"$ref": "#/components/schemas/PlcCurveAllResponse"})
        }
        ("get", "/software_update/manifest") => {
            json!({"$ref": "#/components/schemas/SoftwareUpdateManifest"})
        }
        ("get", "/health") => {
            json!({"$ref": "#/components/schemas/HealthResponse"})
        }
        ("get", "/runtime_info") => {
            json!({"$ref": "#/components/schemas/RuntimeInfoResponse"})
        }
        ("get", "/hardware") => {
            json!({"$ref": "#/components/schemas/HardwareStatusResponse"})
        }
        ("get", "/camera_adjust") => {
            json!({"$ref": "#/components/schemas/CameraAdjustmentStatusResponse"})
        }
        ("get", "/camera/status") => {
            json!({"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"})
        }
        ("get", "/capture_status") => {
            json!({"$ref": "#/components/schemas/CaptureStatusResponse"})
        }
        ("get", "/cameras/{camera_key}/status") => {
            json!({"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"})
        }
        ("get", "/capture/files") | ("get", "/getListenerAddFile") => {
            json!({"type": "object", "title": "CaptureFiles"})
        }
        ("get", "/cameraAlarm") => {
            json!({"$ref": "#/components/schemas/CameraAlarmResponse"})
        }
        ("post", "/camera_adjust/{camera_key}")
        | ("post", "/camera/params")
        | ("post", "/camera/reconnect")
        | ("post", "/cameras/{camera_key}/params")
        | ("post", "/cameras/{camera_key}/reconnect")
        | ("post", "/camera_adjust/{camera_key}/reconnect") => {
            json!({"$ref": "#/components/schemas/CameraActionResponse"})
        }
        ("get", "/settings/test_mode") => {
            json!({"$ref": "#/components/schemas/TestModeResponse"})
        }
        ("post", "/settings/test_mode") => {
            json!({"$ref": "#/components/schemas/SetTestModeResponse"})
        }
        ("get", "/currentCoil") | ("get", "/cameras/{camera_key}/files") => {
            json!({
                "type": "object",
                "additionalProperties": true
            })
        }
        ("get", "/settings/test_mode_status") => {
            json!({"$ref": "#/components/schemas/TestModeStatusResponse"})
        }
        ("get", "/area/status") | ("post", "/area/scan") => {
            json!({"$ref": "#/components/schemas/AreaStatusResponse"})
        }
        ("get", "/alg_2d/models") => {
            json!({"$ref": "#/components/schemas/AlgModelListResponse"})
        }
        ("get", "/getServerState") => {
            json!({"$ref": "#/components/schemas/ServerStateResponse"})
        }
        ("post", "/clip_config") => {
            json!({"$ref": "#/components/schemas/ClipConfigResponse"})
        }
        ("post", "/area/rejoin") => {
            json!({"$ref": "#/components/schemas/AreaRejoinResponse"})
        }
        ("post", "/alg_2d/test/start") => {
            json!({"$ref": "#/components/schemas/AlgTestStartResponse"})
        }
        ("post", "/alg_2d/test/stop") => {
            json!({"$ref": "#/components/schemas/AlgTestStopResponse"})
        }
        ("get", "/reDetection/status") | ("get", "/reDetection/start/{from_id}/{to_id}") => {
            json!({"$ref": "#/components/schemas/ReDetectionStatusResponse"})
        }
        ("get", "/save_to_sql/{sql_file}") => {
            json!({"$ref": "#/components/schemas/SaveToSqlResponse"})
        }
        ("get", "/clipMaxImage/{coil_id}/{key}")
        | ("get", "/backupImageTask/{from_id}/{to_id}/{save_folder}") => json!({"type": "null"}),
        _ => json!({}),
    }
}

fn openapi_validation_error_response() -> Value {
    json!({
        "description": "Validation Error",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HTTPValidationError"},
            },
        },
    })
}

fn openapi_component_schemas() -> Value {
    json!({
        "HTTPValidationError": {
            "properties": {
                "detail": {
                    "items": {"$ref": "#/components/schemas/ValidationError"},
                    "type": "array",
                    "title": "Detail",
                },
            },
            "type": "object",
            "title": "HTTPValidationError",
        },
        "ValidationError": {
            "properties": {
                "loc": {
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                    },
                    "type": "array",
                    "title": "Location",
                },
                "msg": {
                    "type": "string",
                    "title": "Message",
                },
                "type": {
                    "type": "string",
                    "title": "Error Type",
                },
                "input": {
                    "title": "Input",
                },
                "ctx": {
                    "type": "object",
                    "title": "Context",
                },
            },
            "type": "object",
            "required": ["loc", "msg", "type"],
            "title": "ValidationError",
        },
        "CameraAdjustmentPayload": {
            "properties": {
                "exposureTime": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Exposuretime",
                },
                "gain": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Gain",
                },
                "save": {"type": "boolean", "title": "Save", "default": true},
            },
            "type": "object",
            "title": "CameraAdjustmentPayload",
        },
        "ExportXlsxConfigModel": {
            "properties": {
                "export_type": {"type": "string", "title": "Export Type"},
                "detection_3d_info": {"type": "boolean", "title": "Detection 3D Info"},
                "defect_info": {"type": "boolean", "title": "Defect Info"},
                "defect_show_info": {"type": "boolean", "title": "Defect Show Info"},
                "defect_un_show_info": {"type": "boolean", "title": "Defect Un Show Info"},
                "area_defect_image": {
                    "type": "boolean",
                    "title": "Area Defect Image",
                    "default": true,
                },
                "export_plc_data": {"type": "boolean", "title": "Export Plc Data"},
                "startDate": {"type": "string", "title": "Startdate"},
                "endDate": {"type": "string", "title": "Enddate"},
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
                "endDate",
            ],
            "title": "ExportXlsxConfigModel",
        },
        "TestModeRequest": {
            "properties": {
                "enabled": {"type": "boolean", "title": "Enabled"},
            },
            "type": "object",
            "required": ["enabled"],
            "title": "TestModeRequest",
        },
        "HealthResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "service": {"type": "string", "title": "Service"},
            },
            "type": "object",
            "required": ["status", "service"],
            "title": "HealthResponse",
        },
        "RootResponse": {
            "properties": {
                "/docs": {"type": "string", "title": "Docs"},
            },
            "type": "object",
            "required": ["/docs"],
            "title": "RootResponse",
        },
        "DatabaseInfoResponse": {
            "properties": {
                "url": {"$ref": "#/components/schemas/DatabaseUrlInfo"},
                "echo": {"type": "boolean", "title": "Echo"},
                "coil_last": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "null"},
                    ],
                    "title": "Coil Last",
                },
            },
            "type": "object",
            "required": ["url", "echo", "coil_last"],
            "title": "DatabaseInfoResponse",
        },
        "DatabaseUrlInfo": {
            "prefixItems": [
                {"type": "string", "title": "Driver"},
                {"type": "string", "title": "Username"},
                {"type": "string", "title": "Password"},
                {"type": "string", "title": "Host"},
                {"type": "integer", "title": "Port"},
                {"type": "string", "title": "Database"},
                {"type": "object", "title": "Query", "additionalProperties": true},
            ],
            "type": "array",
            "minItems": 7,
            "maxItems": 7,
            "title": "DatabaseUrlInfo",
        },
        "InfoResponse": {
            "properties": {
                "ErrorMap": {"$ref": "#/components/schemas/InfoErrorMap"},
                "RendererList": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Rendererlist",
                },
                "ColorMaps": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                    "title": "Colormaps",
                },
                "SaveImageType": {"type": "string", "title": "Saveimagetype"},
                "PreviewSize": {
                    "prefixItems": [
                        {"type": "integer", "title": "Width"},
                        {"type": "integer", "title": "Height"},
                    ],
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "title": "Previewsize",
                },
                "surfaceS": {"$ref": "#/components/schemas/InfoSurface"},
                "surfaceL": {"$ref": "#/components/schemas/InfoSurface"},
            },
            "type": "object",
            "required": [
                "ErrorMap",
                "RendererList",
                "ColorMaps",
                "SaveImageType",
                "PreviewSize",
            ],
            "additionalProperties": true,
            "title": "InfoResponse",
        },
        "PlcInfoResponse": {
            "properties": {
                "typeList": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Typelist",
                },
                "plc_ip": {"type": "string", "title": "Plc Ip"},
                "rack": {"type": "integer", "title": "Rack"},
                "slot": {"type": "integer", "title": "Slot"},
            },
            "type": "object",
            "required": ["typeList", "plc_ip", "rack", "slot"],
            "title": "PlcInfoResponse",
        },
        "PlcGetValueResponse": {
            "anyOf": [
                {"type": "integer"},
                {"type": "number"},
                {"type": "string"},
                {"type": "boolean"},
                {
                    "items": {"type": "integer"},
                    "type": "array",
                    "title": "PlcGetBytes",
                },
            ],
            "title": "PlcGetValueResponse",
        },
        "InfoErrorMap": {
            "properties": {
                "DataFolderError": {"type": "integer", "title": "Datafoldererror"},
                "ImageError": {"type": "integer", "title": "Imageerror"},
            },
            "type": "object",
            "required": ["DataFolderError", "ImageError"],
            "additionalProperties": {"type": "integer"},
            "title": "InfoErrorMap",
        },
        "InfoSurface": {
            "properties": {
                "key": {"type": "string", "title": "Key"},
                "saveFolder": {"type": "string", "title": "Savefolder"},
                "rotate": {"type": "number", "title": "Rotate"},
                "x_rotate": {"type": "number", "title": "X Rotate"},
                "direction": {"type": "string", "title": "Direction"},
                "save3D_data": {"type": "boolean", "title": "Save3d Data"},
                "folderList": {
                    "items": {"$ref": "#/components/schemas/InfoSurfaceFolder"},
                    "type": "array",
                    "title": "Folderlist",
                },
            },
            "type": "object",
            "required": ["key", "saveFolder", "folderList"],
            "additionalProperties": true,
            "title": "InfoSurface",
        },
        "InfoSurfaceFolder": {
            "properties": {
                "cameraKey": {"type": "string", "title": "Camerakey"},
                "source": {"type": "string", "title": "Source"},
                "cropLeft": {"type": "number", "title": "Cropleft"},
                "cropRight": {"type": "number", "title": "Cropright"},
            },
            "type": "object",
            "required": ["cameraKey", "source"],
            "additionalProperties": true,
            "title": "InfoSurfaceFolder",
        },
        "DefectDictionaryResponse": {
            "properties": {
                "data": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/components/schemas/DefectDictionaryEntry"},
                    "title": "Data",
                },
                "default": {"$ref": "#/components/schemas/DefectDictionaryEntry"},
            },
            "type": "object",
            "required": ["data", "default"],
            "additionalProperties": true,
            "title": "DefectDictionaryResponse",
        },
        "DefectDictionaryEntry": {
            "properties": {
                "level": {"type": "integer", "title": "Level"},
                "color": {"type": "string", "title": "Color"},
                "show": {"type": "boolean", "title": "Show"},
                "name": {"type": "string", "title": "Name"},
                "num": {"type": "integer", "title": "Num"},
            },
            "type": "object",
            "required": ["level", "color", "show"],
            "additionalProperties": true,
            "title": "DefectDictionaryEntry",
        },
        "DefectDictionaryRow": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectType": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defecttype",
                },
                "defectColor": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defectcolor",
                },
                "defectLevel": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Defectlevel",
                },
                "visible": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Visible",
                },
                "defectDesc": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defectdesc",
                },
            },
            "type": "object",
            "required": [
                "Id",
                "defectClass",
                "defectName",
                "defectType",
                "defectColor",
                "defectLevel",
                "visible",
                "defectDesc",
            ],
            "title": "DefectDictionaryRow",
        },
        "SetDefectDictionaryResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "count": {"type": "integer", "title": "Count"},
                "error": {"type": "string", "title": "Error"},
            },
            "type": "object",
            "required": ["status", "count"],
            "additionalProperties": true,
            "title": "SetDefectDictionaryResponse",
        },
        "FlushCoilListResponse": {
            "properties": {
                "coilList": {
                    "items": {"$ref": "#/components/schemas/CoilSummaryItem"},
                    "type": "array",
                    "title": "Coillist",
                },
            },
            "type": "object",
            "additionalProperties": true,
            "title": "FlushCoilListResponse",
        },
        "CoilSummaryItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "CoilNo": {"type": "string", "title": "Coilno"},
                "CreateTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Createtime",
                },
                "CoilType": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Coiltype",
                },
                "CoilInside": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coilinside",
                },
                "CoilDia": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coildia",
                },
                "Thickness": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Thickness",
                },
                "Width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Width",
                },
                "Weight": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Weight",
                },
                "ActWidth": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Actwidth",
                },
                "NextCode": {"type": "string", "title": "Nextcode"},
                "NextInfo": {"type": "string", "title": "Nextinfo"},
                "hasCoil": {"type": "boolean", "title": "Hascoil"},
                "hasAlarmInfo": {"type": "boolean", "title": "Hasalarminfo"},
                "AlarmInfo": {"$ref": "#/components/schemas/CoilSummaryAlarmInfo"},
                "DefectCountS": {"type": "integer", "title": "Defectcounts"},
                "DefectCountL": {"type": "integer", "title": "Defectcountl"},
                "DetectionTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Detectiontime",
                },
                "CheckStatus": {"type": "integer", "title": "Checkstatus"},
                "Status_L": {"type": "integer", "title": "Status L"},
                "Status_S": {"type": "integer", "title": "Status S"},
                "Grade": {"type": "integer", "title": "Grade"},
                "Msg": {"type": "string", "title": "Msg"},
                "childrenCoil": {
                    "items": {"$ref": "#/components/schemas/CoilSummaryChildCoil"},
                    "type": "array",
                    "title": "Childrencoil",
                },
                "childrenAlarmInfo": {
                    "items": {"type": "object", "additionalProperties": true},
                    "type": "array",
                    "title": "Childrenalarminfo",
                },
                "childrenCoilDefect": {
                    "items": {"$ref": "#/components/schemas/CoilSummaryDefect"},
                    "type": "array",
                    "title": "Childrencoildefect",
                },
                "maxDefectName": {"type": "string", "title": "Maxdefectname"},
                "maxDefectLevel": {"type": "integer", "title": "Maxdefectlevel"},
                "maxDefectSurface": {"type": "string", "title": "Maxdefectsurface"},
                "childrenCoilCheck": {
                    "items": {"type": "object", "additionalProperties": true},
                    "type": "array",
                    "title": "Childrencoilcheck",
                },
            },
            "type": "object",
            "required": [
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
                "childrenCoilCheck",
            ],
            "additionalProperties": true,
            "title": "CoilSummaryItem",
        },
        "CoilSummaryAlarmInfo": {
            "properties": {
                "S": {"$ref": "#/components/schemas/CoilSummaryAlarmSurface"},
                "L": {"$ref": "#/components/schemas/CoilSummaryAlarmSurface"},
            },
            "type": "object",
            "required": ["S", "L"],
            "title": "CoilSummaryAlarmInfo",
        },
        "CoilSummaryAlarmSurface": {
            "properties": {
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "defectGrad": {"type": "integer", "title": "Defectgrad"},
                "taperShapeGrad": {"type": "integer", "title": "Tapershapegrad"},
                "looseCoilGrad": {"type": "integer", "title": "Loosecoilgrad"},
                "flatRollGrad": {"type": "integer", "title": "Flatrollgrad"},
                "grad": {"type": "integer", "title": "Grad"},
                "nextCode": {"type": "string", "title": "Nextcode"},
                "nextName": {"type": "string", "title": "Nextname"},
                "createTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Createtime",
                },
                "taperShapeMsg": {"type": "string", "title": "Tapershapemsg"},
                "looseCoilMsg": {"type": "string", "title": "Loosecoilmsg"},
                "flatRollMsg": {"type": "string", "title": "Flatrollmsg"},
                "defectMsg": {"type": "string", "title": "Defectmsg"},
            },
            "type": "object",
            "required": [
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
                "defectMsg",
            ],
            "title": "CoilSummaryAlarmSurface",
        },
        "CoilSummaryChildCoil": {
            "properties": {
                "SecondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "DetectionTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Detectiontime",
                },
                "DefectCountL": {"type": "integer", "title": "Defectcountl"},
                "Status_L": {"type": "integer", "title": "Status L"},
                "Grade": {"type": "integer", "title": "Grade"},
                "DefectCountS": {"type": "integer", "title": "Defectcounts"},
                "Id": {"type": "integer", "title": "Id"},
                "CheckStatus": {"type": "integer", "title": "Checkstatus"},
                "Status_S": {"type": "integer", "title": "Status S"},
                "Msg": {"type": "string", "title": "Msg"},
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilSummaryChildCoil",
        },
        "GraderListItem": {
            "properties": {
                "ActWidth": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Actwidth",
                },
                "CoilNo": {"type": "string", "title": "Coilno"},
                "CreateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Createtime",
                },
                "CoilType": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Coiltype",
                },
                "CoilInside": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coilinside",
                },
                "Id": {"type": "integer", "title": "Id"},
                "CoilDia": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coildia",
                },
                "Thickness": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Thickness",
                },
                "Width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Width",
                },
                "Weight": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Weight",
                },
                "childrenCoil": {
                    "items": {"$ref": "#/components/schemas/CoilSummaryChildCoil"},
                    "type": "array",
                    "title": "Childrencoil",
                },
                "SecondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "DetectionTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Detectiontime",
                },
                "DefectCountS": {"type": "integer", "title": "Defectcounts"},
                "DefectCountL": {"type": "integer", "title": "Defectcountl"},
                "CheckStatus": {"type": "integer", "title": "Checkstatus"},
                "Status_L": {"type": "integer", "title": "Status L"},
                "Status_S": {"type": "integer", "title": "Status S"},
                "Grade": {"type": "integer", "title": "Grade"},
                "Msg": {"type": "string", "title": "Msg"},
                "Next": {"type": "string", "title": "Next"},
            },
            "type": "object",
            "required": [
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
                "Next",
            ],
            "additionalProperties": true,
            "title": "GraderListItem",
        },
        "SyncSummariesResponse": {
            "properties": {
                "synced": {"type": "integer", "title": "Synced"},
                "message": {"type": "string", "title": "Message"},
                "error": {"type": "string", "title": "Error"},
            },
            "type": "object",
            "required": ["synced"],
            "additionalProperties": true,
            "title": "SyncSummariesResponse",
        },
        "CoilInfoResponse": {
            "properties": {
                "coilId": {
                    "anyOf": [{"type": "string"}, {"type": "integer"}],
                    "title": "Coilid",
                },
                "surface": {"type": "string", "title": "Surface"},
                "width": {"type": "integer", "title": "Width"},
                "height": {"type": "integer", "title": "Height"},
                "scan3dCoordinateScaleX": {"type": "number", "title": "Scan3Dcoordinatescalex"},
                "scan3dCoordinateScaleY": {"type": "number", "title": "Scan3Dcoordinatescaley"},
                "scan3dCoordinateScaleZ": {"type": "number", "title": "Scan3Dcoordinatescalez"},
                "scan3dCoordinateOffsetZ": {"type": "number", "title": "Scan3Dcoordinateoffsetz"},
                "median_3d": {"type": "number", "title": "Median 3D"},
                "median_3d_mm": {"type": "number", "title": "Median 3D Mm"},
                "colorFromValue_mm": {"type": "number", "title": "Colorfromvalue Mm"},
                "colorToValue_mm": {"type": "number", "title": "Colortovalue Mm"},
                "circleConfig": {
                    "type": "object",
                    "additionalProperties": true,
                    "title": "Circleconfig",
                },
            },
            "type": "object",
            "additionalProperties": true,
            "title": "CoilInfoResponse",
        },
        "HeightDataSegment": {
            "properties": {
                "pointL": {"$ref": "#/components/schemas/HeightDataPoint2D"},
                "pointR": {"$ref": "#/components/schemas/HeightDataPoint2D"},
                "points": {
                    "items": {"$ref": "#/components/schemas/HeightDataPoint3D"},
                    "type": "array",
                    "title": "Points",
                },
            },
            "type": "object",
            "required": ["pointL", "pointR", "points"],
            "additionalProperties": true,
            "title": "HeightDataSegment",
        },
        "HeightDataPoint2D": {
            "prefixItems": [
                {"type": "integer", "title": "X"},
                {"type": "integer", "title": "Y"},
            ],
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "title": "HeightDataPoint2D",
        },
        "HeightDataPoint3D": {
            "prefixItems": [
                {"type": "integer", "title": "X"},
                {"type": "integer", "title": "Y"},
                {"type": "number", "title": "Z"},
            ],
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "title": "HeightDataPoint3D",
        },
        "HeightPointResponse": {
            "anyOf": [
                {"type": "integer"},
                {"type": "number"},
                {"type": "string"},
            ],
            "title": "HeightPointResponse",
        },
        "CoilSummaryDefect": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectLevel": {"type": "integer", "title": "Defectlevel"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "is_area": {"type": "boolean", "title": "Is Area"},
            },
            "type": "object",
            "required": [
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
                "is_area",
            ],
            "additionalProperties": true,
            "title": "CoilSummaryDefect",
        },
        "DefectItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defecttime",
                },
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "defectData": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defectdata",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "title": "DefectItem",
        },
        "AutoDefectItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defecttime",
                },
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "defectData": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defectdata",
                },
                "type": {"type": "string", "title": "Type"},
            },
            "type": "object",
            "required": [
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
                "type",
            ],
            "title": "AutoDefectItem",
        },
        "ManualDefectItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defecttime",
                },
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "defectData": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defectdata",
                },
                "remark": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Remark",
                },
                "annotator": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Annotator",
                },
                "type": {"type": "string", "title": "Type"},
            },
            "type": "object",
            "required": [
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
                "remark",
                "annotator",
                "type",
            ],
            "title": "ManualDefectItem",
        },
        "ManualDefectErrorResponse": {
            "properties": {
                "error": {"type": "string", "title": "Error"},
                "success": {"type": "boolean", "title": "Success"},
            },
            "type": "object",
            "required": ["error", "success"],
            "title": "ManualDefectErrorResponse",
        },
        "ManualDefectMutationResponse": {
            "anyOf": [
                {"$ref": "#/components/schemas/ManualDefectItem"},
                {"$ref": "#/components/schemas/ManualDefectErrorResponse"},
            ],
            "title": "ManualDefectMutationResponse",
        },
        "DeleteManualDefectSuccessResponse": {
            "properties": {
                "success": {"type": "boolean", "title": "Success"},
                "message": {"type": "string", "title": "Message"},
            },
            "type": "object",
            "required": ["success", "message"],
            "title": "DeleteManualDefectSuccessResponse",
        },
        "DeleteManualDefectResponse": {
            "anyOf": [
                {"$ref": "#/components/schemas/DeleteManualDefectSuccessResponse"},
                {"$ref": "#/components/schemas/ManualDefectErrorResponse"},
            ],
            "title": "DeleteManualDefectResponse",
        },
        "ExportDefectsResponse": {
            "properties": {
                "exported": {"type": "integer", "title": "Exported"},
                "error": {"type": "string", "title": "Error"},
                "errors": {"type": "integer", "title": "Errors"},
                "categories": {"type": "integer", "title": "Categories"},
                "total": {"type": "integer", "title": "Total"},
                "message": {"type": "string", "title": "Message"},
            },
            "type": "object",
            "required": ["exported"],
            "additionalProperties": true,
            "title": "ExportDefectsResponse",
        },
        "ErrorMessageResponse": {
            "properties": {
                "error": {"type": "string", "title": "Error"},
            },
            "type": "object",
            "required": ["error"],
            "title": "ErrorMessageResponse",
        },
        "SpeedTestUploadResponse": {
            "properties": {
                "filename": {"type": "string", "title": "Filename"},
                "file_size_mb": {"type": "number", "title": "File Size Mb"},
                "upload_time_s": {"type": "number", "title": "Upload Time S"},
                "upload_speed_mb_s": {"type": "number", "title": "Upload Speed Mb S"},
            },
            "type": "object",
            "required": ["filename", "file_size_mb", "upload_time_s", "upload_speed_mb_s"],
            "title": "SpeedTestUploadResponse",
        },
        "CameraDataResponse": {
            "properties": {
                "cameraKey": {"type": "string", "title": "Camerakey"},
                "coilId": {"type": "integer", "title": "Coilid"},
                "surface": {"type": "string", "title": "Surface"},
                "source": {"type": "string", "title": "Source"},
                "folder": {"type": "string", "title": "Folder"},
            },
            "type": "object",
            "required": ["cameraKey", "coilId", "surface", "source", "folder"],
            "additionalProperties": true,
            "title": "CameraDataResponse",
        },
        "AreaImageMetadataResponse": {
            "properties": {
                "width": {"type": "integer", "title": "Width"},
                "height": {"type": "integer", "title": "Height"},
            },
            "type": "object",
            "required": ["width", "height"],
            "title": "AreaImageMetadataResponse",
        },
        "CoilDetailResponse": {
            "properties": {
                "hasCoil": {"type": "boolean", "title": "Hascoil"},
                "hasAlarmInfo": {"type": "boolean", "title": "Hasalarminfo"},
                "AlarmInfo": {
                    "type": "object",
                    "additionalProperties": true,
                    "title": "Alarminfo",
                },
                "SecondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "DetectionTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Detectiontime",
                },
                "DefectCountL": {"type": "integer", "title": "Defectcountl"},
                "Status_L": {"type": "integer", "title": "Status L"},
                "Grade": {"type": "integer", "title": "Grade"},
                "DefectCountS": {"type": "integer", "title": "Defectcounts"},
                "Id": {"type": "integer", "title": "Id"},
                "CheckStatus": {"type": "integer", "title": "Checkstatus"},
                "Status_S": {"type": "integer", "title": "Status S"},
                "Msg": {"type": "string", "title": "Msg"},
                "NextCode": {"type": "string", "title": "Nextcode"},
                "NextInfo": {"type": "string", "title": "Nextinfo"},
                "childrenCoilDefect": {
                    "items": {"$ref": "#/components/schemas/CoilDetailDefect"},
                    "type": "array",
                    "title": "Childrencoildefect",
                },
                "defects": {
                    "items": {"$ref": "#/components/schemas/CoilDetailDefectAlias"},
                    "type": "array",
                    "title": "Defects",
                },
                "childrenTaperShapePoint": {
                    "items": {"$ref": "#/components/schemas/TaperShapePointItem"},
                    "type": "array",
                    "title": "Childrentapershapepoint",
                },
                "childrenAlarmTaperShape": {
                    "items": {"$ref": "#/components/schemas/CoilAlarmTaperShapeItem"},
                    "type": "array",
                    "title": "Childrenalarmtapershape",
                },
                "childrenAlarmLooseCoil": {
                    "items": {"$ref": "#/components/schemas/CoilAlarmLooseCoilItem"},
                    "type": "array",
                    "title": "Childrenalarmloosecoil",
                },
                "childrenAlarmFlatRoll": {
                    "items": {"$ref": "#/components/schemas/CoilAlarmFlatRollItem"},
                    "type": "array",
                    "title": "Childrenalarmflatroll",
                },
                "childrenCoilCheck": {
                    "items": {"$ref": "#/components/schemas/CoilCheckResponse"},
                    "type": "array",
                    "title": "Childrencoilcheck",
                },
                "ActWidth": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Actwidth",
                },
                "CoilNo": {"type": "string", "title": "Coilno"},
                "CreateTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Createtime",
                },
                "CoilType": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Coiltype",
                },
                "CoilInside": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coilinside",
                },
                "CoilDia": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Coildia",
                },
                "Thickness": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Thickness",
                },
                "Width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Width",
                },
                "Weight": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Weight",
                },
                "childrenCoil": {
                    "items": {"$ref": "#/components/schemas/CoilSummaryChildCoil"},
                    "type": "array",
                    "title": "Childrencoil",
                },
                "childrenAlarmInfo": {
                    "items": {"$ref": "#/components/schemas/CoilDetailAlarmInfoItem"},
                    "type": "array",
                    "title": "Childrenalarminfo",
                },
                "maxDefectName": {"type": "string", "title": "Maxdefectname"},
                "maxDefectLevel": {"type": "integer", "title": "Maxdefectlevel"},
                "maxDefectSurface": {"type": "string", "title": "Maxdefectsurface"},
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilDetailResponse",
        },
        "CoilDetailDefect": {
            "properties": {
                "surface": {"type": "string", "title": "Surface"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "Id": {"type": "integer", "title": "Id"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defecttime",
                },
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectData": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defectdata",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilDetailDefect",
        },
        "CoilDetailDefectAlias": {
            "properties": {
                "surface": {"type": "string", "title": "Surface"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "Id": {"type": "integer", "title": "Id"},
                "defectClass": {"type": "integer", "title": "Defectclass"},
                "defectStatus": {"type": "integer", "title": "Defectstatus"},
                "defectX": {"type": "integer", "title": "Defectx"},
                "defectW": {"type": "integer", "title": "Defectw"},
                "defectSource": {"type": "number", "title": "Defectsource"},
                "defectName": {"type": "string", "title": "Defectname"},
                "defectTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defecttime",
                },
                "defectY": {"type": "integer", "title": "Defecty"},
                "defectH": {"type": "integer", "title": "Defecth"},
                "defectData": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": true},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Defectdata",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilDetailDefectAlias",
        },
        "TaperShapePointItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "x": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "X",
                },
                "y": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Y",
                },
                "value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Value",
                },
                "level": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Level",
                },
                "err_msg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Err Msg",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
            },
            "type": "object",
            "required": [
                "Id",
                "secondaryCoilId",
                "surface",
                "x",
                "y",
                "value",
                "level",
                "err_msg",
                "crateTime",
                "data",
            ],
            "additionalProperties": true,
            "title": "TaperShapePointItem",
        },
        "CoilDetailAlarmInfoItem": {
            "properties": {
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "nextName": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Nextname",
                },
                "taperShapeMsg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Tapershapemsg",
                },
                "looseCoilMsg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Loosecoilmsg",
                },
                "flatRollMsg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Flatrollmsg",
                },
                "defectMsg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Defectmsg",
                },
                "crateTime": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Cratetime",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
                "Id": {"type": "integer", "title": "Id"},
                "nextCode": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Nextcode",
                },
                "taperShapeGrad": {"type": "integer", "title": "Tapershapegrad"},
                "looseCoilGrad": {"type": "integer", "title": "Loosecoilgrad"},
                "flatRollGrad": {"type": "integer", "title": "Flatrollgrad"},
                "defectGrad": {"type": "integer", "title": "Defectgrad"},
                "grad": {"type": "integer", "title": "Grad"},
            },
            "type": "object",
            "required": [
                "secondaryCoilId",
                "surface",
                "nextName",
                "taperShapeMsg",
                "looseCoilMsg",
                "flatRollMsg",
                "defectMsg",
                "crateTime",
                "data",
                "Id",
                "nextCode",
                "taperShapeGrad",
                "looseCoilGrad",
                "flatRollGrad",
                "defectGrad",
                "grad",
            ],
            "additionalProperties": true,
            "title": "CoilDetailAlarmInfoItem",
        },
        "ControlConfigResponse": {
            "type": "object",
            "additionalProperties": true,
            "title": "ControlConfigResponse",
        },
        "CoilCheckResponse": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "status": {"type": "integer", "title": "Status"},
                "msg": {"type": "string", "title": "Msg"},
            },
            "type": "object",
            "required": ["Id", "secondaryCoilId", "status", "msg"],
            "title": "CoilCheckResponse",
        },
        "DataHasResponse": {
            "type": "object",
            "additionalProperties": {"$ref": "#/components/schemas/DataHasSurfaceFlags"},
            "title": "DataHasResponse",
        },
        "DataHasSurfaceFlags": {
            "properties": {
                "3D": {"type": "boolean", "title": "3D"},
                "MESH": {"type": "boolean", "title": "Mesh"},
                "JPG": {"type": "boolean", "title": "Jpg"},
                "2D": {"type": "boolean", "title": "2D"},
            },
            "type": "object",
            "required": ["3D", "MESH", "JPG", "2D"],
            "title": "DataHasSurfaceFlags",
        },
        "CoilAlarmResponse": {
            "properties": {
                "FlatRoll": {"$ref": "#/components/schemas/CoilAlarmFlatRollMap"},
                "TaperShape": {"$ref": "#/components/schemas/CoilAlarmTaperShapeMap"},
                "LooseCoil": {"$ref": "#/components/schemas/CoilAlarmLooseCoilMap"},
            },
            "type": "object",
            "required": ["FlatRoll", "TaperShape", "LooseCoil"],
            "title": "CoilAlarmResponse",
        },
        "CoilAlarmFlatRollMap": {
            "additionalProperties": {"$ref": "#/components/schemas/CoilAlarmFlatRollItem"},
            "type": "object",
            "title": "CoilAlarmFlatRollMap",
        },
        "CoilAlarmTaperShapeMap": {
            "additionalProperties": {
                "items": {"$ref": "#/components/schemas/CoilAlarmTaperShapeItem"},
                "type": "array",
            },
            "type": "object",
            "title": "CoilAlarmTaperShapeMap",
        },
        "CoilAlarmLooseCoilMap": {
            "additionalProperties": {
                "items": {"$ref": "#/components/schemas/CoilAlarmLooseCoilItem"},
                "type": "array",
            },
            "type": "object",
            "title": "CoilAlarmLooseCoilMap",
        },
        "CoilAlarmFlatRollItem": {
            "properties": {
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "out_circle_height": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Circle Height",
                },
                "inner_circle_center_x": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Circle Center X",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
                "surface": {"type": "string", "title": "Surface"},
                "inner_circle_center_y": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Circle Center Y",
                },
                "out_circle_center_x": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Circle Center X",
                },
                "inner_circle_radius": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Circle Radius",
                },
                "accuracy_x": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Accuracy X",
                },
                "out_circle_center_y": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Circle Center Y",
                },
                "accuracy_y": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Accuracy Y",
                },
                "out_circle_radius": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Circle Radius",
                },
                "level": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Level",
                },
                "Id": {"type": "integer", "title": "Id"},
                "inner_circle_width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Circle Width",
                },
                "err_msg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Err Msg",
                },
                "out_circle_width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Circle Width",
                },
                "inner_circle_height": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Circle Height",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilAlarmFlatRollItem",
        },
        "CoilAlarmTaperShapeItem": {
            "properties": {
                "in_taper_max_x": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "In Taper Max X",
                },
                "err_msg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Err Msg",
                },
                "surface": {"type": "string", "title": "Surface"},
                "in_taper_max_y": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "In Taper Max Y",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
                "out_taper_max_x": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Out Taper Max X",
                },
                "in_taper_max_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "In Taper Max Value",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
                "out_taper_max_y": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Out Taper Max Y",
                },
                "in_taper_min_x": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "In Taper Min X",
                },
                "Id": {"type": "integer", "title": "Id"},
                "out_taper_max_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Taper Max Value",
                },
                "in_taper_min_y": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "In Taper Min Y",
                },
                "out_taper_min_x": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Out Taper Min X",
                },
                "in_taper_min_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "In Taper Min Value",
                },
                "out_taper_min_y": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Out Taper Min Y",
                },
                "rotation_angle": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Rotation Angle",
                },
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "out_taper_min_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Out Taper Min Value",
                },
                "level": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Level",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "additionalProperties": true,
            "title": "CoilAlarmTaperShapeItem",
        },
        "CoilAlarmLooseCoilItem": {
            "properties": {
                "surface": {"type": "string", "title": "Surface"},
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "rotation_angle": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Rotation Angle",
                },
                "err_msg": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Err Msg",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
                "max_width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Max Width",
                },
                "level": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Level",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
            },
            "type": "object",
            "required": [
                "surface",
                "Id",
                "secondaryCoilId",
                "rotation_angle",
                "err_msg",
                "data",
                "max_width",
                "level",
                "crateTime",
            ],
            "additionalProperties": true,
            "title": "CoilAlarmLooseCoilItem",
        },
        "CoilAlarmPythonDateTime": {
            "properties": {
                "year": {"type": "integer", "title": "Year"},
                "month": {"type": "integer", "title": "Month"},
                "weekday": {"type": "integer", "title": "Weekday"},
                "day": {"type": "integer", "title": "Day"},
                "hour": {"type": "integer", "title": "Hour"},
                "minute": {"type": "integer", "title": "Minute"},
                "second": {"type": "integer", "title": "Second"},
            },
            "type": "object",
            "required": ["year", "month", "weekday", "day", "hour", "minute", "second"],
            "title": "CoilAlarmPythonDateTime",
        },
        "CoilStateItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "scan3dCoordinateScaleY": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Scan3Dcoordinatescaley",
                },
                "start": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Start",
                },
                "mask_area": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Mask Area",
                },
                "surface": {"type": "string", "title": "Surface"},
                "scan3dCoordinateScaleZ": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Scan3Dcoordinatescalez",
                },
                "step": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Step",
                },
                "width": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Width",
                },
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "rotate": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Rotate",
                },
                "upperLimit": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Upperlimit",
                },
                "height": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Height",
                },
                "x_rotate": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "X Rotate",
                },
                "lowerLimit": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Lowerlimit",
                },
                "jsonData": {"type": "string", "title": "Jsondata"},
                "median_3d": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Median 3D",
                },
                "lowerArea": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Lowerarea",
                },
                "median_3d_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Median 3D Mm",
                },
                "upperArea": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Upperarea",
                },
                "startTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Starttime",
                },
                "colorFromValue_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Colorfromvalue Mm",
                },
                "lowerArea_percent": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Lowerarea Percent",
                },
                "scan3dCoordinateScaleX": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Scan3Dcoordinatescalex",
                },
                "colorToValue_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Colortovalue Mm",
                },
                "upperArea_percent": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Upperarea Percent",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "title": "CoilStateItem",
        },
        "PlcDataItem": {
            "properties": {
                "Id": {"type": "integer", "title": "Id"},
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "location_S": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location S",
                },
                "location_L": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location L",
                },
                "location_laser": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location Laser",
                },
                "startTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Starttime",
                },
                "pclData": {"type": "string", "title": "Pcldata"},
            },
            "type": "object",
            "required": [
                "Id",
                "secondaryCoilId",
                "location_S",
                "location_L",
                "location_laser",
                "startTime",
                "pclData",
            ],
            "title": "PlcDataItem",
        },
        "PointDataItem": {
            "properties": {
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "surface": {"type": "string", "title": "Surface"},
                "x": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "X",
                },
                "z": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Z",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
                "type": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Type",
                },
                "Id": {"type": "integer", "title": "Id"},
                "y": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Y",
                },
                "z_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Z Mm",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "title": "PointDataItem",
        },
        "LineDataItem": {
            "properties": {
                "width": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Width",
                },
                "inner_min_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Min Value",
                },
                "outer_max_value_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Outer Max Value Mm",
                },
                "height": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Height",
                },
                "inner_min_value_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Min Value Mm",
                },
                "crateTime": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/CoilAlarmPythonDateTime"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Cratetime",
                },
                "secondaryCoilId": {"type": "integer", "title": "Secondarycoilid"},
                "rotation_angle": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Rotation Angle",
                },
                "inner_max_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Max Value",
                },
                "surface": {"type": "string", "title": "Surface"},
                "x1": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "X1",
                },
                "inner_max_value_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Inner Max Value Mm",
                },
                "Id": {"type": "integer", "title": "Id"},
                "y1": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Y1",
                },
                "outer_min_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Outer Min Value",
                },
                "type": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Type",
                },
                "x2": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "X2",
                },
                "outer_min_value_mm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Outer Min Value Mm",
                },
                "center_x": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Center X",
                },
                "y2": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Y2",
                },
                "outer_max_value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Outer Max Value",
                },
                "center_y": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Center Y",
                },
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Data",
                },
            },
            "type": "object",
            "required": [
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
            ],
            "title": "LineDataItem",
        },
        "PlcCurveResponse": {
            "properties": {
                "field": {"type": "string", "title": "Field"},
                "items": {
                    "items": {"$ref": "#/components/schemas/PlcCurveItem"},
                    "type": "array",
                    "title": "Items",
                },
                "error": {"type": "string", "title": "Error"},
            },
            "type": "object",
            "required": ["field", "items"],
            "title": "PlcCurveResponse",
        },
        "PlcCurveItem": {
            "properties": {
                "coil_id": {"type": "integer", "title": "Coil Id"},
                "time": {"type": "string", "title": "Time"},
                "value": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Value",
                },
            },
            "type": "object",
            "required": ["coil_id", "time", "value"],
            "title": "PlcCurveItem",
        },
        "PlcCurveAllResponse": {
            "properties": {
                "items": {
                    "items": {"$ref": "#/components/schemas/PlcCurveAllItem"},
                    "type": "array",
                    "title": "Items",
                },
            },
            "type": "object",
            "required": ["items"],
            "title": "PlcCurveAllResponse",
        },
        "PlcCurveAllItem": {
            "properties": {
                "coil_id": {"type": "integer", "title": "Coil Id"},
                "time": {"type": "string", "title": "Time"},
                "location_S": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location S",
                },
                "location_L": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location L",
                },
                "location_laser": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Location Laser",
                },
                "median_3d_mm_S": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Median 3D Mm S",
                },
                "median_3d_mm_L": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Median 3D Mm L",
                },
                "median_3d_mm_avg": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Median 3D Mm Avg",
                },
                "width_": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Width",
                },
            },
            "type": "object",
            "required": [
                "coil_id",
                "time",
                "location_S",
                "location_L",
                "location_laser",
                "median_3d_mm_S",
                "median_3d_mm_L",
                "median_3d_mm_avg",
                "width_",
            ],
            "title": "PlcCurveAllItem",
        },
        "RuntimeInfoResponse": {
            "properties": {
                "python_version": {"type": "string", "title": "Python Version"},
                "cache_mode": {"type": "string", "title": "Cache Mode"},
                "cpu_model": {"type": "string", "title": "Cpu Model"},
                "gpus": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Gpus",
                },
                "is_local": {"type": "boolean", "title": "Is Local"},
                "developer_mode": {"type": "boolean", "title": "Developer Mode"},
                "offline_mode": {"type": "boolean", "title": "Offline Mode"},
            },
            "type": "object",
            "required": [
                "python_version",
                "cache_mode",
                "cpu_model",
                "gpus",
                "is_local",
                "developer_mode",
                "offline_mode",
            ],
            "title": "RuntimeInfoResponse",
        },
        "HardwareStatusResponse": {
            "properties": {
                "cpu": {"$ref": "#/components/schemas/HardwareStatusItem"},
                "memory": {"$ref": "#/components/schemas/HardwareStatusItem"},
                "disk": {"$ref": "#/components/schemas/HardwareStatusItem"},
                "gpu": {"$ref": "#/components/schemas/HardwareStatusItem"},
            },
            "type": "object",
            "required": ["cpu", "memory", "disk", "gpu"],
            "title": "HardwareStatusResponse",
        },
        "HardwareStatusItem": {
            "properties": {
                "key": {"type": "string", "title": "Key"},
                "value": {"type": "string", "title": "Value"},
                "msg": {"type": "string", "title": "Msg"},
                "level": {"type": "integer", "title": "Level"},
            },
            "type": "object",
            "required": ["key", "value", "msg", "level"],
            "title": "HardwareStatusItem",
        },
        "CameraAdjustmentStatusResponse": {
            "properties": {
                "configFile": {"type": "string", "title": "Configfile"},
                "captureServiceUrl": {"type": "string", "title": "Captureserviceurl"},
                "captureStatus": {"$ref": "#/components/schemas/CameraAdjustmentCaptureStatus"},
                "cameras": {
                    "items": {"$ref": "#/components/schemas/CameraAdjustmentItem"},
                    "type": "array",
                    "title": "Cameras",
                },
            },
            "type": "object",
            "required": ["configFile", "captureServiceUrl", "captureStatus", "cameras"],
            "title": "CameraAdjustmentStatusResponse",
        },
        "CameraAdjustmentCaptureStatus": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "message": {"type": "string", "title": "Message"},
                "cameraCount": {"type": "integer", "title": "Cameracount"},
            },
            "type": "object",
            "required": ["ok", "message", "cameraCount"],
            "title": "CameraAdjustmentCaptureStatus",
        },
        "CameraAdjustmentItem": {
            "properties": {
                "key": {"type": "string", "title": "Key"},
                "name": {"type": "string", "title": "Name"},
                "sn": {"type": "string", "title": "Sn"},
                "serverIp": {"type": "string", "title": "Serverip"},
                "serverPort": {
                    "anyOf": [
                        {"type": "integer"},
                        {"type": "number"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Serverport",
                },
                "yamlConfig": {"type": "string", "title": "Yamlconfig"},
                "serviceUrl": {"type": "string", "title": "Serviceurl"},
                "legacyServiceUrl": {"type": "string", "title": "Legacyserviceurl"},
                "status": {"$ref": "#/components/schemas/CameraAdjustmentRuntimeStatus"},
            },
            "type": "object",
            "required": [
                "key",
                "name",
                "sn",
                "serverIp",
                "serverPort",
                "yamlConfig",
                "serviceUrl",
                "legacyServiceUrl",
                "status",
            ],
            "title": "CameraAdjustmentItem",
        },
        "CameraAdjustmentRuntimeStatus": {
            "properties": {
                "capture": {"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"},
                "lastFrameAge3D": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Lastframeage3d",
                },
                "lastError3D": {"type": "string", "title": "Lasterror3d"},
            },
            "type": "object",
            "required": ["capture", "lastFrameAge3D", "lastError3D"],
            "additionalProperties": true,
            "title": "CameraAdjustmentRuntimeStatus",
        },
        "CameraCaptureRuntimeStatus": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "connected": {"type": "boolean", "title": "Connected"},
                "message": {"type": "string", "title": "Message"},
                "serviceUrl": {"type": "string", "title": "Serviceurl"},
            },
            "type": "object",
            "additionalProperties": true,
            "title": "CameraCaptureRuntimeStatus",
        },
        "CaptureStatusResponse": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "message": {"type": "string", "title": "Message"},
                "service": {"type": "string", "title": "Service"},
                "serviceUrl": {"type": "string", "title": "Serviceurl"},
                "cameraCount": {"type": "integer", "title": "Cameracount"},
                "cameras": {
                    "items": {"$ref": "#/components/schemas/CaptureStatusCamera"},
                    "type": "array",
                    "title": "Cameras",
                },
            },
            "type": "object",
            "required": ["ok"],
            "additionalProperties": true,
            "title": "CaptureStatusResponse",
        },
        "CaptureStatusCamera": {
            "properties": {
                "key": {"type": "string", "title": "Key"},
                "name": {"type": "string", "title": "Name"},
                "sn": {"type": "string", "title": "Sn"},
                "serverIp": {"type": "string", "title": "Serverip"},
                "serverPort": {
                    "anyOf": [
                        {"type": "integer"},
                        {"type": "number"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Serverport",
                },
                "yamlConfig": {"type": "string", "title": "Yamlconfig"},
                "serviceUrl": {"type": "string", "title": "Serviceurl"},
                "legacyServiceUrl": {"type": "string", "title": "Legacyserviceurl"},
                "status": {"$ref": "#/components/schemas/CameraCaptureRuntimeStatus"},
            },
            "type": "object",
            "required": ["key"],
            "additionalProperties": true,
            "title": "CaptureStatusCamera",
        },
        "CameraActionResponse": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "route": {"type": "string", "title": "Route"},
                "message": {"type": "string", "title": "Message"},
            },
            "type": "object",
            "additionalProperties": true,
            "title": "CameraActionResponse",
        },
        "CameraAlarmResponse": {
            "additionalProperties": {"$ref": "#/components/schemas/CameraAlarmItem"},
            "type": "object",
            "title": "CameraAlarmResponse",
        },
        "CameraAlarmItem": {
            "properties": {
                "DeviceTemperature": {
                    "anyOf": [
                        {"type": "number"},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "title": "Devicetemperature",
                },
                "level": {"type": "integer", "title": "Level"},
                "msg": {"type": "string", "title": "Msg"},
                "connected": {"type": "boolean", "title": "Connected"},
                "ok": {"type": "boolean", "title": "Ok"},
                "captureOk": {"type": "boolean", "title": "Captureok"},
                "lastFrameAge": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "Lastframeage",
                },
                "lastError2D": {"type": "string", "title": "Lasterror2d"},
                "lastError3D": {"type": "string", "title": "Lasterror3d"},
                "serviceUrl": {"type": "string", "title": "Serviceurl"},
                "cameraKey": {"type": "string", "title": "Camerakey"},
                "cameraName": {"type": "string", "title": "Cameraname"},
            },
            "type": "object",
            "required": [
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
                "cameraName",
            ],
            "title": "CameraAlarmItem",
        },
        "TestModeResponse": {
            "properties": {
                "test_mode": {"type": "boolean", "title": "Test Mode"},
            },
            "type": "object",
            "required": ["test_mode"],
            "title": "TestModeResponse",
        },
        "SetTestModeResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "test_mode": {"type": "boolean", "title": "Test Mode"},
            },
            "type": "object",
            "required": ["status", "test_mode"],
            "title": "SetTestModeResponse",
        },
        "TestModeStatusResponse": {
            "properties": {
                "config_file_exists": {"type": "boolean", "title": "Config File Exists"},
                "config_file_value": {"type": "boolean", "title": "Config File Value"},
                "developer_mode": {"type": "boolean", "title": "Developer Mode"},
                "is_local": {"type": "boolean", "title": "Is Local"},
                "config_file_path": {"type": "string", "title": "Config File Path"},
            },
            "type": "object",
            "required": [
                "config_file_exists",
                "config_file_value",
                "developer_mode",
                "is_local",
                "config_file_path",
            ],
            "title": "TestModeStatusResponse",
        },
        "ClipConfigPayload": {
            "properties": {
                "surface_key": {"type": "string", "title": "Surface Key"},
                "mode": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Mode",
                },
                "fixed": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Fixed",
                },
                "a": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "A",
                },
                "b": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "B",
                },
                "c": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "title": "C",
                },
                "offset": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Offset",
                },
            },
            "type": "object",
            "required": ["surface_key"],
            "title": "ClipConfigPayload",
        },
        "ClipConfigResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "surface_key": {"type": "string", "title": "Surface Key"},
                "clip_config": {"$ref": "#/components/schemas/AreaClipConfig"},
            },
            "type": "object",
            "required": ["status", "surface_key", "clip_config"],
            "title": "ClipConfigResponse",
        },
        "SaveToSqlResponse": {
            "properties": {
                "state": {"type": "boolean", "title": "State"},
            },
            "type": "object",
            "required": ["state"],
            "title": "SaveToSqlResponse",
        },
        "AreaClipConfig": {
            "properties": {
                "mode": {"type": "string", "title": "Mode"},
                "fixed": {"type": "integer", "title": "Fixed"},
                "a": {"type": "number", "title": "A"},
                "b": {"type": "number", "title": "B"},
                "c": {"type": "number", "title": "C"},
                "offset": {"type": "integer", "title": "Offset"},
            },
            "type": "object",
            "required": ["mode", "fixed", "a", "b", "c", "offset"],
            "title": "AreaClipConfig",
        },
        "AreaRejoinPayload": {
            "properties": {
                "coil_id": {"type": "integer", "title": "Coil Id"},
                "surface_key": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Surface Key",
                },
            },
            "type": "object",
            "required": ["coil_id"],
            "title": "AreaRejoinPayload",
        },
        "AreaRejoinResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "coil_id": {"type": "integer", "title": "Coil Id"},
                "queued": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Queued",
                },
                "failed": {
                    "items": {"type": "object"},
                    "type": "array",
                    "title": "Failed",
                },
                "queueDepths": {
                    "additionalProperties": {"type": "integer"},
                    "type": "object",
                    "title": "Queuedepths",
                },
            },
            "type": "object",
            "required": ["status", "coil_id", "queued", "failed"],
            "title": "AreaRejoinResponse",
        },
        "AreaStatusResponse": {
            "properties": {
                "status": {"type": "string", "title": "Status"},
                "surfaces": {
                    "additionalProperties": {"$ref": "#/components/schemas/AreaSurfaceStatus"},
                    "type": "object",
                    "title": "Surfaces",
                },
                "queueDepths": {
                    "additionalProperties": {"type": "integer"},
                    "type": "object",
                    "title": "Queuedepths",
                },
                "scanner": {"$ref": "#/components/schemas/AreaScannerStatus"},
                "joinQueueSize": {"type": "integer", "title": "Joinqueuesize"},
            },
            "type": "object",
            "required": ["status", "surfaces", "queueDepths", "scanner"],
            "title": "AreaStatusResponse",
        },
        "AreaScannerStatus": {
            "properties": {
                "enabled": {"type": "boolean", "title": "Enabled"},
                "scanInterval": {"type": "integer", "title": "Scaninterval"},
                "scanLimit": {"type": "integer", "title": "Scanlimit"},
                "maxQueueDepth": {"type": "integer", "title": "Maxqueuedepth"},
                "minImagesPerCamera": {"type": "integer", "title": "Minimagespercamera"},
                "maxCameraCountSkew": {"type": "integer", "title": "Maxcameracountskew"},
                "scanRunning": {"type": "boolean", "title": "Scanrunning"},
                "lastScanStartTime": {"type": "number", "title": "Lastscanstarttime"},
                "lastScanTime": {"type": "number", "title": "Lastscantime"},
                "lastScanError": {"type": "string", "title": "Lastscanerror"},
                "lastCandidates": {
                    "items": {"type": "integer"},
                    "type": "array",
                    "title": "Lastcandidates",
                },
                "queued": {
                    "items": {"$ref": "#/components/schemas/AreaScanQueuedItem"},
                    "type": "array",
                    "title": "Queued",
                },
                "skippedProcessed": {"type": "integer", "title": "Skippedprocessed"},
                "skippedIncomplete": {"type": "integer", "title": "Skippedincomplete"},
                "skippedQueueFull": {"type": "integer", "title": "Skippedqueuefull"},
                "queueFailures": {
                    "items": {"type": "integer"},
                    "type": "array",
                    "title": "Queuefailures",
                },
            },
            "type": "object",
            "required": [
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
                "queueFailures",
            ],
            "title": "AreaScannerStatus",
        },
        "AreaScanQueuedItem": {
            "properties": {
                "coil_id": {"type": "integer", "title": "Coil Id"},
                "reason": {"type": "string", "title": "Reason"},
            },
            "type": "object",
            "required": ["coil_id", "reason"],
            "title": "AreaScanQueuedItem",
        },
        "ServerStateResponse": {
            "items": {"$ref": "#/components/schemas/ServerStateEntry"},
            "type": "array",
            "title": "ServerStateResponse",
        },
        "ServerStateEntry": {
            "anyOf": [
                {"$ref": "#/components/schemas/ServerStateTuple"},
                {"$ref": "#/components/schemas/ServerStateMessage"},
                {"type": "string"},
                {"type": "number"},
                {"type": "boolean"},
            ],
            "title": "ServerStateEntry",
        },
        "ServerStateTuple": {
            "prefixItems": [
                {"type": "string", "title": "Type"},
                {"title": "Message"},
            ],
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "title": "ServerStateTuple",
        },
        "ServerStateMessage": {
            "properties": {
                "key": {"type": "string", "title": "Key"},
                "name": {"type": "string", "title": "Name"},
                "title": {"type": "string", "title": "Title"},
                "value": {"title": "Value"},
                "state": {"title": "State"},
                "status": {"title": "Status"},
                "msg": {"title": "Msg"},
                "message": {"title": "Message"},
                "detail": {"title": "Detail"},
                "level": {
                    "anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "string"}],
                    "title": "Level",
                },
                "alarmLevel": {
                    "anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "string"}],
                    "title": "Alarmlevel",
                },
            },
            "type": "object",
            "additionalProperties": true,
            "title": "ServerStateMessage",
        },
        "AlgTestStartResponse": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "task_id": {"type": "string", "title": "Task Id"},
            },
            "type": "object",
            "required": ["ok", "task_id"],
            "title": "AlgTestStartResponse",
        },
        "AlgTestStopResponse": {
            "properties": {
                "ok": {"type": "boolean", "title": "Ok"},
                "message": {"type": "string", "title": "Message"},
            },
            "type": "object",
            "required": ["ok", "message"],
            "title": "AlgTestStopResponse",
        },
        "AlgModelListResponse": {
            "properties": {
                "models": {
                    "items": {"$ref": "#/components/schemas/AlgModelInfo"},
                    "type": "array",
                    "title": "Models",
                },
            },
            "type": "object",
            "required": ["models"],
            "title": "AlgModelListResponse",
        },
        "AlgModelInfo": {
            "properties": {
                "name": {"type": "string", "title": "Name"},
                "type": {"type": "string", "title": "Type"},
                "display_name": {"type": "string", "title": "Display Name"},
            },
            "type": "object",
            "required": ["name", "type", "display_name"],
            "title": "AlgModelInfo",
        },
        "ReDetectionStatusResponse": {
            "properties": {
                "total": {"type": "integer", "title": "Total"},
                "done": {"type": "integer", "title": "Done"},
                "pending": {"type": "integer", "title": "Pending"},
                "running": {"type": "boolean", "title": "Running"},
                "error": {"type": "string", "title": "Error"},
                "queue": {
                    "items": {"type": "integer"},
                    "type": "array",
                    "title": "Queue",
                },
                "messages": {
                    "items": {"type": "object"},
                    "type": "array",
                    "title": "Messages",
                },
                "progress": {"type": "number", "title": "Progress"},
            },
            "type": "object",
            "required": [
                "total", "done", "pending", "running", "error", "queue", "messages", "progress",
            ],
            "title": "ReDetectionStatusResponse",
        },
        "AreaSurfaceStatus": {
            "properties": {
                "queueSize": {"type": "integer", "title": "Queuesize"},
                "lastCoilId": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "title": "Lastcoilid",
                },
                "lastError": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "title": "Lasterror",
                },
                "clipConfig": {"$ref": "#/components/schemas/AreaClipConfig"},
            },
            "type": "object",
            "required": ["queueSize", "lastCoilId"],
            "title": "AreaSurfaceStatus",
        },
        "SoftwareUpdateManifest": {
            "properties": {
                "version": {"type": "string", "title": "Version"},
                "latest_version": {"type": "string", "title": "Latest Version"},
                "latestVersion": {"type": "string", "title": "Latestversion"},
                "download_url": {"type": "string", "title": "Download Url"},
                "downloadUrl": {"type": "string", "title": "Downloadurl"},
                "package_url": {"type": "string", "title": "Package Url"},
                "packageUrl": {"type": "string", "title": "Packageurl"},
                "file_name": {"type": "string", "title": "File Name"},
                "fileName": {"type": "string", "title": "Filename"},
                "release_notes": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Release Notes",
                },
                "releaseNotes": {
                    "items": {"type": "string"},
                    "type": "array",
                    "title": "Releasenotes",
                },
            },
            "type": "object",
            "required": ["version", "latest_version", "download_url", "package_url", "file_name"],
            "title": "SoftwareUpdateManifest",
        },
        "Body_upload_test_speedtest_upload_post": {
            "properties": {
                "file": {
                    "type": "string",
                    "contentMediaType": "application/octet-stream",
                    "title": "File",
                },
            },
            "type": "object",
            "required": ["file"],
            "title": "Body_upload_test_speedtest_upload_post",
        },
    })
}

fn openapi_path_parameter_type(name: &str) -> &'static str {
    let lower = name.to_ascii_lowercase();
    if lower.contains("id")
        || matches!(
            lower.as_str(),
            "x" | "y" | "w" | "h" | "from_id" | "to_id" | "number" | "status"
        )
    {
        "integer"
    } else {
        "string"
    }
}

fn openapi_parameter_title(name: &str) -> String {
    name.split('_')
        .filter(|part| !part.is_empty())
        .map(|part| {
            let mut chars = part.chars();
            match chars.next() {
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

async fn swagger_docs() -> Response {
    html_response(
        r##"<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>FastAPI - Swagger UI</title>
  <link type="text/css" rel="stylesheet" href="/static/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/static/swagger-ui-bundle.js"></script>
  <script>
    const ui = SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      oauth2RedirectUrl: window.location.origin + "/docs/oauth2-redirect",
      presets: [SwaggerUIBundle.presets.apis],
      layout: "BaseLayout"
    });
  </script>
</body>
</html>"##,
    )
}

async fn swagger_oauth2_redirect() -> Response {
    html_response(
        r#"<!DOCTYPE html>
<html>
<head>
  <title>Swagger UI OAuth2 Redirect</title>
</head>
<body>
<script>
  'use strict';
  var oauth2RedirectUrl = window.location.href;
  window.opener && window.opener.postMessage({ oauth2RedirectUrl: oauth2RedirectUrl }, window.location.origin);
</script>
</body>
</html>"#,
    )
}

async fn redoc_docs() -> Response {
    html_response(
        r#"<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>FastAPI - ReDoc</title>
  <link type="text/css" rel="stylesheet" href="/static/swagger-ui.css">
</head>
<body>
  <redoc spec-url="/openapi.json"></redoc>
  <script src="/static/redoc.standalone.js"></script>
</body>
</html>"#,
    )
}

async fn swagger_ui_bundle_js() -> Response {
    text_response(
        r##"(function () {
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char];
    });
  }

  function renderOperationMeta(operation, summaryClass, tagClass, descriptionClass) {
    var summary = operation && operation.summary ? operation.summary : "";
    var tags = operation && Array.isArray(operation.tags) ? operation.tags.join(", ") : "";
    var description = operation && operation.description ? operation.description : "";
    return [
      summary ? "<span class=\"" + summaryClass + "\">" + escapeHtml(summary) + "</span>" : "",
      tags ? "<span class=\"" + tagClass + "\">" + escapeHtml(tags) + "</span>" : "",
      description ? "<span class=\"" + descriptionClass + "\">" + escapeHtml(description) + "</span>" : ""
    ].join("");
  }

  function renderSchemaLabel(schema) {
    if (!schema) return "";
    if (schema.$ref) return schema.$ref.replace(/^#\/components\/schemas\//, "");
    if (schema.type === "array" && schema.items) return "array<" + renderSchemaLabel(schema.items) + ">";
    if (schema.type) return schema.format ? schema.type + ":" + schema.format : schema.type;
    if (Array.isArray(schema.anyOf)) {
      return "anyOf(" + schema.anyOf.map(renderSchemaLabel).filter(Boolean).join(" | ") + ")";
    }
    if (Array.isArray(schema.oneOf)) {
      return "oneOf(" + schema.oneOf.map(renderSchemaLabel).filter(Boolean).join(" | ") + ")";
    }
    if (Array.isArray(schema.allOf)) {
      return "allOf(" + schema.allOf.map(renderSchemaLabel).filter(Boolean).join(" & ") + ")";
    }
    if (schema.properties) return "object";
    return "schema";
  }

  function renderContentSchemaList(content) {
    return Object.keys(content || {}).sort().map(function (contentType) {
      var mediaType = content[contentType] || {};
      var schemaLabel = renderSchemaLabel(mediaType.schema);
      return schemaLabel ? contentType + " -> " + schemaLabel : contentType;
    }).filter(Boolean);
  }

  function operationSearchText(method, path, operation) {
    return [
      method,
      path,
      operation.summary || "",
      operation.description || "",
      Array.isArray(operation.tags) ? operation.tags.join(" ") : ""
    ].join(" ").toLowerCase();
  }

  function filterOperations(root) {
    var input = root.querySelector(".docs-operation-filter");
    var query = input ? input.value.trim().toLowerCase() : "";
    var rows = root.querySelectorAll("[data-docs-search-text]");
    var visibleCount = 0;
    Array.prototype.forEach.call(rows, function (row) {
      var matches = !query || (row.getAttribute("data-docs-search-text") || "").indexOf(query) !== -1;
      row.hidden = !matches;
      if (matches) visibleCount += 1;
    });
    var emptyMessage = root.querySelector(".docs-empty-message");
    if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
  }

  function bindOperationFilter(root) {
    var input = root.querySelector(".docs-operation-filter");
    if (input) input.addEventListener("input", function () { filterOperations(root); });
    filterOperations(root);
  }

  function renderOperationDetails(operation, prefix) {
    var parameterClass = prefix === "swagger" ? "swagger-operation-parameters" : "redoc-operation-parameters";
    var requestClass = prefix === "swagger" ? "swagger-operation-request-body" : "redoc-operation-request-body";
    var responseClass = prefix === "swagger" ? "swagger-operation-responses" : "redoc-operation-responses";
    var detailsClass = prefix === "swagger" ? "swagger-operation-details" : "redoc-operation-details";
    var parameters = Array.isArray(operation.parameters) ? operation.parameters : [];
    var parameterText = parameters.map(function (parameter) {
      var pieces = [
        parameter.in || "param",
        parameter.name || "",
        renderSchemaLabel(parameter.schema)
      ].filter(Boolean).join(" ");
      return pieces ? pieces + (parameter.required ? " required" : "") : "";
    }).filter(Boolean).join("; ");
    var requestBody = operation.requestBody || {};
    var requestContent = renderContentSchemaList(requestBody.content || {});
    var responses = operation.responses || {};
    var responseText = Object.keys(responses).sort().map(function (statusCode) {
      var response = responses[statusCode] || {};
      var contentLabels = renderContentSchemaList(response.content || {});
      return [statusCode, response.description || "", contentLabels.join(", ")].filter(Boolean).join(" ");
    }).filter(Boolean).join("; ");
    var details = [
      parameterText ? "<span class=\"" + parameterClass + "\">Parameters: " + escapeHtml(parameterText) + "</span>" : "",
      requestContent.length ? "<span class=\"" + requestClass + "\">Request: " + escapeHtml(requestContent.join(", ")) + "</span>" : "",
      responseText ? "<span class=\"" + responseClass + "\">Responses: " + escapeHtml(responseText) + "</span>" : ""
    ].filter(Boolean).join("");
    return details ? "<div class=\"" + detailsClass + "\">" + details + "</div>" : "";
  }

  function renderSchema(root, schema) {
    var paths = schema.paths || {};
    var rows = Object.keys(paths).sort().flatMap(function (path) {
      return Object.keys(paths[path]).sort().map(function (method) {
        var operation = paths[path][method] || {};
        return [
          "<li data-docs-search-text=\"" + escapeHtml(operationSearchText(method, path, operation)) + "\">",
          "<strong>" + escapeHtml(method.toUpperCase()) + "</strong>",
          "<code>" + escapeHtml(path) + "</code>",
          renderOperationMeta(
            operation,
            "swagger-operation-summary",
            "swagger-operation-tag",
            "swagger-operation-description"
          ),
          renderOperationDetails(operation, "swagger"),
          "</li>"
        ].join("");
      });
    }).join("");
    root.innerHTML = [
      "<section class=\"swagger-shell\">",
      "<h1>" + escapeHtml((schema.info && schema.info.title) || "FastAPI") + " - Swagger UI</h1>",
      "<p>OpenAPI source: <code>/openapi.json</code></p>",
      "<p>" + Object.keys(paths).reduce(function (total, path) { return total + Object.keys(paths[path]).length; }, 0) + " operations</p>",
      "<label class=\"docs-operation-filter-label\"><span>Filter operations</span><input class=\"docs-operation-filter\" type=\"search\" placeholder=\"Filter by path, method, tag, summary\" autocomplete=\"off\"></label>",
      "<p class=\"docs-empty-message\" hidden>No matching operations</p>",
      "<ul class=\"swagger-route-list\">" + rows + "</ul>",
      "</section>"
    ].join("");
    bindOperationFilter(root);
  }

  window.SwaggerUIBundle = function (options) {
    var root = document.querySelector((options && options.dom_id) || "#swagger-ui");
    if (!root) return {};
    root.innerHTML = "<section class=\"swagger-shell\"><h1>FastAPI - Swagger UI</h1><p>Loading /openapi.json...</p></section>";
    fetch((options && options.url) || "/openapi.json")
      .then(function (response) { return response.json(); })
      .then(function (schema) { renderSchema(root, schema); })
      .catch(function (error) {
        root.innerHTML = "<section class=\"swagger-shell\"><h1>FastAPI - Swagger UI</h1><p class=\"docs-error\">" + escapeHtml(error.message || error) + "</p></section>";
      });
    return {};
  };
  window.SwaggerUIBundle.presets = { apis: {} };
})();"##,
        "application/javascript; charset=utf-8",
    )
}

async fn swagger_ui_css() -> Response {
    text_response(
        r#":root {
  color-scheme: dark;
  font-family: "Segoe UI", Arial, sans-serif;
  background: #0b1218;
  color: #d8e7f2;
}

body {
  margin: 0;
  background: #0b1218;
}

#swagger-ui,
redoc {
  display: block;
  min-height: 100vh;
}

.swagger-shell,
.redoc-shell {
  padding: 24px;
}

.swagger-shell h1,
.redoc-shell h1 {
  margin: 0 0 8px;
  font-size: 24px;
}

.docs-operation-filter-label {
  display: flex;
  gap: 10px;
  align-items: center;
  max-width: 720px;
  margin: 14px 0;
  color: #a7bdc9;
}

.docs-operation-filter {
  flex: 1;
  min-width: 220px;
  padding: 7px 9px;
  border: 1px solid #2e4758;
  border-radius: 4px;
  background: #0d1720;
  color: #f4faff;
  font: inherit;
}

.docs-operation-filter:focus {
  outline: 1px solid #7ad7ec;
  outline-offset: 1px;
}

.docs-empty-message {
  margin: 8px 0;
  color: #ffcf8a;
}

.swagger-route-list,
.redoc-route-list {
  display: grid;
  gap: 6px;
  padding: 0;
  list-style: none;
}

.swagger-route-list li,
.redoc-route-list li {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 10px;
  border: 1px solid #294050;
  border-radius: 4px;
  background: #111b24;
}

.swagger-route-list strong,
.redoc-route-list strong {
  min-width: 64px;
  color: #7ad7ec;
}

code {
  color: #f4faff;
}

.swagger-route-list code,
.redoc-route-list code {
  word-break: break-all;
}

.swagger-operation-summary,
.redoc-operation-summary {
  flex: 1;
  min-width: 160px;
  color: #b8cbd8;
}

.swagger-operation-tag,
.redoc-operation-tag {
  flex: 0 0 auto;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 6px;
  border: 1px solid #2f566d;
  border-radius: 4px;
  color: #8fc7ff;
  font-size: 12px;
}

.swagger-operation-description,
.redoc-operation-description {
  flex: 1 1 100%;
  margin-left: 76px;
  color: #8fa7b5;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
}

.swagger-operation-details,
.redoc-operation-details {
  display: flex;
  flex: 1 1 100%;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: 76px;
}

.swagger-operation-parameters,
.swagger-operation-request-body,
.swagger-operation-responses,
.redoc-operation-parameters,
.redoc-operation-request-body,
.redoc-operation-responses {
  max-width: 100%;
  padding: 2px 6px;
  border: 1px solid #2e4758;
  border-radius: 4px;
  background: #0d1720;
  color: #a7bdc9;
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.docs-error {
  color: #ff9b9b;
}

@media (max-width: 700px) {
  .swagger-route-list li,
  .redoc-route-list li {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .swagger-operation-summary,
  .redoc-operation-summary {
    min-width: 100%;
  }

  .swagger-operation-description,
  .redoc-operation-description {
    margin-left: 0;
  }

  .swagger-operation-details,
  .redoc-operation-details {
    margin-left: 0;
  }

  .docs-operation-filter-label {
    align-items: flex-start;
    flex-direction: column;
  }

  .docs-operation-filter {
    width: 100%;
    min-width: 0;
  }
}"#,
        "text/css; charset=utf-8",
    )
}

async fn redoc_standalone_js() -> Response {
    text_response(
        r#"(function () {
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char];
    });
  }

  function renderOperationMeta(operation) {
    var summary = operation && operation.summary ? operation.summary : "";
    var tags = operation && Array.isArray(operation.tags) ? operation.tags.join(", ") : "";
    var description = operation && operation.description ? operation.description : "";
    return [
      summary ? "<span class=\"redoc-operation-summary\">" + escapeHtml(summary) + "</span>" : "",
      tags ? "<span class=\"redoc-operation-tag\">" + escapeHtml(tags) + "</span>" : "",
      description ? "<span class=\"redoc-operation-description\">" + escapeHtml(description) + "</span>" : ""
    ].join("");
  }

  function renderSchemaLabel(schema) {
    if (!schema) return "";
    if (schema.$ref) return schema.$ref.replace(/^#\/components\/schemas\//, "");
    if (schema.type === "array" && schema.items) return "array<" + renderSchemaLabel(schema.items) + ">";
    if (schema.type) return schema.format ? schema.type + ":" + schema.format : schema.type;
    if (Array.isArray(schema.anyOf)) {
      return "anyOf(" + schema.anyOf.map(renderSchemaLabel).filter(Boolean).join(" | ") + ")";
    }
    if (Array.isArray(schema.oneOf)) {
      return "oneOf(" + schema.oneOf.map(renderSchemaLabel).filter(Boolean).join(" | ") + ")";
    }
    if (Array.isArray(schema.allOf)) {
      return "allOf(" + schema.allOf.map(renderSchemaLabel).filter(Boolean).join(" & ") + ")";
    }
    if (schema.properties) return "object";
    return "schema";
  }

  function renderContentSchemaList(content) {
    return Object.keys(content || {}).sort().map(function (contentType) {
      var mediaType = content[contentType] || {};
      var schemaLabel = renderSchemaLabel(mediaType.schema);
      return schemaLabel ? contentType + " -> " + schemaLabel : contentType;
    }).filter(Boolean);
  }

  function operationSearchText(method, path, operation) {
    return [
      method,
      path,
      operation.summary || "",
      operation.description || "",
      Array.isArray(operation.tags) ? operation.tags.join(" ") : ""
    ].join(" ").toLowerCase();
  }

  function filterOperations(root) {
    var input = root.querySelector(".docs-operation-filter");
    var query = input ? input.value.trim().toLowerCase() : "";
    var rows = root.querySelectorAll("[data-docs-search-text]");
    var visibleCount = 0;
    Array.prototype.forEach.call(rows, function (row) {
      var matches = !query || (row.getAttribute("data-docs-search-text") || "").indexOf(query) !== -1;
      row.hidden = !matches;
      if (matches) visibleCount += 1;
    });
    var emptyMessage = root.querySelector(".docs-empty-message");
    if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
  }

  function bindOperationFilter(root) {
    var input = root.querySelector(".docs-operation-filter");
    if (input) input.addEventListener("input", function () { filterOperations(root); });
    filterOperations(root);
  }

  function renderOperationDetails(operation, prefix) {
    var parameterClass = prefix === "swagger" ? "swagger-operation-parameters" : "redoc-operation-parameters";
    var requestClass = prefix === "swagger" ? "swagger-operation-request-body" : "redoc-operation-request-body";
    var responseClass = prefix === "swagger" ? "swagger-operation-responses" : "redoc-operation-responses";
    var detailsClass = prefix === "swagger" ? "swagger-operation-details" : "redoc-operation-details";
    var parameters = Array.isArray(operation.parameters) ? operation.parameters : [];
    var parameterText = parameters.map(function (parameter) {
      var pieces = [
        parameter.in || "param",
        parameter.name || "",
        renderSchemaLabel(parameter.schema)
      ].filter(Boolean).join(" ");
      return pieces ? pieces + (parameter.required ? " required" : "") : "";
    }).filter(Boolean).join("; ");
    var requestBody = operation.requestBody || {};
    var requestContent = renderContentSchemaList(requestBody.content || {});
    var responses = operation.responses || {};
    var responseText = Object.keys(responses).sort().map(function (statusCode) {
      var response = responses[statusCode] || {};
      var contentLabels = renderContentSchemaList(response.content || {});
      return [statusCode, response.description || "", contentLabels.join(", ")].filter(Boolean).join(" ");
    }).filter(Boolean).join("; ");
    var details = [
      parameterText ? "<span class=\"" + parameterClass + "\">Parameters: " + escapeHtml(parameterText) + "</span>" : "",
      requestContent.length ? "<span class=\"" + requestClass + "\">Request: " + escapeHtml(requestContent.join(", ")) + "</span>" : "",
      responseText ? "<span class=\"" + responseClass + "\">Responses: " + escapeHtml(responseText) + "</span>" : ""
    ].filter(Boolean).join("");
    return details ? "<div class=\"" + detailsClass + "\">" + details + "</div>" : "";
  }

  class RedocElement extends HTMLElement {
    connectedCallback() {
      var specUrl = this.getAttribute("spec-url") || "/openapi.json";
      this.innerHTML = "<section class=\"redoc-shell\"><h1>FastAPI - ReDoc</h1><p>Loading /openapi.json...</p></section>";
      fetch(specUrl)
        .then(function (response) { return response.json(); })
        .then((schema) => {
          var paths = schema.paths || {};
          var routeRows = Object.keys(paths).sort().flatMap(function (path) {
            return Object.keys(paths[path]).sort().map(function (method) {
              var operation = paths[path][method] || {};
              return [
                "<li data-docs-search-text=\"" + escapeHtml(operationSearchText(method, path, operation)) + "\">",
                "<strong>" + escapeHtml(method.toUpperCase()) + "</strong>",
                "<code>" + escapeHtml(path) + "</code>",
                renderOperationMeta(operation),
                renderOperationDetails(operation, "redoc"),
                "</li>"
              ].join("");
            });
          }).join("");
          this.innerHTML = [
            "<section class=\"redoc-shell\">",
            "<h1>" + escapeHtml((schema.info && schema.info.title) || "FastAPI") + " - ReDoc</h1>",
            "<p>OpenAPI source: <code>/openapi.json</code></p>",
            "<label class=\"docs-operation-filter-label\"><span>Filter operations</span><input class=\"docs-operation-filter\" type=\"search\" placeholder=\"Filter by path, method, tag, summary\" autocomplete=\"off\"></label>",
            "<p class=\"docs-empty-message\" hidden>No matching operations</p>",
            "<ul class=\"redoc-route-list\">" + routeRows + "</ul>",
            "</section>"
          ].join("");
          bindOperationFilter(this);
        })
        .catch((error) => {
          this.innerHTML = "<section class=\"redoc-shell\"><h1>FastAPI - ReDoc</h1><p class=\"docs-error\">" + escapeHtml(error.message || error) + "</p></section>";
        });
    }
  }

  if (!customElements.get("redoc")) {
    customElements.define("redoc", RedocElement);
  }
})();"#,
        "application/javascript; charset=utf-8",
    )
}

async fn info(State(state): State<ApiState>) -> Json<Value> {
    Json(
        state
            .data_config
            .as_ref()
            .map(DataRuntimeConfig::api_info)
            .unwrap_or_else(default_api_info),
    )
}

fn read_plc_runtime_state() -> PlcRuntimeState {
    let config = read_json_object(&plc_server_config_path()).unwrap_or_default();
    let plc_ip = config
        .get("plc_ip")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .unwrap_or("192.168.0.1");

    PlcRuntimeState {
        ip: plc_ip.to_string(),
        rack: config.get("plc_rack").and_then(value_to_i64).unwrap_or(0),
        slot: config.get("plc_slot").and_then(value_to_i64).unwrap_or(0),
        connected: false,
    }
}

fn plc_info_body_default() -> Value {
    plc_info_body_from_state(&read_plc_runtime_state())
}

fn plc_info_body_from_state(state: &PlcRuntimeState) -> Value {
    json!({
        "typeList": ["int", "real", "dword", "string", "bytes", "word", "bool"],
        "plc_ip": state.ip,
        "rack": state.rack,
        "slot": state.slot,
    })
}

fn plc_fake_read_bytes(
    state: &PlcRuntimeState,
    addr: &str,
    requested: usize,
    type_str: &str,
) -> Vec<u8> {
    let mut hasher = DefaultHasher::new();
    state.ip.hash(&mut hasher);
    state.rack.hash(&mut hasher);
    state.slot.hash(&mut hasher);
    state.connected.hash(&mut hasher);
    addr.hash(&mut hasher);
    hasher.write(type_str.as_bytes());

    let normalized_type = type_str.to_ascii_lowercase();
    let byte_count = match normalized_type.as_str() {
        "int" | "word" => requested.max(2),
        "dword" | "real" => requested.max(4),
        "bool" => requested.max(1),
        "string" | "bytes" => requested.max(1),
        _ => requested.max(1),
    };

    let mut value = hasher.finish();
    (0..byte_count)
        .map(|_| {
            value = value
                .wrapping_mul(1_664_525)
                .wrapping_add(1_013_904_223);
            (value & 0xFF) as u8
        })
        .collect()
}

fn plc_parse_plc_value(type_str: &str, bytes: &[u8]) -> Option<Value> {
    match type_str.to_ascii_lowercase().as_str() {
        "int" => {
            if bytes.len() < 2 {
                return None;
            }
            let value = i16::from_be_bytes([bytes[0], bytes[1]]);
            Some(json!(value))
        }
        "real" => {
            if bytes.len() < 4 {
                return None;
            }
            let value = f32::from_bits(u32::from_be_bytes([
                bytes[0],
                bytes[1],
                bytes[2],
                bytes[3],
            ]));
            Some(json!(value))
        }
        "dword" => {
            if bytes.len() < 4 {
                return None;
            }
            Some(json!(u32::from_be_bytes([
                bytes[0],
                bytes[1],
                bytes[2],
                bytes[3],
            ]) as u64))
        }
        "word" => {
            if bytes.len() < 2 {
                return None;
            }
            Some(json!(u16::from_be_bytes([bytes[0], bytes[1]]) as u64))
        }
        "string" => {
            if bytes.is_empty() {
                return Some(json!(String::new()));
            }
            match String::from_utf8(bytes.to_vec()) {
                Ok(text) => Some(json!(text)),
                Err(_) => {
                    let hex = bytes
                        .iter()
                        .map(|byte| format!("{:02x}", byte))
                        .collect::<String>();
                    Some(json!(hex))
                }
            }
        }
        "bytes" => {
            let values = bytes
                .iter()
                .map(|byte| json!(u64::from(*byte)))
                .collect::<Vec<_>>();
            Some(Value::Array(values))
        }
        "bool" => bytes.first().map(|byte| json!((byte & 1) != 0)),
        _ => None,
    }
}

async fn database_info(State(state): State<ApiState>) -> Json<Value> {
    let coil_last = state
        .repository
        .latest_coil()
        .await
        .ok()
        .flatten()
        .map(|row| latest_coil_to_python_json(&row))
        .unwrap_or(Value::Null);

    Json(json!({
        "url": database_url_info(),
        "echo": false,
        "coil_last": coil_last,
    }))
}

async fn defect_dict() -> Json<Value> {
    Json(read_json_value(&defect_classes_config_path()).unwrap_or_else(default_defect_dict))
}

async fn defect_dict_all(State(state): State<ApiState>) -> Result<Json<Value>, ApiError> {
    let rows = state.repository.defect_class_dict().await?;
    Ok(Json(Value::Array(
        rows.iter().map(defect_class_dict_to_python_json).collect(),
    )))
}

async fn set_defect_dict(Json(payload): Json<Value>) -> Result<Json<Value>, ApiError> {
    let config_path = defect_classes_config_path();
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent)?;
    }

    let defect_data = match payload {
        Value::Object(data) => data,
        _ => {
            return Ok(Json(json!({
                "status": "error",
                "error": "defect dict payload must be an object",
            })));
        }
    };
    let count = defect_data.len();

    let mut config = read_json_object(&config_path).unwrap_or_else(|| {
        default_defect_dict()
            .as_object()
            .cloned()
            .unwrap_or_default()
    });
    config.insert("data".to_string(), Value::Object(defect_data));
    config
        .entry("default".to_string())
        .or_insert_with(|| default_defect_dict()["default"].clone());

    fs::write(
        &config_path,
        serde_json::to_vec_pretty(&Value::Object(config))?,
    )?;

    Ok(Json(json!({
        "status": "success",
        "count": count,
    })))
}

async fn grader_list(
    State(state): State<ApiState>,
    Query(query): Query<HashMap<String, String>>,
) -> Result<Response, ApiError> {
    let count = match parse_u32_query(&query, "count", 100) {
        Ok(value) => value,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.grader_list(count).await?;
    Ok(Json(Value::Array(
        rows.iter()
            .map(|row| grader_to_python_json(row, next_text_for_weight(row.weight)))
            .collect(),
    ))
    .into_response())
}

async fn coil_list_value_change_keys() -> Json<Value> {
    Json(json!([
        "二级内径",
        "二级卷径",
        "二级厚度",
        "宽度",
        "PLC位置信息",
        "缺陷",
        "距离平均",
        "识别速度",
        "生产间隔",
    ]))
}

async fn health() -> Json<Value> {
    Json(json!({"status": "ok", "service": "rust_api_service"}))
}

async fn version() -> Json<&'static str> {
    Json("0.1.1")
}

async fn delay() -> Json<i32> {
    Json(0)
}

fn env_string(name: &str) -> String {
    std::env::var(name)
        .map(|value| value.trim().to_string())
        .unwrap_or_default()
}

async fn software_update_manifest() -> Json<Value> {
    let version = {
        let configured = env_string("RUST_API_SOFTWARE_UPDATE_VERSION");
        if configured.is_empty() {
            "0.1.1".to_string()
        } else {
            configured
        }
    };
    let package_file_name = configured_software_update_package_file_name();
    let mut download_url = env_string("RUST_API_SOFTWARE_UPDATE_URL");
    let mut file_name = env_string("RUST_API_SOFTWARE_UPDATE_FILE_NAME");
    if file_name.is_empty() {
        file_name = package_file_name.clone();
    }
    if download_url.is_empty() && !package_file_name.is_empty() {
        download_url = format!("/updates/{package_file_name}");
    }
    let release_notes = env_string("RUST_API_SOFTWARE_UPDATE_NOTES");

    Json(json!({
        "version": version,
        "latest_version": version,
        "current_version": "0.1.1",
        "download_url": download_url,
        "downloadUrl": download_url,
        "package_url": download_url,
        "packageUrl": download_url,
        "file_name": file_name,
        "fileName": file_name,
        "release_notes": release_notes,
        "releaseNotes": release_notes,
        "notes": release_notes,
    }))
}

fn configured_software_update_package_file_name() -> String {
    let package_path = PathBuf::from(env_string("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE"));
    if !package_path.is_file() {
        return String::new();
    }
    package_path
        .file_name()
        .and_then(|value| value.to_str())
        .map(sanitize_download_file_name)
        .unwrap_or_default()
}

async fn software_update_package(Path(file_name): Path<String>) -> Response {
    let package_path = PathBuf::from(env_string("RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE"));
    if package_path.as_os_str().is_empty() || !package_path.is_file() {
        return StatusCode::NOT_FOUND.into_response();
    }

    if !is_plain_download_file_name(&file_name) {
        return StatusCode::NOT_FOUND.into_response();
    }
    let configured_name = package_path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let requested_name = sanitize_download_file_name(&file_name);
    if requested_name.is_empty() || configured_name != requested_name {
        return StatusCode::NOT_FOUND.into_response();
    }

    match fs::read(&package_path) {
        Ok(bytes) => {
            let mut response = bytes_response(bytes, "application/octet-stream");
            let disposition = format!(
                "attachment; filename=\"{}\"",
                requested_name.replace('"', "_")
            );
            response.headers_mut().insert(
                header::CONTENT_DISPOSITION,
                disposition.parse().expect("content disposition"),
            );
            response
        }
        Err(_) => StatusCode::NOT_FOUND.into_response(),
    }
}

fn is_plain_download_file_name(file_name: &str) -> bool {
    !file_name.is_empty()
        && file_name == sanitize_download_file_name(file_name)
        && !file_name.contains(['/', '\\'])
        && !file_name.chars().any(char::is_control)
}

fn sanitize_download_file_name(file_name: &str) -> String {
    file_name
        .split(['/', '\\'])
        .next_back()
        .unwrap_or_default()
        .replace(['\r', '\n'], "")
}

async fn download_test() -> Response {
    let path = download_test_file_path();
    if !path.exists() {
        return Json(json!({"error": "File not found"})).into_response();
    }
    match fs::read(&path) {
        Ok(bytes) => {
            let mut response = bytes_response(bytes, "application/octet-stream");
            response.headers_mut().insert(
                header::CONTENT_DISPOSITION,
                "attachment; filename=\"downloaded_file.zip\""
                    .parse()
                    .expect("content disposition"),
            );
            response
        }
        Err(_) => Json(json!({"error": "File not found"})).into_response(),
    }
}

async fn speedtest_download(Query(query): Query<HashMap<String, String>>) -> Response {
    let size_in_mb = match query.get("size_in_mb") {
        Some(value) => match value.parse::<i64>() {
            Ok(value) => value,
            Err(_) => return fastapi_int_query_error("size_in_mb", value),
        },
        None => 10,
    };
    let total_bytes = if size_in_mb <= 0 {
        0
    } else {
        (size_in_mb as usize).saturating_mul(1024 * 1024)
    };
    bytes_response(vec![b'0'; total_bytes], "application/octet-stream")
}

fn fastapi_int_query_error(field: &str, input: &str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", field],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": input
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_int_path_error(field: &str, input: &str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["path", field],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": input
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_float_query_error(field: &str, input: &str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "float_parsing",
                    "loc": ["query", field],
                    "msg": "Input should be a valid number, unable to parse string as a number",
                    "input": input
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_bool_query_error(field: &str, input: &str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "bool_parsing",
                    "loc": ["query", field],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": input
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_query_value_error(field: &str, input: &str, allowed: &[&str]) -> Response {
    let allowed_values = allowed.join(", ");
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", field],
                    "msg": format!("Input should be one of: {allowed_values}"),
                    "input": input
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_greater_than_equal_query_error(field: &str, input: &str, ge: i32) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "greater_than_equal",
                    "loc": ["query", field],
                    "msg": format!("Input should be greater than or equal to {ge}"),
                    "input": input,
                    "ctx": {
                        "ge": ge
                    }
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_less_than_equal_query_error(field: &str, input: &str, le: i32) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "less_than_equal",
                    "loc": ["query", field],
                    "msg": format!("Input should be less than or equal to {le}"),
                    "input": input,
                    "ctx": {
                        "le": le
                    }
                }
            ]
        })),
    )
        .into_response()
}

fn fastapi_missing_query_error(field: &str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", field],
                    "msg": "Field required",
                    "input": null
                }
            ]
        })),
    )
        .into_response()
}

fn python_internal_server_error_response() -> Response {
    (StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error").into_response()
}

fn python_not_found_response() -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(json!({
            "detail": "Not Found"
        })),
    )
        .into_response()
}

fn parse_required_string_query(
    query: &HashMap<String, String>,
    field: &'static str,
) -> Result<String, Response> {
    query
        .get(field)
        .cloned()
        .ok_or_else(|| fastapi_missing_query_error(field))
}

fn parse_i32_query(
    query: &HashMap<String, String>,
    field: &'static str,
    default: i32,
) -> Result<i32, Response> {
    Ok(parse_optional_i32_query(query, field)?.unwrap_or(default))
}

fn parse_i64_query(
    query: &HashMap<String, String>,
    field: &'static str,
    default: i64,
) -> Result<i64, Response> {
    Ok(parse_optional_i64_query(query, field)?.unwrap_or(default))
}

fn parse_i64_path(value: &str, field: &'static str) -> Result<i64, Response> {
    value
        .parse::<i64>()
        .map_err(|_| fastapi_int_path_error(field, value))
}

fn parse_python_int_converter_path(value: &str) -> Result<i64, Response> {
    if value.is_empty() || !value.chars().all(|character| character.is_ascii_digit()) {
        return Err(python_not_found_response());
    }
    Ok(value.parse::<i64>().unwrap_or(i64::MAX))
}

fn parse_optional_i32_query(
    query: &HashMap<String, String>,
    field: &'static str,
) -> Result<Option<i32>, Response> {
    query
        .get(field)
        .map(|value| {
            value
                .parse::<i32>()
                .map_err(|_| fastapi_int_query_error(field, value))
        })
        .transpose()
}

fn parse_optional_i32_query_range(
    query: &HashMap<String, String>,
    field: &'static str,
    min: i32,
    max: i32,
) -> Result<Option<i32>, Response> {
    let parsed = parse_optional_i32_query(query, field)?;
    let Some(value) = parsed else {
        return Ok(None);
    };
    let input = query.get(field).map(String::as_str).unwrap_or_default();
    if value < min {
        return Err(fastapi_greater_than_equal_query_error(field, input, min));
    }
    if value > max {
        return Err(fastapi_less_than_equal_query_error(field, input, max));
    }
    Ok(Some(value))
}

fn parse_optional_i64_query(
    query: &HashMap<String, String>,
    field: &'static str,
) -> Result<Option<i64>, Response> {
    query
        .get(field)
        .map(|value| {
            value
                .parse::<i64>()
                .map_err(|_| fastapi_int_query_error(field, value))
        })
        .transpose()
}

fn parse_optional_u32_query_range(
    query: &HashMap<String, String>,
    field: &'static str,
    min: u32,
    max: u32,
) -> Result<Option<u32>, Response> {
    let parsed = parse_optional_i32_query(query, field)?;
    let Some(value) = parsed else {
        return Ok(None);
    };
    let input = query.get(field).map(String::as_str).unwrap_or_default();
    if value < min as i32 {
        return Err(fastapi_greater_than_equal_query_error(
            field,
            input,
            min as i32,
        ));
    }
    if value > max as i32 {
        return Err(fastapi_less_than_equal_query_error(
            field,
            input,
            max as i32,
        ));
    }
    Ok(Some(value as u32))
}

fn parse_u32_query(
    query: &HashMap<String, String>,
    field: &'static str,
    default: u32,
) -> Result<u32, Response> {
    match query.get(field) {
        Some(value) => value
            .parse::<u32>()
            .map_err(|_| fastapi_int_query_error(field, value)),
        None => Ok(default),
    }
}

fn parse_optional_u8_query_range(
    query: &HashMap<String, String>,
    field: &'static str,
    min: u8,
    max: u8,
) -> Result<Option<u8>, Response> {
    let parsed = parse_optional_i32_query(query, field)?;
    let Some(value) = parsed else {
        return Ok(None);
    };
    let input = query.get(field).map(String::as_str).unwrap_or_default();
    if value < min as i32 {
        return Err(fastapi_greater_than_equal_query_error(
            field,
            input,
            min as i32,
        ));
    }
    if value > max as i32 {
        return Err(fastapi_less_than_equal_query_error(
            field,
            input,
            max as i32,
        ));
    }
    Ok(Some(value as u8))
}

fn parse_optional_f64_query(
    query: &HashMap<String, String>,
    field: &'static str,
) -> Result<Option<f64>, Response> {
    query
        .get(field)
        .map(|value| {
            value
                .parse::<f64>()
                .map_err(|_| fastapi_float_query_error(field, value))
        })
        .transpose()
}

fn parse_optional_bool_query(
    query: &HashMap<String, String>,
    field: &'static str,
) -> Result<Option<bool>, Response> {
    query
        .get(field)
        .map(|value| match value.trim().to_ascii_lowercase().as_str() {
            "1" | "true" | "t" | "yes" | "y" | "on" => Ok(true),
            "0" | "false" | "f" | "no" | "n" | "off" => Ok(false),
            _ => Err(fastapi_bool_query_error(field, value)),
        })
        .transpose()
}

fn parse_render_query(query: &HashMap<String, String>) -> Result<RenderQuery, Response> {
    Ok(RenderQuery {
        thumbnail: parse_optional_bool_query(query, "thumbnail")?,
        grayscale: parse_optional_bool_query(query, "grayscale")?,
        scale: parse_optional_f64_query(query, "scale")?,
        mask: parse_optional_bool_query(query, "mask")?,
        min_value: parse_optional_i32_query(query, "min_value")?,
        max_value: parse_optional_i32_query(query, "max_value")?,
        min_value_compat: parse_optional_i32_query(query, "minValue")?,
        max_value_compat: parse_optional_i32_query(query, "maxValue")?,
    })
}

fn parse_error_image_query(query: &HashMap<String, String>) -> Result<ErrorImageQuery, Response> {
    let _mask = parse_optional_bool_query(query, "mask")?;
    Ok(ErrorImageQuery {
        scale: parse_optional_f64_query(query, "scale")?,
        min_value: parse_optional_f64_query(query, "minValue")?,
        max_value: parse_optional_f64_query(query, "maxValue")?,
        force_cache: parse_optional_bool_query(query, "force_cache")?,
    })
}

fn parse_image_file_query(query: &HashMap<String, String>) -> Result<ImageFileQuery, Response> {
    Ok(ImageFileQuery {
        width: parse_optional_u32_query_range(query, "width", 1, 20000)?,
        height: parse_optional_u32_query_range(query, "height", 1, 20000)?,
        quality: parse_optional_u8_query_range(query, "quality", 1, 100)?,
        format: parse_image_file_format_query(query)?,
        mask: parse_optional_bool_query(query, "mask")?,
    })
}

fn parse_image_area_query(query: &HashMap<String, String>) -> Result<ImageAreaQuery, Response> {
    Ok(ImageAreaQuery {
        row: parse_optional_i32_query_range(query, "row", -2, 2)?,
        col: parse_optional_i32_query_range(query, "col", 0, 2)?,
        count: parse_optional_i32_query_range(query, "count", 0, 3)?,
        level: parse_optional_i32_query_range(query, "level", 0, 4)?,
    })
}

fn parse_image_file_format_query(
    query: &HashMap<String, String>,
) -> Result<Option<ImageFileFormat>, Response> {
    let Some(raw) = query.get("format") else {
        return Ok(None);
    };
    match raw.trim().to_ascii_lowercase().as_str() {
        "jpg" | "jpeg" => Ok(Some(ImageFileFormat::Jpeg)),
        "png" => Ok(Some(ImageFileFormat::Png)),
        "" => Ok(None),
        value => Err(fastapi_query_value_error(
            "format",
            value,
            &["jpg", "jpeg", "png"],
        )),
    }
}

fn parse_plc_curve_query(query: &HashMap<String, String>) -> Result<PlcCurveQuery, Response> {
    Ok(PlcCurveQuery {
        start_id: Some(parse_i64_query(query, "start_id", 0)?),
        end_id: Some(parse_i64_query(query, "end_id", 0)?),
        limit: Some(parse_plc_curve_limit_query(query)?),
    })
}

fn parse_plc_curve_limit_query(query: &HashMap<String, String>) -> Result<u32, Response> {
    let value = parse_i64_query(query, "limit", 200)?;
    Ok(value.clamp(1, 2000) as u32)
}

fn parse_sync_summaries_limit(query: &HashMap<String, String>) -> Result<u32, Response> {
    let value = parse_i64_query(query, "limit", 1000)?;
    if value < 0 {
        return Err(python_internal_server_error_response());
    }
    u32::try_from(value).map_err(|_| python_internal_server_error_response())
}

async fn speedtest_upload(headers: HeaderMap, body: Bytes) -> (StatusCode, Json<Value>) {
    let started = Instant::now();
    let Some((filename, file_size)) = parse_multipart_file_upload(&headers, &body) else {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["body", "file"],
                        "msg": "Field required",
                        "input": null
                    }
                ]
            })),
        );
    };
    let upload_time = started.elapsed().as_secs_f64().max(0.000_001);
    let file_size_mb = file_size as f64 / (1024.0 * 1024.0);
    let upload_speed_mb_s = file_size_mb / upload_time;
    (
        StatusCode::OK,
        Json(json!({
            "filename": filename,
            "file_size_mb": round_2(file_size_mb),
            "upload_time_s": round_2(upload_time),
            "upload_speed_mb_s": round_2(upload_speed_mb_s),
        })),
    )
}

async fn runtime_info(State(state): State<ApiState>) -> Json<Value> {
    Json(state.runtime_info_value())
}

fn runtime_info_uncached() -> Value {
    let developer_mode = runtime_developer_mode();
    json!({
        "python_version": runtime_python_version(),
        "cache_mode": runtime_cache_mode(),
        "cpu_model": runtime_cpu_model(),
        "gpus": runtime_gpu_models(),
        "is_local": developer_mode,
        "developer_mode": developer_mode,
        "offline_mode": runtime_offline_mode(),
    })
}

fn runtime_python_version() -> String {
    if let Ok(value) = std::env::var("RUST_API_PYTHON_VERSION") {
        return value;
    }
    if let Ok(value) = std::env::var("PYTHON_VERSION") {
        return value;
    }
    std::process::Command::new("python")
        .args(["-c", "import sys; print(sys.version)"])
        .output()
        .ok()
        .filter(|output| output.status.success())
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|value| value.trim().to_string())
        .unwrap_or_default()
}

fn runtime_cache_mode() -> String {
    let mode = std::env::var("RUST_API_CACHE_MODE")
        .or_else(|_| std::env::var("IMAGE_CACHE_BACKEND"))
        .or_else(|_| std::env::var("CACHE_BACKEND"))
        .unwrap_or_else(|_| "memory".to_string())
        .to_ascii_lowercase();
    if mode == "redis" {
        mode
    } else {
        "memory".to_string()
    }
}

fn runtime_cpu_model() -> String {
    std::env::var("PROCESSOR_IDENTIFIER")
        .or_else(|_| std::env::var("PROCESSOR_ARCHITECTURE"))
        .unwrap_or_else(|_| std::env::consts::ARCH.to_string())
}

fn runtime_gpu_models() -> Vec<String> {
    if let Ok(value) = std::env::var("RUST_API_GPU_MODELS") {
        return value
            .split(';')
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .map(ToOwned::to_owned)
            .collect();
    }

    Vec::new()
}

fn runtime_developer_mode() -> bool {
    runtime_env_flag("API_DEVELOPER_MODE")
        || runtime_config_marker_exists("developer_mode=true")
        || runtime_known_local_host()
}

fn runtime_offline_mode() -> bool {
    runtime_env_flag("API_OFFLINE_MODE") || runtime_config_marker_exists("offline_mode=true")
}

fn runtime_env_flag(name: &str) -> bool {
    std::env::var(name)
        .map(|value| {
            matches!(
                value.to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(false)
}

fn runtime_config_marker_exists(marker: &str) -> bool {
    runtime_config_dir()
        .map(|path| path.join(marker).exists())
        .unwrap_or(false)
}

fn runtime_config_dir() -> Option<PathBuf> {
    if let Ok(value) = std::env::var("CONFIG_3D_DIR") {
        return Some(PathBuf::from(value));
    }
    Some(PathBuf::from(r"D:\CONFIG_3D"))
}

fn runtime_known_local_host() -> bool {
    const LOCAL_HOSTS: [&str; 5] = [
        "lcx_ace",
        "lcx_mov",
        "DESKTOP-94ADH1G",
        "MS-LGKRSZGOVODD",
        "DESKTOP-3VCH6DO",
    ];

    ["COMPUTERNAME", "HOSTNAME"].iter().any(|name| {
        std::env::var(name).ok().is_some_and(|host| {
            LOCAL_HOSTS
                .iter()
                .any(|known| known.eq_ignore_ascii_case(host.trim()))
        })
    })
}

async fn control_config(State(state): State<ApiState>) -> Json<Value> {
    Json(state.control_config_snapshot())
}

async fn set_control_config(
    State(state): State<ApiState>,
    Json(payload): Json<Value>,
) -> Json<Value> {
    state.merge_control_config(payload);
    Json(Value::Null)
}

async fn set_control_property(
    State(state): State<ApiState>,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    let key = match parse_required_string_query(&query, "key") {
        Ok(value) => value,
        Err(response) => return response,
    };
    let value = match parse_required_string_query(&query, "value") {
        Ok(value) => value,
        Err(response) => return response,
    };

    state.set_control_property(key, value);
    Json(Value::Null).into_response()
}

async fn hardware(State(state): State<ApiState>) -> Json<Value> {
    Json(state.hardware_value())
}

async fn capture_status(State(state): State<ApiState>) -> Json<Value> {
    Json(state.capture_status_value().await)
}

async fn capture_status_proxy(State(state): State<ApiState>) -> Json<Value> {
    Json(state.capture_status_value().await)
}

async fn capture_files(Query(query): Query<HashMap<String, String>>) -> Response {
    let clear = match parse_optional_bool_query(&query, "clear") {
        Ok(value) => value,
        Err(response) => return response,
    };
    let path = append_clear_query("/capture/files", clear);
    Json(capture_service_get(&path, Duration::from_millis(5000)).await).into_response()
}

async fn capture_listener_add_file(Query(query): Query<HashMap<String, String>>) -> Response {
    let clear = match parse_optional_bool_query(&query, "clear") {
        Ok(value) => value,
        Err(response) => return response,
    };
    let path = append_clear_query("/getListenerAddFile", clear);
    Json(capture_service_get(&path, Duration::from_millis(5000)).await).into_response()
}

async fn cameras_status(State(state): State<ApiState>) -> Response {
    let result = capture_service_get("/cameras", Duration::from_millis(5000)).await;
    let has_cameras = result
        .get("cameras")
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty());
    if result.get("ok").and_then(Value::as_bool) != Some(false) || has_cameras {
        return Json(result).into_response();
    }
    Json(state.capture_status_value().await).into_response()
}

fn append_clear_query(path: &str, clear: Option<bool>) -> String {
    match clear {
        Some(true) => format!("{path}?clear=true"),
        Some(false) | None => path.to_string(),
    }
}

async fn capture_camera_status_default() -> Response {
    let mut cameras = capture_cameras();
    let Some(camera) = cameras.pop() else {
        return (StatusCode::NOT_FOUND, Json(json!({"detail": "未找到相机: 无"}))).into_response();
    };
    Json(camera_service_get(&camera, "/camera/status").await).into_response()
}

async fn capture_camera_set_params(Json(payload): Json<Value>) -> Response {
    let mut cameras = capture_cameras();
    let Some(camera) = cameras.pop() else {
        return (StatusCode::NOT_FOUND, Json(json!({"detail": "未找到相机: 无"}))).into_response();
    };
    let camera_key = camera_string(&camera, "key");
    camera_service_post(&camera_key, CameraPostAction::Params, payload).await
}

async fn capture_camera_reconnect() -> Response {
    let mut cameras = capture_cameras();
    let Some(camera) = cameras.pop() else {
        return (StatusCode::NOT_FOUND, Json(json!({"detail": "未找到相机: 无"}))).into_response();
    };
    let camera_key = camera_string(&camera, "key");
    camera_service_post(&camera_key, CameraPostAction::Reconnect, json!({})).await
}

async fn capture_camera_status(Path(camera_key): Path<String>) -> Response {
    let Some(camera) = find_capture_camera(&camera_key) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({"detail": format!("camera not found: {camera_key}")})),
        )
            .into_response();
    };
    Json(camera_service_get(&camera, "/camera/status").await).into_response()
}

async fn capture_camera_files(
    Path(camera_key): Path<String>,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    let Some(camera) = find_capture_camera(&camera_key) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({"detail": format!("camera not found: {camera_key}")})),
        )
            .into_response();
    };
    let clear = match parse_optional_bool_query(&query, "clear") {
        Ok(value) => value,
        Err(response) => return response,
    };
    let path = append_clear_query(&format!("/cameras/{camera_key}/files"), clear);
    Json(camera_service_get(&camera, &path).await).into_response()
}

async fn cameras_set_params(
    Path(camera_key): Path<String>,
    Json(payload): Json<Value>,
) -> Response {
    camera_service_post(&camera_key, CameraPostAction::Params, payload).await
}

async fn cameras_reconnect(Path(camera_key): Path<String>) -> Response {
    camera_service_post(&camera_key, CameraPostAction::Reconnect, json!({})).await
}

async fn camera_adjust(State(state): State<ApiState>) -> Json<Value> {
    Json(state.camera_adjust_value().await)
}

async fn camera_adjust_value_uncached() -> Value {
    let config_path = capture_config_path();
    let cameras = capture_cameras();
    let capture_service_url = capture_service_base_url();
    let capture_status = capture_service_get("/capture/status", CAPTURE_STATUS_TIMEOUT).await;
    let status_by_key = capture_status
        .get("cameras")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| {
                    let key = item.get("key")?.as_str()?.to_string();
                    Some((key, item.clone()))
                })
                .collect::<HashMap<_, _>>()
        })
        .unwrap_or_default();
    let capture_service_offline = status_by_key.is_empty()
        && capture_status.get("ok").and_then(Value::as_bool) == Some(false);
    let fetched_statuses = if capture_service_offline {
        HashMap::new()
    } else {
        fetch_missing_camera_statuses(&cameras, &status_by_key).await
    };
    let mut camera_items = Vec::new();
    for camera in &cameras {
        let key = camera_string(camera, "key");
        let status = match status_by_key.get(&key) {
            Some(value) => value.clone(),
            None if capture_service_offline => offline_camera_status(camera),
            None => fetched_statuses
                .get(&key)
                .cloned()
                .unwrap_or_else(|| offline_camera_status(camera)),
        };
        camera_items.push(camera_adjust_item_with_status(camera, status));
    }
    json!({
        "configFile": config_path.to_string_lossy(),
        "captureServiceUrl": capture_service_url,
        "captureStatus": {
            "ok": capture_status.get("ok").and_then(Value::as_bool).unwrap_or(false),
            "message": capture_status.get("message").and_then(Value::as_str).unwrap_or(""),
            "cameraCount": capture_status
                .get("cameraCount")
                .and_then(Value::as_u64)
                .map(Value::from)
                .unwrap_or_else(|| json!(camera_items.len())),
        },
        "cameras": camera_items,
    })
}

async fn camera_alarm(State(state): State<ApiState>) -> Json<Value> {
    Json(state.camera_alarm_value().await)
}

async fn camera_alarm_value_uncached() -> Value {
    let mut cameras = capture_cameras();
    let capture_status = capture_service_get("/capture/status", CAPTURE_STATUS_TIMEOUT).await;
    let status_by_key = capture_status
        .get("cameras")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| {
                    let key = item.get("key")?.as_str()?.to_string();
                    Some((key, item.clone()))
                })
                .collect::<HashMap<_, _>>()
        })
        .unwrap_or_default();
    if status_by_key.is_empty()
        && !cameras.is_empty()
        && capture_cameras_look_like_local_placeholders(&cameras)
        && !capture_cameras_match_camera_data(&cameras)
    {
        let server_cameras = server_camera_data_cameras();
        if !server_cameras.is_empty() {
            cameras = server_cameras;
        }
    }
    let fetched_statuses = if status_by_key.is_empty() {
        HashMap::new()
    } else {
        fetch_missing_camera_statuses(&cameras, &status_by_key).await
    };
    let mut body = serde_json::Map::new();
    for camera in &cameras {
        let camera_key = camera_string(camera, "key");
        let status = match status_by_key.get(&camera_key) {
            Some(value) => value.clone(),
            None => {
                if status_by_key.is_empty() {
                    capture_status.clone()
                } else {
                    fetched_statuses
                        .get(&camera_key)
                        .cloned()
                        .unwrap_or_else(|| offline_camera_status(camera))
                }
            }
        };
        let key = camera
            .get("name")
            .and_then(Value::as_str)
            .filter(|value| !value.trim().is_empty())
            .or_else(|| camera.get("key").and_then(Value::as_str))
            .unwrap_or_default()
            .to_string();
        body.insert(key, camera_alarm_item_with_status(camera, &status));
    }
    Value::Object(body)
}

async fn set_camera_adjustment(
    Path(camera_key): Path<String>,
    Json(payload): Json<Value>,
) -> Response {
    camera_service_post(&camera_key, CameraPostAction::Params, payload).await
}

async fn reconnect_camera_adjustment(Path(camera_key): Path<String>) -> Response {
    camera_service_post(&camera_key, CameraPostAction::Reconnect, json!({})).await
}

async fn settings_test_mode_status() -> Json<Value> {
    let project_root = default_project_root();
    let config_file_path = test_mode_config_path(&project_root);
    let config_file_value = read_test_mode_config(&config_file_path).unwrap_or(false);
    let developer_mode = runtime_developer_mode() || config_file_test_mode_enabled(&project_root);

    Json(json!({
        "config_file_exists": config_file_path.exists(),
        "config_file_value": config_file_value,
        "developer_mode": developer_mode,
        "is_local": developer_mode,
        "config_file_path": config_file_path.to_string_lossy(),
    }))
}

async fn settings_test_mode() -> Json<Value> {
    let project_root = default_project_root();
    let config_file_path = test_mode_config_path(&project_root);
    let test_mode = read_test_mode_config(&config_file_path).unwrap_or_else(|| {
        runtime_developer_mode() || config_file_test_mode_enabled(&project_root)
    });

    Json(json!({
        "test_mode": test_mode,
    }))
}

async fn update_settings_test_mode(
    Json(request): Json<TestModeRequest>,
) -> Result<Json<Value>, ApiError> {
    let project_root = default_project_root();
    let config_file_path = test_mode_config_path(&project_root);
    if let Some(parent) = config_file_path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    let mut config = read_json_object(&config_file_path).unwrap_or_default();
    config.insert("test_mode".to_string(), json!(request.enabled));
    std::fs::write(
        &config_file_path,
        serde_json::to_vec_pretty(&Value::Object(config))?,
    )?;

    Ok(Json(json!({
        "status": "success",
        "test_mode": request.enabled,
    })))
}

async fn data_has(State(state): State<ApiState>, Path(coil_id): Path<String>) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    Json(
        state
            .test_mode
            .as_ref()
            .and_then(|test_mode| test_mode.data_has())
            .or_else(|| {
                state
                    .data_config
                    .as_ref()
                    .map(|data_config| data_config.data_has(coil_id))
            })
            .unwrap_or_else(|| {
                json!({
                    "S": {"3D": false, "MESH": false, "JPG": false, "2D": false},
                    "L": {"3D": false, "MESH": false, "JPG": false, "2D": false},
                })
            }),
    )
    .into_response()
}

async fn coil_info(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    let surface = surface.to_ascii_uppercase();
    let test_mode_available = state.test_mode_for_coil(coil_id).is_some();
    let coil_state_response = if test_mode_available {
        coil_state_info_response_with_timeout(&state, coil_id, &surface).await
    } else {
        coil_state_info_response(&state, coil_id, &surface).await
    };
    if let Some(response) = coil_state_response {
        return response;
    }

    Json(
        state
            .test_mode_for_coil(coil_id)
            .and_then(|test_mode| test_mode.coil_info(&surface))
            .or_else(|| {
                state
                    .data_config
                    .as_ref()
                    .and_then(|data_config| runtime_coil_info(data_config, coil_id, &surface))
            })
            .unwrap_or(Value::Null),
    )
    .into_response()
}

fn coil_info_db_timeout() -> Duration {
    std::env::var("RUST_API_COIL_INFO_DB_TIMEOUT_MS")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .map(Duration::from_millis)
        .unwrap_or_else(|| Duration::from_millis(DEFAULT_COIL_INFO_DB_TIMEOUT_MS))
}

async fn coil_state_info_response_with_timeout(
    state: &ApiState,
    coil_id: i64,
    surface: &str,
) -> Option<Response> {
    let body = coil_state_info_body_with_thread_timeout(
        Arc::clone(&state.repository),
        coil_id,
        surface.to_string(),
        coil_info_db_timeout(),
    )
    .await?;
    Some(coil_state_json_response(body))
}

async fn coil_state_info_body_with_thread_timeout(
    repository: Arc<dyn CoilRepository>,
    coil_id: i64,
    surface: String,
    timeout: Duration,
) -> Option<String> {
    let (sender, receiver) = tokio::sync::oneshot::channel();
    thread::spawn(move || {
        let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        else {
            return;
        };
        let body =
            runtime.block_on(async { coil_state_info_body(&repository, coil_id, &surface).await });
        let _ = sender.send(body);
    });
    tokio::time::timeout(timeout, receiver)
        .await
        .ok()?
        .ok()
        .flatten()
}

async fn coil_state_info_response(
    state: &ApiState,
    coil_id: i64,
    surface: &str,
) -> Option<Response> {
    let body = coil_state_info_body(&state.repository, coil_id, surface).await?;
    Some(coil_state_json_response(body))
}

async fn coil_state_info_body(
    repository: &Arc<dyn CoilRepository>,
    coil_id: i64,
    surface: &str,
) -> Option<String> {
    let row = repository.coil_state(coil_id, surface).await.ok()??;
    let json_data = row.json_data.as_deref()?.trim();
    if json_data.is_empty() {
        return None;
    }
    compact_json_preserving_number_text(json_data)
}

fn coil_state_json_response(body: String) -> Response {
    ([(header::CONTENT_TYPE, "application/json")], body).into_response()
}

fn compact_json_preserving_number_text(json_text: &str) -> Option<String> {
    serde_json::from_str::<Value>(json_text).ok()?;

    let mut compacted = String::with_capacity(json_text.len());
    let mut chars = json_text.chars().peekable();
    let mut in_string = false;
    let mut escaped = false;
    while let Some(character) = chars.next() {
        if in_string {
            compacted.push(character);
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == '"' {
                in_string = false;
            }
            continue;
        }

        match character {
            '"' => {
                in_string = true;
                compacted.push(character);
            }
            ' ' | '\n' | '\r' | '\t' => {}
            '-' | '0'..='9' => {
                let mut number_text = String::from(character);
                while let Some(next) = chars.peek().copied() {
                    if matches!(next, '0'..='9' | '.' | 'e' | 'E' | '+' | '-') {
                        number_text.push(next);
                        chars.next();
                    } else {
                        break;
                    }
                }
                if number_text.contains(['e', 'E']) {
                    if let Ok(number) = number_text.parse::<f64>() {
                        if let Ok(serialized) = serde_json::to_string(&number) {
                            compacted.push_str(&serialized);
                            continue;
                        }
                    }
                }
                compacted.push_str(&number_text);
            }
            _ => compacted.push(character),
        }
    }

    Some(compacted)
}

async fn height_data(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    let endpoint = "/coilData/heightData";
    let total_started = Instant::now();
    let context = format!("surface={surface} coil_id={coil_id}");
    let x1 = match parse_i32_query(&query, "x1", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let y1 = match parse_i32_query(&query, "y1", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let mut x2 = match parse_i32_query(&query, "x2", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let mut y2 = match parse_i32_query(&query, "y2", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    if x2 == 0 && y2 == 0 {
        x2 = x1 + 10;
        y2 = y1;
    }
    let parsed_coil_id = coil_id.parse::<i64>().ok();

    if let Some(value) = state
        .test_mode_data_fallback()
        .and_then(|test_mode| test_mode.height_segments(&surface, x1, y1, x2, y2))
    {
        profile_stage(endpoint, "test_mode", total_started, &context);
        return Json(value).into_response();
    }

    let value = parsed_coil_id
        .and_then(|coil_id| {
            let resolve_started = Instant::now();
            let surface_dir = state
                .data_config
                .as_ref()
                .and_then(|data_config| data_config.surface_asset_dir(coil_id, &surface))?;
            profile_stage(endpoint, "resolve_surface_dir", resolve_started, &context);

            let load_depth_started = Instant::now();
            let depth_map = load_depth_map_from_dir(&surface_dir)?;
            profile_stage(endpoint, "load_depth", load_depth_started, &context);

            let load_mask_started = Instant::now();
            let mask = load_mask_image(&surface_dir);
            profile_stage(endpoint, "load_mask", load_mask_started, &context);

            let compute_started = Instant::now();
            let value = real_height_segments(&depth_map, mask.as_ref(), x1, y1, x2, y2);
            profile_stage(endpoint, "compute_segments", compute_started, &context);
            Some(value)
        })
        .unwrap_or_else(|| Value::Array(Vec::new()));
    profile_stage(endpoint, "total", total_started, &context);
    Json(value).into_response()
}

async fn height_point(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    let x = match parse_i32_query(&query, "x", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let y = match parse_i32_query(&query, "y", 0) {
        Ok(value) => value,
        Err(response) => return response,
    };
    Json(height_point_value(
        &state,
        &surface,
        coil_id.parse::<i64>().ok(),
        x,
        y,
    ))
    .into_response()
}

async fn render_image(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let endpoint = "/coilData/Render";
    let total_started = Instant::now();
    let context = format!("surface={surface} coil_id={coil_id}");
    let query = match parse_render_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    if let Some(rendered) = state
        .test_mode_data_fallback()
        .and_then(|test_mode| test_mode.render_image(&surface, &query))
    {
        profile_stage(endpoint, "test_mode", total_started, &context);
        return rendered.into_response();
    }
    let parsed_coil_id = coil_id.parse::<i64>().ok();
    if let Some(rendered) = state
        .data_config
        .as_ref()
        .and_then(|data_config| data_config.surface_asset_dir(parsed_coil_id?, &surface))
        .and_then(|surface_dir| render_image_from_surface_dir(&surface_dir, &query))
    {
        profile_stage(endpoint, "total", total_started, &context);
        return rendered.into_response();
    }

    profile_stage(endpoint, "placeholder", total_started, &context);
    RenderedImage::placeholder(query.thumbnail(), query.colormap()).into_response()
}

async fn area_image(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(query): Query<AreaQuery>,
) -> Response {
    let endpoint = "/coilData/Area";
    let total_started = Instant::now();
    let context = format!("surface={surface} coil_id={coil_id}");
    let Some(coil_id) = coil_id.parse::<i64>().ok().filter(|value| *value >= 0) else {
        return python_internal_server_error_response();
    };
    let Some(surface_dir) = surface_dir_for_request(&state, coil_id, &surface) else {
        return python_internal_server_error_response();
    };
    let load_depth_started = Instant::now();
    let Some(depth_map) = load_depth_map_from_dir(&surface_dir) else {
        return python_internal_server_error_response();
    };
    profile_stage(endpoint, "load_depth", load_depth_started, &context);
    let _mask = query.mask.unwrap_or(true);
    let encode_started = Instant::now();
    match generate_area_png(&depth_map, &query) {
        Some(bytes) => {
            profile_stage(endpoint, "render_encode", encode_started, &context);
            profile_stage(endpoint, "total", total_started, &context);
            bytes_response(bytes, "image/png")
        }
        None => {
            profile_stage(endpoint, "placeholder", total_started, &context);
            transparent_png_response(100, 100)
        }
    }
}

async fn error_image(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let endpoint = "/coilData/Error";
    let total_started = Instant::now();
    let context = format!("surface={surface} coil_id={coil_id}");
    let query = match parse_error_image_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    let Some(surface_dir) = surface_dir_for_string_request(&state, &coil_id, &surface) else {
        return transparent_png_response(100, 100);
    };
    let min_threshold = query.min_value.map(abs_finite_f64).unwrap_or(0.0);
    let max_threshold = query.max_value.map(abs_finite_f64).unwrap_or(255.0);

    let error_cache = surface_dir.join("png").join("Error.png");
    if error_cache.exists() && error_cache_matches(&error_cache, min_threshold, max_threshold) {
        let read_started = Instant::now();
        if let Ok(bytes) = fs::read(&error_cache) {
            profile_stage(endpoint, "read_cache", read_started, &context);
            profile_stage(endpoint, "total", total_started, &context);
            return bytes_response(bytes, "image/png");
        }
    }

    if query.force_cache.unwrap_or(false) {
        return transparent_png_response(100, 100);
    }

    let load_depth_started = Instant::now();
    let Some(depth_map) = load_depth_map_from_dir(&surface_dir) else {
        return transparent_png_response(100, 100);
    };
    profile_stage(endpoint, "load_depth", load_depth_started, &context);
    let render_started = Instant::now();
    match generate_error_png(&depth_map, None, &query) {
        Some(bytes) => {
            profile_stage(endpoint, "render_encode", render_started, &context);
            profile_stage(endpoint, "total", total_started, &context);
            bytes_response(bytes, "image/png")
        }
        None => {
            profile_stage(endpoint, "placeholder", total_started, &context);
            transparent_png_response(100, 100)
        }
    }
}

async fn image_preview(
    State(state): State<ApiState>,
    Path((surface, coil_id, type_)): Path<(String, String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let query = match parse_image_file_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    let Some(surface_dir) = surface_dir_for_string_request(&state, &coil_id, &surface) else {
        return placeholder_jpeg_response();
    };
    match image_file_response_with_query(&surface_dir.join("preview"), &type_, &query) {
        Some(response) => response,
        None => placeholder_jpeg_response(),
    }
}

async fn image_source(
    State(state): State<ApiState>,
    Path((surface, coil_id, type_)): Path<(String, String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let query = match parse_image_file_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    let Some(surface_dir) = surface_dir_for_string_request(&state, &coil_id, &surface) else {
        return placeholder_jpeg_response();
    };
    let query_mask = query.mask.unwrap_or(false);
    let response = if query_mask {
        image_file_response_with_query_for_path(
            &surface_dir.join("mask").join(format!("{type_}.png")),
            &query,
        )
    } else {
        image_file_response_with_query(&surface_dir.join("jpg"), &type_, &query)
            .or_else(|| image_file_response_with_query(&surface_dir.join("png"), &type_, &query))
    };
    match response {
        Some(response) => response,
        None => placeholder_jpeg_response(),
    }
}

async fn image_area(
    State(state): State<ApiState>,
    Path((surface, coil_id)): Path<(String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let query = match parse_image_area_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    image_area_response(&state, &surface, &coil_id, "AREA", query)
}

async fn image_area_typed(
    State(state): State<ApiState>,
    Path((surface, coil_id, type_)): Path<(String, String, String)>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Response {
    let query = match parse_image_area_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return response,
    };
    let type_ = normalize_area_image_type(&type_);
    image_area_response(&state, &surface, &coil_id, &type_, query)
}

fn image_area_response(
    state: &ApiState,
    surface: &str,
    coil_id: &str,
    type_: &str,
    query: ImageAreaQuery,
) -> Response {
    let endpoint = "/image/area";
    let total_started = Instant::now();
    let context = format!("surface={surface} coil_id={coil_id} type={type_}");
    let Some(surface_dir) = surface_dir_for_string_request(state, coil_id, surface) else {
        return placeholder_jpeg_response();
    };
    let row = query.row.unwrap_or(0);
    let col = query.col.unwrap_or(0);
    let requested_count = query.count.unwrap_or(0);
    let count = if requested_count > 0 { 3 } else { 0 };
    let level = query.level.unwrap_or(4).clamp(0, 4);
    let source_path = area_source_image_path(&surface_dir, type_);

    if requested_count == 0 {
        let metadata_started = Instant::now();
        if let Some((width, height)) =
            area_tile_cache_metadata(&surface_dir, source_path.as_deref())
        {
            profile_stage(endpoint, "metadata_cache", metadata_started, &context);
            return Json(json!({"width": width, "height": height})).into_response();
        }
        let decode_started = Instant::now();
        return match source_path.and_then(|path| image::open(path).ok()) {
            Some(image) => {
                profile_stage(endpoint, "decode_metadata", decode_started, &context);
                Json(json!({"width": image.width(), "height": image.height()})).into_response()
            }
            None => placeholder_jpeg_response(),
        };
    }

    if row == -2 {
        return match area_image_file_response(&surface_dir.join("preview"), type_) {
            Some(response) => response,
            None => placeholder_jpeg_response(),
        };
    }

    if row == -1 || requested_count == 1 {
        let read_started = Instant::now();
        return match area_image_file_response(&surface_dir.join("jpg"), type_)
            .or_else(|| area_image_file_response(&surface_dir.join("png"), type_))
        {
            Some(response) => {
                profile_stage(endpoint, "read_full_area", read_started, &context);
                profile_stage(endpoint, "total", total_started, &context);
                response
            }
            None => placeholder_jpeg_response(),
        };
    }

    let cache_started = Instant::now();
    if let Some(response) =
        area_tile_cache_response(&surface_dir, row, col, level, source_path.as_deref())
    {
        profile_stage(endpoint, "read_tile_cache", cache_started, &context);
        profile_stage(endpoint, "total", total_started, &context);
        return response;
    }
    let l4_started = Instant::now();
    if let Some(response) =
        area_l4_tile_cache_miss_response(&surface_dir, row, col, level, source_path.as_deref())
    {
        profile_stage(endpoint, "read_l4_tile_cache", l4_started, &context);
        profile_stage(endpoint, "total", total_started, &context);
        return response;
    }
    let Some(path) = source_path else {
        return placeholder_jpeg_response();
    };
    let crop_started = Instant::now();
    let Some(tile) = crop_image_area_tile(&path, row, col, count) else {
        return placeholder_jpeg_response();
    };
    profile_stage(endpoint, "decode_crop", crop_started, &context);
    let resize_started = Instant::now();
    let level_tile = resize_area_tile_for_level(&tile, level);
    profile_stage(endpoint, "resize_tile", resize_started, &context);
    let encode_started = Instant::now();
    match encode_luma_jpeg(&level_tile, area_tile_jpeg_quality(level)) {
        Some(bytes) => {
            profile_stage(endpoint, "encode_tile", encode_started, &context);
            write_area_l4_tile_cache_from_source(&surface_dir, &path, count);
            let _ = write_area_tile_cache_bytes(&surface_dir, row, col, level, &bytes);
            let mut response = bytes_response(bytes, "image/jpeg");
            response.headers_mut().insert(
                "X-Tile-Level",
                level.to_string().parse().expect("tile level header"),
            );
            response
                .headers_mut()
                .insert("X-Cache", "fallback".parse().expect("cache header"));
            profile_stage(endpoint, "total", total_started, &context);
            response
        }
        None => placeholder_jpeg_response(),
    }
}

async fn classifier_image(
    State(state): State<ApiState>,
    Path((coil_id, surface, class_name, x, y, w, h)): Path<(
        String,
        String,
        String,
        i32,
        i32,
        i32,
        i32,
    )>,
) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    if let Some(production_surface_dir) =
        production_surface_dir_for_request(&state, coil_id, &surface)
    {
        if let Some(image_path) =
            cached_classifier_image_path(&production_surface_dir, &class_name, coil_id, x, y)
        {
            if let Ok(bytes) = fs::read(&image_path) {
                return bytes_response(bytes, content_type_for_path(&image_path));
            }
        }
    }

    let Some(surface_dir) = surface_dir_for_request(&state, coil_id, &surface) else {
        return RenderedImage::placeholder(false, "GRAY").into_response();
    };

    let Some(source) = load_gray_rgb_image_from_surface_dir(&surface_dir) else {
        return RenderedImage::placeholder(false, "GRAY").into_response();
    };
    let Some((clip_x, clip_y, clip_w, clip_h)) =
        image_clip_box(x, y, w, h, source.width(), source.height())
    else {
        return RenderedImage::placeholder(false, "GRAY").into_response();
    };

    let crop = imageops::crop_imm(&source, clip_x, clip_y, clip_w, clip_h).to_image();
    match encode_rgb_jpeg(&crop, 90) {
        Some(bytes) => bytes_response(bytes, "image/jpeg"),
        None => RenderedImage::placeholder(false, "GRAY").into_response(),
    }
}

async fn defect_image(
    State(state): State<ApiState>,
    Path((surface, coil_id, type_, x, y, w, h)): Path<(
        String,
        String,
        String,
        String,
        String,
        String,
        String,
    )>,
) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    let Ok(x) = parse_defect_image_coord(&x, 0) else {
        return placeholder_jpeg_response();
    };
    let Ok(y) = parse_defect_image_coord(&y, 0) else {
        return placeholder_jpeg_response();
    };
    let Ok(w) = parse_defect_image_coord(&w, 100) else {
        return placeholder_jpeg_response();
    };
    let Ok(h) = parse_defect_image_coord(&h, 100) else {
        return placeholder_jpeg_response();
    };

    if let Some(production_surface_dir) =
        production_surface_dir_for_request(&state, coil_id, &surface)
    {
        if let Some(image_path) =
            matching_detection_defect_image_path(&production_surface_dir, coil_id, x, y, w, h)
        {
            if let Ok(bytes) = fs::read(&image_path) {
                return bytes_response(bytes, content_type_for_path(&image_path));
            }
        }
    }

    let Some(surface_dir) = surface_dir_for_request(&state, coil_id, &surface) else {
        return placeholder_jpeg_response();
    };

    let Some(source) = load_named_rgb_image_from_surface_dir(&surface_dir, &type_) else {
        return placeholder_jpeg_response();
    };

    let crop = defect_image_crop(&source, x, y, w, h);
    match encode_rgb_jpeg(&crop, 85) {
        Some(bytes) => bytes_response(bytes, "image/jpeg"),
        None => placeholder_jpeg_response(),
    }
}

async fn clip_max_image(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
    Query(query): Query<ClipMaxImageQuery>,
) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    let Some(surface_dir) = surface_dir_for_request(&state, coil_id, &surface) else {
        return Json(Value::Null).into_response();
    };
    let output_dir = query
        .save_url
        .filter(|value| !value.trim().is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| surface_dir.clone())
        .join("clip_max");

    if output_dir.exists() {
        return Json(Value::Null).into_response();
    }
    if fs::create_dir_all(&output_dir).is_err() {
        return Json(Value::Null).into_response();
    }

    let _ = clip_max_images_from_surface_dir(&surface_dir, &output_dir, coil_id, &surface);
    Json(Value::Null).into_response()
}

async fn camera_data(Path((coil_id, camera_key)): Path<(String, String)>) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    match camera_data_value(coil_id, &camera_key) {
        Some(value) => Json(value).into_response(),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": format!("camera not found: {camera_key}")})),
        )
            .into_response(),
    }
}

async fn ws_height_point(
    State(state): State<ApiState>,
    websocket: WebSocketUpgrade,
) -> impl IntoResponse {
    websocket.on_upgrade(move |socket| ws_height_point_loop(socket, state))
}

async fn ws_height_point_loop(mut socket: WebSocket, state: ApiState) {
    while let Some(message) = socket.recv().await {
        match message {
            Ok(Message::Text(text)) => {
                let Some(response) = ws_height_point_response(&state, &text) else {
                    let _ = socket.send(Message::Close(None)).await;
                    break;
                };
                if socket
                    .send(Message::Text(response.to_string().into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }
            Ok(Message::Close(_)) => break,
            Ok(_) => {}
            Err(_) => break,
        }
    }
}

async fn run_re_detection_worker(
    repository: Arc<dyn CoilRepository>,
    re_detection: Arc<Mutex<ReDetectionState>>,
    generation: u64,
    start_id: i64,
    end_id: i64,
) {
    if let Some(command) = external_re_detection_command(start_id, end_id) {
        let total = match re_detection.lock() {
            Ok(mut state) => {
                if state.generation != generation {
                    return;
                }
                state.running = true;
                state.refresh_progress();
                state.append_message(format!(
                    "start external reDetection worker: {}",
                    command.display()
                ));
                state.total
            }
            Err(_) => return,
        };

        if total <= 0 {
            if let Ok(mut state) = re_detection.lock() {
                state.running = false;
            }
        } else {
            match run_re_detection_command(command, &re_detection, generation).await {
                Ok(message) => {
                    let mut state = match re_detection.lock() {
                        Ok(state) => state,
                        Err(_) => return,
                    };
                    if state.generation != generation {
                        return;
                    }
                    state.queue.clear();
                    state.done = state.total.max(0);
                    state.pending = 0;
                    state.running = false;
                    state.error.clear();
                    state.refresh_progress();
                    if !message.is_empty() {
                        state.append_message(message);
                    }
                    state.append_message("重识别外部执行器已完成".to_string());
                    return;
                }
                Err(error) => {
                    let mut state = match re_detection.lock() {
                        Ok(state) => state,
                        Err(_) => return,
                    };
                    if state.generation != generation {
                        return;
                    }
                    state.append_message(format!("重识别外部执行器失败，回退内置处理: {error}"));
                    state.running = true;
                    state.error = error;
                }
            }
        }
    }

    run_re_detection_fallback_worker(repository, re_detection, generation).await;
}

async fn run_re_detection_fallback_worker(
    repository: Arc<dyn CoilRepository>,
    re_detection: Arc<Mutex<ReDetectionState>>,
    generation: u64,
) {
    loop {
        tokio::time::sleep(Duration::from_millis(300)).await;

        let Some(coil_id) = ({
            let mut state = match re_detection.lock() {
                Ok(state) => state,
                Err(_) => return,
            };
            if state.generation != generation {
                return;
            }

            let next = state.consume_next_coil();
            if next.is_some() {
                state.running = true;
                state.refresh_progress();
            }
            next
        }) else {
            return;
        };

        let processing_error = match repository.secondary_coils(coil_id).await {
            Ok(_) => None,
            Err(error) => Some(error.to_string()),
        };

        tokio::time::sleep(Duration::from_millis(500)).await;

        {
            let mut state = match re_detection.lock() {
                Ok(state) => state,
                Err(_) => return,
            };
            if state.generation != generation {
                return;
            }
            if let Some(error) = processing_error {
                state.error = error;
            }
            state.mark_done();
            if !state.running {
                return;
            }
        }
    }
}

async fn run_re_detection_command(
    command: ExternalCommandInvocation,
    re_detection: &Arc<Mutex<ReDetectionState>>,
    generation: u64,
) -> Result<String, String> {
    let output = Command::new(&command.executable)
        .args(&command.args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|error| format!("无法启动重识别执行器: {error}"))?;

    if let Ok(mut state) = re_detection.lock() {
        if state.generation != generation {
            return Ok("任务已被新的请求覆盖".to_string());
        }
        state.append_message(format!(
            "外部重识别执行器已退出: code={}",
            output.status.code().unwrap_or(-1),
        ));
    }

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let details = format!("stdout={stdout}\nstderr={stderr}").trim().to_string();
        return Err(format!(
            "外部重识别执行器失败 {}: {}",
            output.status.code().unwrap_or(-1),
            details
        ));
    }

    let mut message = "外部重识别执行器已成功返回".to_string();
    if let Ok(stdout) = String::from_utf8(output.stdout.clone()) {
        let tail = stdout
            .lines()
            .filter_map(|line| {
                let line = line.trim();
                if line.is_empty() {
                    None
                } else {
                    Some(line.to_string())
                }
            })
            .last();
        if let Some(line) = tail {
            message = line;
        }
    }

    Ok(message)
}


async fn re_detection_status(State(state): State<ApiState>) -> Json<Value> {
    Json(state.re_detection_status())
}

async fn re_detection_start(
    State(state): State<ApiState>,
    Path((from_id, to_id)): Path<(String, String)>,
) -> Response {
    let from_id = match parse_python_int_converter_path(&from_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let to_id = match parse_python_int_converter_path(&to_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    Json(state.start_re_detection(from_id, to_id).await).into_response()
}

async fn ws_re_detection(
    State(state): State<ApiState>,
    websocket: WebSocketUpgrade,
) -> impl IntoResponse {
    websocket.on_upgrade(move |socket| ws_re_detection_loop(socket, state))
}

async fn ws_re_detection_loop(mut socket: WebSocket, state: ApiState) {
    let mut status_tick = tokio::time::interval(Duration::from_secs(1));
    status_tick.tick().await;

    loop {
        tokio::select! {
            message = socket.recv() => {
                match message {
                    Some(Ok(Message::Text(text))) => {
                        if ws_re_detection_response(&state, &text).await.is_none() {
                            let _ = socket.send(Message::Close(None)).await;
                            break;
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Ok(_)) => {}
                    Some(Err(_)) => break,
                }
            }
            _ = status_tick.tick() => {
                let response = state.re_detection_status();
                if socket
                    .send(Message::Text(response.to_string().into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }
        }
    }
}

async fn get_server_state(State(state): State<ApiState>) -> Json<Value> {
    Json(state.server_state_snapshot())
}

async fn ws_detection_state(
    State(state): State<ApiState>,
    websocket: WebSocketUpgrade,
) -> impl IntoResponse {
    websocket.on_upgrade(move |socket| ws_detection_state_loop(socket, state))
}

async fn ws_detection_state_loop(mut socket: WebSocket, state: ApiState) {
    let mut status_tick = tokio::time::interval(Duration::from_secs(1));
    status_tick.tick().await;

    loop {
        tokio::select! {
            message = socket.recv() => {
                match message {
                    Some(Ok(Message::Text(text))) => {
                        let request: Value = match serde_json::from_str(&text) {
                            Ok(request) => request,
                            Err(_) => {
                                let _ = socket.send(Message::Close(None)).await;
                                break;
                            }
                        };
                        if request.get("from_id").is_none() || request.get("to_id").is_none() {
                            let _ = socket.send(Message::Close(None)).await;
                            break;
                        }
                        if socket
                            .send(Message::Text(
                                state.server_state_snapshot().to_string().into(),
                            ))
                            .await
                            .is_err()
                        {
                            break;
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Ok(_)) => {}
                    Some(Err(_)) => break,
                }
            }
            _ = status_tick.tick() => {
                if socket
                    .send(Message::Text(
                        state.server_state_snapshot().to_string().into(),
                    ))
                    .await
                    .is_err()
                {
                    break;
                }
            }
        }
    }
}

async fn alg_2d_models() -> Json<Value> {
    Json(json!({ "models": list_alg_2d_models() }))
}

async fn alg_2d_test_start(State(state): State<ApiState>, Json(payload): Json<Value>) -> Response {
    if !payload.is_object() {
        return bad_request_detail("payload 必须是对象");
    }

    let model_name = payload
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .trim();
    if model_name.is_empty() {
        return bad_request_detail("model 必填");
    }

    let target = payload
        .get("target")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .trim();
    if target.is_empty() {
        return bad_request_detail("target 必填");
    }

    let output = payload
        .get("output")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .trim();
    if output.is_empty() {
        return bad_request_detail("output 必填");
    }

    let models = list_alg_2d_models();
    if !models
        .iter()
        .any(|model| model.get("name").and_then(Value::as_str) == Some(model_name))
    {
        return bad_request_detail(format!("model not found: {model_name}"));
    }

    let target_path = PathBuf::from(target);
    if !target_path.is_dir() {
        return bad_request_detail(format!("目标路径不存在: {target}"));
    }

    if let Err(error) = fs::create_dir_all(output) {
        return bad_request_detail(format!("无法创建输出目录: {error}"));
    }

    let mode = payload
        .get("mode")
        .and_then(Value::as_str)
        .unwrap_or("copy")
        .trim()
        .to_string();
    let threshold = payload
        .get("threshold")
        .and_then(Value::as_f64)
        .unwrap_or(0.4)
        .clamp(0.01, 0.99);
    let model_type = models
        .iter()
        .filter_map(Value::as_object)
        .find_map(|model_info| {
            if model_info.get("name").and_then(Value::as_str) == Some(model_name) {
                model_info
                    .get("type")
                    .and_then(Value::as_str)
                    .map(|model_type| model_type.to_string())
                    .or_else(|| Some("detector".to_string()))
            } else {
                None
            }
        })
        .unwrap_or_else(|| "detector".to_string());
    let options_obj = payload.get("options").and_then(Value::as_object);
    let classify_save = options_obj
        .and_then(|options| options.get("classify_save"))
        .and_then(Value::as_bool)
        .or_else(|| payload.get("classify_save").and_then(Value::as_bool))
        .unwrap_or(true);
    let save_label = options_obj
        .and_then(|options| options.get("save_label"))
        .and_then(Value::as_bool)
        .or_else(|| payload.get("save_label").and_then(Value::as_bool))
        .unwrap_or(false);
    let save_label = if model_type == "classifier" {
        false
    } else {
        save_label
    };
    let prioritize = options_obj
        .and_then(|options| options.get("prioritize"))
        .and_then(Value::as_bool)
        .or_else(|| payload.get("prioritize").and_then(Value::as_bool))
        .unwrap_or(false);
    let run_options = AlgTestRunOptions {
        model: model_name.to_string(),
        model_type,
        mode: mode.clone(),
        threshold,
        classify_save,
        save_label,
        prioritize,
    };

    let image_paths = list_alg_test_image_files(&target_path);

    match state.alg_test.lock() {
        Ok(mut alg_state) => match alg_state.start() {
            Ok(task_id) => {
                if image_paths.is_empty() {
                    alg_state.update(
                        &task_id,
                        alg_test_progress_payload(
                            Some(&task_id),
                            "完成",
                            0,
                            0,
                            0,
                            0,
                            "未找到可测试图片",
                            true,
                            Instant::now(),
                            Some(&run_options),
                            &AlgTestSummary::default(),
                        ),
                        true,
                    );
                } else {
                    let alg_test_state = Arc::clone(&state.alg_test);
                    let output_path = PathBuf::from(output);
                    let target = target_path.clone();
                    let task_id_for_worker = task_id.clone();
                    let run_options = run_options.clone();
                    thread::spawn(move || {
                        run_alg_test_file_job(
                            alg_test_state,
                            task_id_for_worker,
                            image_paths,
                            output_path,
                            target,
                            run_options,
                        );
                    });
                }
                Json(json!({"ok": true, "task_id": task_id})).into_response()
            }
            Err(error) => bad_request_detail(error),
        },
        Err(_) => bad_request_detail("算法测试状态锁定失败"),
    }
}

async fn alg_2d_test_stop(State(state): State<ApiState>, payload: Option<Json<Value>>) -> Response {
    let task_id = payload
        .as_ref()
        .and_then(|Json(value)| value.as_object())
        .and_then(|object| object.get("task_id"))
        .and_then(Value::as_str);

    match state.alg_test.lock() {
        Ok(mut alg_state) => match alg_state.stop(task_id) {
            Ok(body) => Json(body).into_response(),
            Err(error) => bad_request_detail(error),
        },
        Err(_) => bad_request_detail("算法测试状态锁定失败"),
    }
}

async fn ws_alg_2d_test_progress(
    State(state): State<ApiState>,
    websocket: WebSocketUpgrade,
) -> impl IntoResponse {
    websocket.on_upgrade(move |socket| ws_alg_2d_test_progress_loop(socket, state))
}

async fn ws_alg_2d_test_progress_loop(mut socket: WebSocket, state: ApiState) {
    let mut last_payload = state.alg_test_snapshot();
    if socket
        .send(Message::Text(last_payload.to_string().into()))
        .await
        .is_err()
    {
        return;
    }

    let mut progress_tick = tokio::time::interval(Duration::from_millis(100));
    progress_tick.tick().await;

    loop {
        tokio::select! {
            message = socket.recv() => {
                match message {
                    Some(Ok(Message::Text(_))) => {
                        let payload = state.alg_test_snapshot();
                        last_payload = payload.clone();
                        if socket
                            .send(Message::Text(payload.to_string().into()))
                            .await
                            .is_err()
                        {
                            break;
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Ok(_)) => {}
                    Some(Err(_)) => break,
                }
            }
            _ = progress_tick.tick() => {
                let payload = state.alg_test_snapshot();
                if payload != last_payload {
                    last_payload = payload.clone();
                    if socket
                        .send(Message::Text(payload.to_string().into()))
                        .await
                        .is_err()
                    {
                        break;
                    }
                }
            }
        }
    }
}

async fn set_area_clip_config(
    State(state): State<ApiState>,
    Json(payload): Json<ClipConfigPayload>,
) -> Response {
    let surface_key = match normalize_area_2d_surface_key(&payload.surface_key) {
        Ok(surface_key) => surface_key,
        Err(error) => return bad_request_detail(error),
    };
    let mode = payload.mode.unwrap_or_else(|| "fixed".to_string());
    if !matches!(mode.as_str(), "fixed" | "dynamic") {
        return bad_request_detail(format!("Invalid mode: {mode}"));
    }

    let existing_offset = area_join_config_path()
        .as_deref()
        .and_then(|path| read_area_join_clip_offset(path, &surface_key))
        .unwrap_or(40);
    let default_clip_c = if surface_key.eq_ignore_ascii_case("S") {
        2600.0
    } else {
        4000.0
    };
    let clip_config = json!({
        "mode": mode,
        "fixed": payload.fixed.unwrap_or(200),
        "a": payload.a.unwrap_or(3.0),
        "b": payload.b.unwrap_or(220.0),
        "c": payload.c.unwrap_or(default_clip_c),
        "offset": payload.offset.unwrap_or(existing_offset),
    });
    if let Some(config_path) = area_join_config_path() {
        if let Err(error) = write_area_join_clip_config(&config_path, &surface_key, &clip_config) {
            return bad_request_detail(format!("Failed to update area join config: {error}"));
        }
    }
    match state.area_2d.lock() {
        Ok(mut area_state) => {
            area_state.set_clip_config(surface_key.clone(), clip_config.clone());
            Json(json!({
                "status": "ok",
                "surface_key": surface_key,
                "clip_config": clip_config,
            }))
            .into_response()
        }
        Err(_) => bad_request_detail("2D area state lock poisoned"),
    }
}

fn area_join_config_path() -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(path) = std::env::var("RUST_API_AREA_JOIN_CONFIG") {
        candidates.push(PathBuf::from(path));
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        let config_dir = PathBuf::from(config_dir);
        candidates.push(config_dir.join("area_join.json"));
        candidates.push(config_dir.join("configs").join("area_join.json"));
    }
    candidates.push(PathBuf::from(r"D:\CONFIG_3D\configs\area_join.json"));
    candidates.push(
        default_project_root()
            .join("app")
            .join("algorithm_runtime_2D")
            .join("config")
            .join("area_join.json"),
    );
    candidates.into_iter().find(|path| path.exists())
}

fn read_area_join_clip_offset(path: &FsPath, surface_key: &str) -> Option<i64> {
    let value = read_json_value(path)?;
    value
        .get("surfaces")?
        .get(surface_key)?
        .get("clip_config")?
        .get("offset")?
        .as_i64()
}

fn write_area_join_clip_config(
    path: &FsPath,
    surface_key: &str,
    clip_config: &Value,
) -> std::io::Result<()> {
    let content = fs::read_to_string(path)?;
    let mut value: Value = serde_json::from_str(&content).map_err(std::io::Error::other)?;
    let surface = value
        .get_mut("surfaces")
        .and_then(Value::as_object_mut)
        .and_then(|surfaces| surfaces.get_mut(surface_key))
        .and_then(Value::as_object_mut)
        .ok_or_else(|| std::io::Error::other(format!("Missing surface config: {surface_key}")))?;
    surface.insert("clip_config".to_string(), clip_config.clone());
    let json = serde_json::to_vec_pretty(&value).map_err(std::io::Error::other)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, json)
}

fn area_scan_settings() -> AreaScanSettings {
    AreaScanSettings {
        scan_interval: area_scan_env_usize("ALG_2D_AUTO_SCAN_INTERVAL", 10),
        scan_limit: area_scan_env_usize("ALG_2D_AUTO_SCAN_LIMIT", 20),
        max_queue_depth: area_scan_env_usize("ALG_2D_AUTO_SCAN_MAX_QUEUE_DEPTH", 1),
        min_images_per_camera: area_scan_env_usize("ALG_2D_MIN_IMAGES_PER_CAMERA", 2),
        max_camera_count_skew: area_scan_env_usize("ALG_2D_MAX_CAMERA_COUNT_SKEW", 2),
    }
}

fn area_scan_env_usize(name: &str, default_value: usize) -> usize {
    std::env::var(name)
        .ok()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(default_value)
}

fn read_area_scan_surfaces(path: &FsPath) -> Result<Vec<AreaScanSurface>, String> {
    let value = read_json_value(path)
        .ok_or_else(|| format!("Failed to read area join config: {}", path.display()))?;
    let surfaces = value
        .get("surfaces")
        .and_then(Value::as_object)
        .ok_or_else(|| "Missing surfaces in area join config".to_string())?;

    let mut result = Vec::new();
    for (key, surface_value) in surfaces {
        let Some(surface) = surface_value.as_object() else {
            continue;
        };
        let cameras = surface
            .get("cameras")
            .and_then(Value::as_array)
            .map(|cameras| {
                cameras
                    .iter()
                    .filter_map(|camera| {
                        let folder = camera
                            .get("folder")
                            .and_then(Value::as_str)
                            .filter(|folder| !folder.trim().is_empty())?;
                        Some(AreaScanCamera {
                            folder: PathBuf::from(folder),
                            loss_num: camera.get("loss_num").and_then(Value::as_u64).unwrap_or(0)
                                as usize,
                            max_len: camera.get("max_len").and_then(Value::as_u64).unwrap_or(10)
                                as usize,
                        })
                    })
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();
        let clip_config = surface.get("clip_config").unwrap_or(&Value::Null);
        let default_clip_c = if key.eq_ignore_ascii_case("S") {
            2600.0
        } else {
            4000.0
        };
        let clip_mode = clip_config
            .get("mode")
            .and_then(Value::as_str)
            .unwrap_or("fixed")
            .to_ascii_lowercase();
        let clip_fixed = clip_config
            .get("fixed")
            .and_then(Value::as_u64)
            .unwrap_or(200) as u32;
        let clip_dynamic_a = clip_config.get("a").and_then(area_json_f64).unwrap_or(3.0);
        let clip_dynamic_b = clip_config
            .get("b")
            .and_then(area_json_f64)
            .unwrap_or(220.0);
        let clip_dynamic_c = clip_config
            .get("c")
            .and_then(area_json_f64)
            .unwrap_or(default_clip_c);
        let clip_dynamic_offset = clip_config
            .get("offset")
            .and_then(Value::as_u64)
            .unwrap_or(40) as u32;
        let Some(save_folder) = surface
            .get("save_folder")
            .and_then(Value::as_str)
            .filter(|folder| !folder.trim().is_empty())
        else {
            continue;
        };
        if cameras.is_empty() {
            continue;
        }
        result.push(AreaScanSurface {
            key: key.trim().to_ascii_uppercase(),
            cameras,
            save_folder: PathBuf::from(save_folder),
            clip_mode,
            clip_fixed,
            clip_dynamic_a,
            clip_dynamic_b,
            clip_dynamic_c,
            clip_dynamic_offset,
        });
    }
    Ok(result)
}

fn area_json_f64(value: &Value) -> Option<f64> {
    value
        .as_f64()
        .or_else(|| value.as_i64().map(|number| number as f64))
        .filter(|number| number.is_finite())
}

fn area_source_coil_ids(surfaces: &[AreaScanSurface], limit: usize) -> Vec<i64> {
    let mut coil_ids = Vec::new();
    for surface in surfaces {
        for camera in &surface.cameras {
            let Ok(entries) = fs::read_dir(&camera.folder) else {
                continue;
            };
            let mut camera_ids = entries
                .filter_map(Result::ok)
                .filter(|entry| {
                    entry
                        .file_type()
                        .map(|file_type| file_type.is_dir())
                        .unwrap_or(false)
                })
                .filter_map(|entry| {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if !name.is_empty() && name.chars().all(|ch| ch.is_ascii_digit()) {
                        name.parse::<i64>().ok()
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>();
            camera_ids.sort_unstable_by(|left, right| right.cmp(left));
            for coil_id in camera_ids.into_iter().take(limit) {
                if !coil_ids.contains(&coil_id) {
                    coil_ids.push(coil_id);
                }
            }
        }
    }
    coil_ids.sort_unstable_by(|left, right| right.cmp(left));
    coil_ids.truncate(limit);
    coil_ids
}

fn area_surface_complete(
    surface: &AreaScanSurface,
    coil_id: i64,
    settings: &AreaScanSettings,
) -> bool {
    let mut counts = Vec::new();
    for camera in &surface.cameras {
        let image_folder = camera.folder.join(coil_id.to_string()).join("area");
        if !image_folder.is_dir() {
            return false;
        }
        let Ok(entries) = fs::read_dir(&image_folder) else {
            return false;
        };
        let count = entries
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_type()
                    .map(|file_type| file_type.is_file())
                    .unwrap_or(false)
                    && entry
                        .path()
                        .extension()
                        .and_then(|extension| extension.to_str())
                        .map(|extension| extension.eq_ignore_ascii_case("jpg"))
                        .unwrap_or(false)
            })
            .count();
        if count < settings.min_images_per_camera {
            return false;
        }
        counts.push(count);
    }

    let Some(min_count) = counts.iter().min() else {
        return true;
    };
    let max_count = counts.iter().max().unwrap_or(min_count);
    max_count.saturating_sub(*min_count) <= settings.max_camera_count_skew
}

fn area_surface_processed(surface: &AreaScanSurface, coil_id: i64) -> bool {
    surface
        .save_folder
        .join(coil_id.to_string())
        .join("jpg")
        .join("AREA.jpg")
        .exists()
}

async fn write_area_outputs_for_surfaces(
    coil_id: i64,
    surface_keys: &[String],
    repository: &Arc<dyn CoilRepository>,
) -> std::io::Result<()> {
    let Some(config_path) = area_join_config_path() else {
        return Ok(());
    };
    let surfaces = read_area_scan_surfaces(&config_path).map_err(std::io::Error::other)?;
    let coil_states = repository
        .coil_states(coil_id)
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    for surface_key in surface_keys {
        if let Some(surface) = surfaces
            .iter()
            .find(|surface| surface.key.eq_ignore_ascii_case(surface_key))
        {
            write_area_output_for_surface(surface, coil_id, &coil_states)?;
        }
    }
    Ok(())
}

fn write_area_output_for_surface(
    surface: &AreaScanSurface,
    coil_id: i64,
    coil_states: &[CoilStateRow],
) -> std::io::Result<()> {
    let settings = area_scan_settings();
    if !area_surface_complete(surface, coil_id, &settings) {
        return Ok(());
    }
    let mut cameras = surface.cameras.iter().collect::<Vec<_>>();
    cameras.sort_by_key(|camera| area_camera_position_sort_key(camera));
    let mut strips = Vec::new();
    for camera in cameras {
        strips.push(load_area_camera_strip(camera, coil_id)?);
    }
    if strips.is_empty() {
        return Ok(());
    }

    let clip_nums = area_surface_clip_nums(surface, coil_states);
    let area_image = stack_area_camera_strips(strips, clip_nums);
    if area_image.width() == 0 || area_image.height() == 0 {
        return Ok(());
    }
    let area_path = surface
        .save_folder
        .join(coil_id.to_string())
        .join("jpg")
        .join("AREA.jpg");
    let preview_path = surface
        .save_folder
        .join(coil_id.to_string())
        .join("preview")
        .join("AREA.jpg");
    write_rgb_jpeg_file(&area_path, &area_image, 95)?;
    write_area_tile_cache(&area_path, &area_image)?;

    let preview = DynamicImage::ImageRgb8(area_image.clone())
        .thumbnail(512, 512)
        .to_rgb8();
    write_rgb_jpeg_file(&preview_path, &preview, 90)?;
    Ok(())
}

fn area_camera_position_sort_key(camera: &AreaScanCamera) -> (u8, String) {
    let camera_key = camera
        .folder
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
        .to_string();
    let rank = camera_key
        .rsplit('_')
        .next()
        .and_then(|position| match position {
            "U" => Some(0),
            "M" => Some(1),
            "D" => Some(2),
            _ => None,
        })
        .unwrap_or(3);
    (rank, camera_key)
}

fn load_area_camera_strip(camera: &AreaScanCamera, coil_id: i64) -> std::io::Result<RgbImage> {
    let image_folder = camera.folder.join(coil_id.to_string()).join("area");
    let mut image_paths = fs::read_dir(&image_folder)?
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .file_type()
                .map(|file_type| file_type.is_file())
                .unwrap_or(false)
                && entry
                    .path()
                    .extension()
                    .and_then(|extension| extension.to_str())
                    .map(|extension| extension.eq_ignore_ascii_case("jpg"))
                    .unwrap_or(false)
        })
        .map(|entry| entry.path())
        .collect::<Vec<_>>();
    image_paths.sort_by(|left, right| area_image_sort_key(left).cmp(&area_image_sort_key(right)));
    image_paths = image_paths
        .into_iter()
        .skip(camera.loss_num)
        .take(camera.max_len)
        .collect();
    let camera_key = camera
        .folder
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default();
    if camera_key.contains('S') {
        image_paths.reverse();
    }

    let images = image_paths
        .iter()
        .filter_map(|path| image::open(path).ok().map(|image| image.to_rgb8()))
        .collect::<Vec<_>>();
    if images.is_empty() {
        return Err(std::io::Error::other(format!(
            "No readable area images: {}",
            image_folder.display()
        )));
    }
    Ok(concat_area_camera_images_like_python(&images))
}

fn area_image_sort_key(path: &FsPath) -> (u8, String) {
    let stem = path
        .file_stem()
        .and_then(|stem| stem.to_str())
        .unwrap_or_default();
    if let Ok(number) = stem.parse::<u64>() {
        (0, format!("{number:020}"))
    } else {
        (1, stem.to_string())
    }
}

fn concat_rgb_images_horizontally(images: &[RgbImage]) -> RgbImage {
    let width = images.iter().map(RgbImage::width).sum();
    let height = images.iter().map(RgbImage::height).max().unwrap_or(0);
    let mut output = RgbImage::from_pixel(width, height, Rgb([255, 255, 255]));
    let mut x_offset = 0;
    for image in images {
        copy_rgb_image(&mut output, image, x_offset, 0);
        x_offset += image.width();
    }
    output
}

fn concat_area_camera_images_like_python(images: &[RgbImage]) -> RgbImage {
    if images.len() < 2 {
        return concat_rgb_images_horizontally(images);
    }
    let intersections = area_camera_intersections(images);
    let mut cropped_images = Vec::with_capacity(images.len());
    cropped_images.push(images[0].clone());
    for index in 0..intersections.len() {
        let image = &images[index + 1];
        let mut intersection = image.width();
        for previous in (0..=index).rev() {
            if intersections[previous] != 0 {
                intersection = intersections[previous].min(image.width());
                break;
            }
        }
        let crop_left = image
            .width()
            .saturating_sub(intersection)
            .min(image.width());
        let crop_width = image.width().saturating_sub(crop_left);
        if crop_width == 0 {
            continue;
        }
        cropped_images
            .push(imageops::crop_imm(image, crop_left, 0, crop_width, image.height()).to_image());
    }
    concat_rgb_images_horizontally(&cropped_images)
}

fn area_camera_intersections(images: &[RgbImage]) -> Vec<u32> {
    images
        .windows(2)
        .map(|pair| area_camera_intersection(&pair[0], &pair[1]))
        .collect()
}

fn area_camera_intersection(left: &RgbImage, right: &RgbImage) -> u32 {
    let left_bounds = area_active_bounds_by_row(left);
    let right_bounds = area_active_bounds_by_row(right);
    let height = left.height().min(right.height());
    let width = left.width().min(right.width());
    let mut left_differences = Vec::new();
    let mut right_differences = Vec::new();
    for y in 0..height as usize {
        let Some((left_min, left_max)) = left_bounds.get(y).and_then(|value| *value) else {
            continue;
        };
        let Some((right_min, right_max)) = right_bounds.get(y).and_then(|value| *value) else {
            continue;
        };
        let row = y as u32;
        if area_point_inbounds(left_min, row, width, height)
            && area_point_inbounds(right_min, row, width, height)
        {
            left_differences.push(left_min.abs_diff(right_min));
        }
        if area_point_inbounds(left_max, row, width, height)
            && area_point_inbounds(right_max, row, width, height)
        {
            right_differences.push(left_max.abs_diff(right_max));
        }
    }
    let left_median = area_median_significant_difference(left_differences);
    let right_median = area_median_significant_difference(right_differences);
    match (left_median, right_median) {
        (0, 0) => 0,
        (0, value) | (value, 0) => value,
        (left_value, right_value) => left_value.max(right_value),
    }
}

fn area_active_bounds_by_row(image: &RgbImage) -> Vec<Option<(u32, u32)>> {
    let mut rows = Vec::with_capacity(image.height() as usize);
    for y in 0..image.height() {
        let mut min_x = None;
        let mut max_x = None;
        for x in 0..image.width() {
            if area_pixel_active(image.get_pixel(x, y)) {
                min_x.get_or_insert(x);
                max_x = Some(x);
            }
        }
        rows.push(min_x.zip(max_x));
    }
    rows
}

fn area_pixel_active(pixel: &Rgb<u8>) -> bool {
    pixel.0.iter().any(|channel| *channel > 64)
}

fn area_point_inbounds(x: u32, y: u32, width: u32, height: u32) -> bool {
    x >= 3 && x < width.saturating_sub(3) && y >= 3 && y < height.saturating_sub(3)
}

fn area_median_significant_difference(mut values: Vec<u32>) -> u32 {
    values.retain(|value| *value > 10);
    if values.len() < 5 {
        return 0;
    }
    values.sort_unstable();
    values[values.len() / 2]
}

fn area_surface_clip_nums(surface: &AreaScanSurface, coil_states: &[CoilStateRow]) -> (u32, u32) {
    let fixed = (surface.clip_fixed, surface.clip_fixed);
    if surface.clip_mode != "dynamic" {
        return fixed;
    }
    let Some(median_3d_mm) = coil_states
        .iter()
        .find(|state| state.surface.eq_ignore_ascii_case(&surface.key))
        .and_then(|state| state.median_3d_mm)
    else {
        return fixed;
    };

    let c =
        (median_3d_mm - surface.clip_dynamic_c) * surface.clip_dynamic_a + surface.clip_dynamic_b;
    let c2 = c + surface.clip_dynamic_offset as f64;
    (c.max(0.0) as u32, c2.max(0.0) as u32)
}

fn stack_area_camera_strips(strips: Vec<RgbImage>, clip_nums: (u32, u32)) -> RgbImage {
    let width = strips.iter().map(RgbImage::width).max().unwrap_or(0);
    let height = strips
        .iter()
        .enumerate()
        .map(|(index, image)| {
            let crop_top = match index {
                0 => 0,
                1 => clip_nums.0.min(image.height()),
                _ => clip_nums.1.min(image.height()),
            };
            image.height().saturating_sub(crop_top)
        })
        .sum();
    let mut output = RgbImage::from_pixel(width, height, Rgb([255, 255, 255]));
    let mut y_offset = 0;
    for (index, image) in strips.iter().enumerate() {
        let crop_top = match index {
            0 => 0,
            1 => clip_nums.0.min(image.height()),
            _ => clip_nums.1.min(image.height()),
        };
        let cropped_height = image.height().saturating_sub(crop_top);
        if cropped_height == 0 {
            continue;
        }
        let cropped =
            imageops::crop_imm(image, 0, crop_top, image.width(), cropped_height).to_image();
        copy_rgb_image(&mut output, &cropped, 0, y_offset);
        y_offset += cropped_height;
    }
    output
}

fn copy_rgb_image(output: &mut RgbImage, input: &RgbImage, x_offset: u32, y_offset: u32) {
    for y in 0..input.height() {
        for x in 0..input.width() {
            output.put_pixel(x_offset + x, y_offset + y, *input.get_pixel(x, y));
        }
    }
}

fn write_rgb_jpeg_file(path: &FsPath, image: &RgbImage, quality: u8) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let file = File::create(path)?;
    let mut encoder = JpegEncoder::new_with_quality(file, quality);
    encoder
        .encode_image(&DynamicImage::ImageRgb8(image.clone()))
        .map_err(std::io::Error::other)
}

fn write_area_tile_cache(area_path: &FsPath, image: &RgbImage) -> std::io::Result<()> {
    const TILE_COUNT: u32 = 3;
    const TILE_LEVELS: [(i32, u8); 5] = [(0, 60), (1, 70), (2, 80), (3, 90), (4, 95)];
    let tile_width = image.width() / TILE_COUNT;
    let tile_height = image.height() / TILE_COUNT;
    if tile_width == 0 || tile_height == 0 {
        return Ok(());
    }
    let coil_dir = area_path
        .parent()
        .and_then(FsPath::parent)
        .unwrap_or_else(|| area_path.parent().unwrap_or(area_path));
    let cache_base = coil_dir.join("cache").join("area").join("tild");
    let gray = DynamicImage::ImageRgb8(image.clone()).to_luma8();
    for row in 0..TILE_COUNT {
        for col in 0..TILE_COUNT {
            let left = col * tile_width;
            let top = row * tile_height;
            let right = if col == TILE_COUNT - 1 {
                image.width()
            } else {
                left + tile_width
            };
            let bottom = if row == TILE_COUNT - 1 {
                image.height()
            } else {
                top + tile_height
            };
            let tile = imageops::crop_imm(&gray, left, top, right - left, bottom - top).to_image();
            for (level, quality) in TILE_LEVELS {
                let level_dir = cache_base.join(format!("L{level}"));
                fs::create_dir_all(&level_dir)?;
                let level_path = level_dir.join(format!("{col}_{row}.jpg"));
                let level_tile = DynamicImage::ImageLuma8(resize_area_tile_for_level(&tile, level));
                let file = File::create(level_path)?;
                let mut encoder = JpegEncoder::new_with_quality(file, quality);
                encoder
                    .encode_image(&level_tile)
                    .map_err(std::io::Error::other)?;
            }
        }
    }
    Ok(())
}

fn configured_area_surfaces() -> Option<Vec<AreaScanSurface>> {
    let config_path = area_join_config_path()?;
    let surfaces = read_area_scan_surfaces(&config_path).ok()?;
    if surfaces.is_empty() {
        None
    } else {
        Some(surfaces)
    }
}

fn configured_area_surface_keys() -> Option<Vec<String>> {
    configured_area_surfaces().map(|surfaces| {
        surfaces
            .into_iter()
            .map(|surface| surface.key)
            .collect::<Vec<_>>()
    })
}

fn area_status_context() -> (Vec<String>, serde_json::Map<String, Value>) {
    let Some(surfaces) = configured_area_surfaces() else {
        return (area_2d_surface_keys(), serde_json::Map::new());
    };

    let mut surface_keys = Vec::new();
    let mut clip_configs = serde_json::Map::new();
    for surface in surfaces {
        let surface_key = surface.key.clone();
        clip_configs.insert(surface_key.clone(), surface.clip_config_json());
        surface_keys.push(surface_key);
    }
    (surface_keys, clip_configs)
}

async fn rejoin_area(
    State(state): State<ApiState>,
    Json(payload): Json<RejoinPayload>,
) -> Response {
    let requested_surface_keys = if let Some(surface_key) = payload.surface_key.as_deref() {
        match normalize_area_2d_surface_key(surface_key) {
            Ok(surface_key) => vec![surface_key],
            Err(error) => return bad_request_detail(error),
        }
    } else {
        configured_area_surface_keys().unwrap_or_else(area_2d_surface_keys)
    };
    let available_surface_keys =
        configured_area_surface_keys().unwrap_or_else(area_2d_surface_keys);
    let mut queued = Vec::new();
    let mut failed = Vec::new();
    for surface_key in requested_surface_keys {
        if available_surface_keys
            .iter()
            .any(|available| available.eq_ignore_ascii_case(&surface_key))
        {
            queued.push(surface_key);
        } else {
            failed.push(surface_key);
        }
    }

    match state.area_2d.lock() {
        Ok(mut area_state) => area_state.enqueue(payload.coil_id, &queued),
        Err(_) => return bad_request_detail("2D area state lock poisoned"),
    }
    let _ = write_area_outputs_for_surfaces(payload.coil_id, &queued, &state.repository).await;
    match state.area_2d.lock() {
        Ok(mut area_state) => area_state.complete(payload.coil_id, &queued),
        Err(_) => return bad_request_detail("2D area state lock poisoned"),
    }
    Json(json!({
        "status": "queued",
        "coil_id": payload.coil_id,
        "queued": queued,
        "failed": failed,
    }))
    .into_response()
}

async fn area_status(State(state): State<ApiState>) -> Json<Value> {
    let (surface_keys, configured_clip_configs) = area_status_context();
    Json(
        state
            .area_2d
            .lock()
            .map(|area_state| area_state.status_json(&surface_keys, &configured_clip_configs))
            .unwrap_or_else(|_| json!({"status": "error", "error": "2D area state lock poisoned"})),
    )
}

async fn area_scan(State(state): State<ApiState>) -> Json<Value> {
    let scan_work = match state.area_2d.lock() {
        Ok(mut area_state) => {
            area_state.scan();
            area_state.last_scan_queued.clone()
        }
        Err(_) => {
            return Json(json!({"status": "error", "error": "2D area state lock poisoned"}));
        }
    };

    for (coil_id, reason) in scan_work {
        let surface_keys = area_queue_entry_surface_keys(&reason);
        let _ = write_area_outputs_for_surfaces(coil_id, &surface_keys, &state.repository).await;
        match state.area_2d.lock() {
            Ok(mut area_state) => area_state.complete(coil_id, &surface_keys),
            Err(_) => {
                return Json(json!({"status": "error", "error": "2D area state lock poisoned"}));
            }
        }
    }

    let (surface_keys, configured_clip_configs) = area_status_context();
    Json(
        state
            .area_2d
            .lock()
            .map(|area_state| area_state.status_json(&surface_keys, &configured_clip_configs))
            .unwrap_or_else(|_| json!({"status": "error", "error": "2D area state lock poisoned"})),
    )
}

async fn save_to_sql(State(state): State<ApiState>, Path(sql_file): Path<String>) -> Json<Value> {
    let lower = sql_file.to_ascii_lowercase();
    let path = PathBuf::from(&sql_file);
    let mut backup_state = false;

    if lower.contains(".sql") {
        backup_state = write_sql_dump(&state, &path).is_ok();
    }
    if lower.contains(".db") {
        backup_state = match write_sqlite_snapshot(&state, &path).await {
            Ok(()) => true,
            Err(error) => {
                eprintln!("save_to_sql sqlite backup failed: {error}");
                false
            }
        };
    }

    Json(json!({ "state": backup_state }))
}

fn write_sql_dump(state: &ApiState, path: &FsPath) -> std::io::Result<()> {
    let raw_url = std::env::var(DATABASE_URL_ENV).map_err(|error| {
        std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("{DATABASE_URL_ENV} is required: {error}"),
        )
    })?;
    let url = Url::parse(&raw_url).map_err(|error| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!("invalid database url: {error}"),
        )
    })?;
    let scheme = url.scheme().to_ascii_lowercase();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    if scheme.starts_with("postgres") {
        run_pg_dump(state, &url, path)
    } else {
        run_mysqldump(state, &url, path)
    }
}

fn run_mysqldump(state: &ApiState, url: &Url, path: &FsPath) -> std::io::Result<()> {
    let output = File::create(path)?;
    let mut command = Command::new(sql_dump_executable(state, "mysql"));
    command
        .arg("-h")
        .arg(url.host_str().unwrap_or("127.0.0.1"))
        .arg("-P")
        .arg(url.port().unwrap_or(3306).to_string())
        .arg("-u")
        .arg(database_username(url, "root"))
        .arg(format!(
            "--default-character-set={}",
            database_query_value(url, "charset").unwrap_or_else(|| "utf8mb4".to_string())
        ))
        .arg(database_name(url, "Coil"))
        .stdout(Stdio::from(output));
    if let Some(password) = url.password() {
        command.env("MYSQL_PWD", password);
    }
    run_dump_command(command, path)
}

fn run_pg_dump(state: &ApiState, url: &Url, path: &FsPath) -> std::io::Result<()> {
    let mut command = Command::new(sql_dump_executable(state, "postgres"));
    command
        .arg("-h")
        .arg(url.host_str().unwrap_or("127.0.0.1"))
        .arg("-p")
        .arg(url.port().unwrap_or(5432).to_string())
        .arg("-U")
        .arg(database_username(url, "postgres"))
        .arg("-d")
        .arg(database_name(url, "Coil"))
        .arg("-f")
        .arg(path);
    if let Some(password) = url.password() {
        command.env("PGPASSWORD", password);
    }
    run_dump_command(command, path)
}

fn run_dump_command(mut command: Command, path: &FsPath) -> std::io::Result<()> {
    let status = command.status()?;
    if status.success() {
        Ok(())
    } else {
        Err(std::io::Error::other(format!(
            "database backup failed for {} with status {status}",
            path.display()
        )))
    }
}

fn sql_dump_executable(state: &ApiState, backend: &str) -> String {
    match backend {
        "postgres" => std::env::var("RUST_API_PG_DUMP_EXE")
            .ok()
            .or_else(|| {
                state
                    .data_config
                    .as_ref()
                    .and_then(DataRuntimeConfig::pg_dump_exe)
                    .map(str::to_string)
            })
            .unwrap_or_else(|| "pg_dump.exe".to_string()),
        _ => std::env::var("RUST_API_MYSQLDUMP_EXE")
            .ok()
            .or_else(|| {
                state
                    .data_config
                    .as_ref()
                    .and_then(DataRuntimeConfig::mysqldump_exe)
                    .map(str::to_string)
            })
            .unwrap_or_else(|| "mysqldump.exe".to_string()),
    }
}

fn database_username(url: &Url, default: &str) -> String {
    let username = url.username();
    if username.is_empty() {
        default.to_string()
    } else {
        username.to_string()
    }
}

fn database_name(url: &Url, default: &str) -> String {
    let database = url.path().trim_start_matches('/');
    if database.is_empty() {
        default.to_string()
    } else {
        database.to_string()
    }
}

fn database_query_value(url: &Url, key: &str) -> Option<String> {
    url.query_pairs()
        .find_map(|(query_key, value)| (query_key == key).then(|| value.to_string()))
}

async fn write_sqlite_snapshot(state: &ApiState, path: &FsPath) -> std::io::Result<()> {
    let rows = state
        .repository
        .list_coils(1000)
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let secondary_coil_rows = state
        .repository
        .backup_secondary_coils()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let defects = state
        .repository
        .backup_defects()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let defect_classes = state
        .repository
        .defect_class_dict()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let next_code_rows = state
        .repository
        .next_code_dict()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let manual_defects = state
        .repository
        .backup_manual_defects()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let coil_states = state
        .repository
        .backup_coil_states()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let plc_rows = state
        .repository
        .backup_plc_data()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let coil_checks = state
        .repository
        .backup_coil_checks()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let coil_child_rows = state
        .repository
        .backup_coil_rows()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let alarm_info_rows = state
        .repository
        .backup_alarm_infos()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let point_rows = state
        .repository
        .backup_point_data()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let line_rows = state
        .repository
        .backup_line_data()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let alarm_flat_rows = state
        .repository
        .backup_alarm_flat_rolls()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let alarm_taper_rows = state
        .repository
        .backup_alarm_taper_shapes()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let alarm_loose_rows = state
        .repository
        .backup_alarm_loose_coils()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let taper_shape_point_rows = state
        .repository
        .backup_taper_shape_points()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let server_detection_error_rows = state
        .repository
        .backup_server_detection_errors()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let defect_check_rows = state
        .repository
        .backup_defect_checks()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let data_ellipse_rows = state
        .repository
        .backup_data_ellipses()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let deep_point_rows = state
        .repository
        .backup_deep_points()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let detection_speed_rows = state
        .repository
        .backup_detection_speeds()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let coil_alarm_status_rows = state
        .repository
        .backup_coil_alarm_statuses()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let image_join_rows = state
        .repository
        .backup_image_join_logs()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let defect_statistics_rows = state
        .repository
        .backup_defect_statistics()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let alarm_flat_roll_data_rows = state
        .repository
        .backup_alarm_flat_roll_data()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let cap_true_log_rows = state
        .repository
        .backup_cap_true_logs()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    let cap_true_log_item_rows = state
        .repository
        .backup_cap_true_log_items()
        .await
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    if path.exists() {
        fs::remove_file(path)?;
    }
    let connection =
        Connection::open(path).map_err(|error| std::io::Error::other(error.to_string()))?;
    connection
        .execute_batch(
            "CREATE TABLE IF NOT EXISTS coil_summary_snapshot (
                Id INTEGER PRIMARY KEY,
                CoilNo TEXT NOT NULL,
                CreateTime TEXT,
                CoilType TEXT,
                Thickness REAL,
                Width REAL,
                ActWidth REAL,
                Weight REAL,
                DefectCountS INTEGER,
                DefectCountL INTEGER,
                Grade INTEGER,
                MaxDefectName TEXT,
                MaxDefectSurface TEXT
            );
            CREATE TABLE IF NOT EXISTS coil_summary (
                Id INTEGER PRIMARY KEY,
                CoilNo TEXT,
                CreateTime TEXT,
                CoilType TEXT,
                CoilInside REAL,
                CoilDia REAL,
                Thickness REAL,
                Width REAL,
                Weight REAL,
                ActWidth REAL,
                NextCode TEXT,
                NextInfo TEXT,
                S_DefectGrad INTEGER,
                S_TaperShapeGrad INTEGER,
                S_LooseCoilGrad INTEGER,
                S_FlatRollGrad INTEGER,
                S_Grad INTEGER,
                S_HasAlarm INTEGER,
                S_NextCode TEXT,
                S_NextName TEXT,
                L_DefectGrad INTEGER,
                L_TaperShapeGrad INTEGER,
                L_LooseCoilGrad INTEGER,
                L_FlatRollGrad INTEGER,
                L_Grad INTEGER,
                L_HasAlarm INTEGER,
                L_NextCode TEXT,
                L_NextName TEXT,
                DefectCountS INTEGER,
                DefectCountL INTEGER,
                DetectionTime TEXT,
                CheckStatus INTEGER,
                Status_L INTEGER,
                Status_S INTEGER,
                Grade INTEGER,
                HasCoil INTEGER,
                MaxDefectName TEXT,
                MaxDefectLevel INTEGER,
                MaxDefectSurface TEXT,
                MaxDefectIsShown INTEGER,
                UpdateTime TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_summary_coilno
                ON coil_summary (CoilNo);
            CREATE INDEX IF NOT EXISTS idx_summary_hascoil_id_desc
                ON coil_summary (HasCoil, Id);
            CREATE TABLE IF NOT EXISTS SecondaryCoil (
                Id INTEGER PRIMARY KEY,
                CoilNo TEXT,
                CoilType TEXT,
                CoilInside REAL,
                CoilDia REAL,
                Thickness REAL,
                Width REAL,
                Weight REAL,
                ActWidth REAL,
                CreateTime TEXT
            );
            CREATE TABLE IF NOT EXISTS CoilDefect (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                defectClass INTEGER,
                defectName TEXT,
                defectStatus INTEGER,
                defectTime TEXT,
                defectX INTEGER,
                defectY INTEGER,
                defectW INTEGER,
                defectH INTEGER,
                defectSource REAL,
                defectData TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_coil_defect_secondary_coil_id
                ON CoilDefect (secondaryCoilId);
            CREATE INDEX IF NOT EXISTS idx_coil_defect_secondary_surface
                ON CoilDefect (secondaryCoilId, surface);
            CREATE TABLE IF NOT EXISTS ManualDefect (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                defectClass INTEGER,
                defectName TEXT,
                defectStatus INTEGER,
                defectX INTEGER,
                defectY INTEGER,
                defectW INTEGER,
                defectH INTEGER,
                defectSource REAL,
                defectData TEXT,
                remark TEXT,
                annotator TEXT,
                createTime TEXT,
                updateTime TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_manual_defect_secondary_coil_id
                ON ManualDefect (secondaryCoilId);
            CREATE INDEX IF NOT EXISTS idx_manual_defect_secondary_surface
                ON ManualDefect (secondaryCoilId, surface);
            CREATE TABLE IF NOT EXISTS CoilState (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                startTime TEXT,
                scan3dCoordinateScaleX REAL,
                scan3dCoordinateScaleY REAL,
                scan3dCoordinateScaleZ REAL,
                rotate INTEGER,
                x_rotate INTEGER,
                median_3d REAL,
                median_3d_mm REAL,
                colorFromValue_mm REAL,
                colorToValue_mm REAL,
                start REAL,
                step REAL,
                upperLimit REAL,
                lowerLimit REAL,
                lowerArea INTEGER,
                upperArea INTEGER,
                lowerArea_percent REAL,
                upperArea_percent REAL,
                mask_area INTEGER,
                width INTEGER,
                height INTEGER,
                jsonData TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_coil_state_secondary_coil_id
                ON CoilState (secondaryCoilId);
            CREATE INDEX IF NOT EXISTS idx_coil_state_secondary_surface_id
                ON CoilState (secondaryCoilId, surface, Id DESC);
            CREATE TABLE IF NOT EXISTS PlcData (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                location_S REAL,
                location_L REAL,
                location_laser REAL,
                startTime TEXT,
                pclData TEXT
            );
            CREATE TABLE IF NOT EXISTS CoilCheck (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                status INTEGER,
                msg TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_coil_check_secondary_coil_id
                ON CoilCheck (secondaryCoilId);
            CREATE TABLE IF NOT EXISTS PointData (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                type TEXT,
                x REAL,
                y REAL,
                z REAL,
                z_mm REAL,
                data TEXT,
                crateTime TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_point_data_secondary_coil_id
                ON PointData (secondaryCoilId);
            CREATE INDEX IF NOT EXISTS idx_point_data_secondary_surface
                ON PointData (secondaryCoilId, surface);
            CREATE TABLE IF NOT EXISTS LineData (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                type TEXT,
                center_x REAL,
                center_y REAL,
                width REAL,
                height REAL,
                rotation_angle REAL,
                x1 REAL,
                y1 REAL,
                x2 REAL,
                y2 REAL,
                data TEXT,
                inner_min_value REAL,
                inner_min_value_mm REAL,
                inner_max_value REAL,
                inner_max_value_mm REAL,
                outer_min_value REAL,
                outer_min_value_mm REAL,
                outer_max_value REAL,
                outer_max_value_mm REAL,
                crateTime TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_line_data_secondary_coil_id
                ON LineData (secondaryCoilId);
            CREATE INDEX IF NOT EXISTS idx_line_data_secondary_surface
                ON LineData (secondaryCoilId, surface);
            CREATE TABLE IF NOT EXISTS DefectClassDict (
                Id INTEGER PRIMARY KEY,
                defectClass INTEGER,
                defectName TEXT,
                defectType TEXT,
                defectColor TEXT,
                defectLevel INTEGER,
                visible INTEGER,
                defectDesc TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_defect_class_dict_name
                ON DefectClassDict (defectName);
            CREATE TABLE IF NOT EXISTS AlarmFlatRoll (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                out_circle_width REAL,
                out_circle_height REAL,
                out_circle_center_x REAL,
                out_circle_center_y REAL,
                out_circle_radius REAL,
                inner_circle_width REAL,
                inner_circle_height REAL,
                inner_circle_center_x REAL,
                inner_circle_center_y REAL,
                inner_circle_radius REAL,
                accuracy_x REAL,
                accuracy_y REAL,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS AlarmFlatRollData (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS AlarmInfo (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                nextCode TEXT,
                nextName TEXT,
                taperShapeGrad INTEGER,
                taperShapeMsg TEXT,
                looseCoilGrad INTEGER,
                looseCoilMsg TEXT,
                flatRollGrad INTEGER,
                flatRollMsg TEXT,
                defectGrad INTEGER,
                defectMsg TEXT,
                grad INTEGER,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS AlarmLooseCoil (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                max_width REAL,
                rotation_angle REAL,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS AlarmTaperShape (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                out_taper_max_x REAL,
                out_taper_max_y REAL,
                out_taper_max_value REAL,
                out_taper_min_x REAL,
                out_taper_min_y REAL,
                out_taper_min_value REAL,
                in_taper_max_x REAL,
                in_taper_max_y REAL,
                in_taper_max_value REAL,
                in_taper_min_x REAL,
                in_taper_min_y REAL,
                in_taper_min_value REAL,
                rotation_angle REAL,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS CapTrueLog (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                cameraId INTEGER,
                cameraName TEXT,
                capTrueStartTime TEXT,
                capTrueEndTime TEXT
            );
            CREATE TABLE IF NOT EXISTS CapTrueLogItem (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                cameraId INTEGER,
                cameraName TEXT,
                capTrueTime TEXT,
                imageIndex INTEGER
            );
            CREATE TABLE IF NOT EXISTS Coil (
                Id INTEGER PRIMARY KEY,
                SecondaryCoilId INTEGER,
                DetectionTime TEXT,
                DefectCountS INTEGER,
                DefectCountL INTEGER,
                CheckStatus INTEGER,
                Status_L INTEGER,
                Status_S INTEGER,
                Grade INTEGER,
                Msg TEXT
            );
            CREATE TABLE IF NOT EXISTS CoilAlarmStatus (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                level INTEGER,
                alarmStatus INTEGER,
                alarmFlatRoll INTEGER,
                alarmTaper INTEGER,
                alarmFolding INTEGER,
                alarmDefect INTEGER,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS DataEllipse (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                type TEXT,
                center_x REAL,
                center_y REAL,
                width REAL,
                height REAL,
                rotation_angle REAL,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS DeepPoint (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                x REAL,
                y REAL,
                x_mm REAL,
                y_mm REAL,
                value REAL,
                value_int INTEGER,
                by_user INTEGER,
                draw INTEGER,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS DefectCheck (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                defectId INTEGER,
                key TEXT,
                status INTEGER,
                oldDefectId INTEGER,
                oldDefectName TEXT,
                newDefectId INTEGER,
                newDefectName TEXT,
                addTime TEXT,
                msg TEXT
            );
            CREATE TABLE IF NOT EXISTS DefectStatistics (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT
            );
            CREATE TABLE IF NOT EXISTS DetectionSpeed (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                startTime TEXT,
                endTime TEXT,
                allTime REAL
            );
            CREATE TABLE IF NOT EXISTS ImageJoinLog (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                imageCount INTEGER,
                rotate INTEGER,
                flipH INTEGER,
                flipV INTEGER,
                clip1L INTEGER,
                clip1R INTEGER,
                clip2L INTEGER,
                clip2R INTEGER,
                clip3L INTEGER,
                clip3R INTEGER,
                data TEXT,
                createTime TEXT
            );
            CREATE TABLE IF NOT EXISTS NextCodeDict (
                Id INTEGER PRIMARY KEY,
                code TEXT,
                info TEXT
            );
            CREATE TABLE IF NOT EXISTS ServerDetectionError (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                errorType TEXT,
                time TEXT,
                msg TEXT
            );
            CREATE TABLE IF NOT EXISTS TaperShapePoint (
                Id INTEGER PRIMARY KEY,
                secondaryCoilId INTEGER,
                surface TEXT,
                x REAL,
                y REAL,
                value REAL,
                level INTEGER,
                err_msg TEXT,
                crateTime TEXT,
                data TEXT
            );
            DELETE FROM coil_summary_snapshot;
            DELETE FROM coil_summary;
            DELETE FROM SecondaryCoil;
            DELETE FROM CoilDefect;
            DELETE FROM ManualDefect;
            DELETE FROM CoilState;
            DELETE FROM PlcData;
            DELETE FROM CoilCheck;
            DELETE FROM PointData;
            DELETE FROM LineData;
            DELETE FROM DefectClassDict;
            DELETE FROM AlarmFlatRoll;
            DELETE FROM AlarmFlatRollData;
            DELETE FROM AlarmInfo;
            DELETE FROM AlarmLooseCoil;
            DELETE FROM AlarmTaperShape;
            DELETE FROM CapTrueLog;
            DELETE FROM CapTrueLogItem;
            DELETE FROM Coil;
            DELETE FROM CoilAlarmStatus;
            DELETE FROM DataEllipse;
            DELETE FROM DeepPoint;
            DELETE FROM DefectCheck;
            DELETE FROM DefectStatistics;
            DELETE FROM DetectionSpeed;
            DELETE FROM ImageJoinLog;
            DELETE FROM NextCodeDict;
            DELETE FROM ServerDetectionError;
            DELETE FROM TaperShapePoint;",
        )
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    connection
        .execute_batch("BEGIN IMMEDIATE;")
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    for row in &rows {
        connection
            .execute(
                "INSERT INTO coil_summary_snapshot (
                    Id, CoilNo, CreateTime, CoilType, Thickness, Width, ActWidth, Weight,
                    DefectCountS, DefectCountL, Grade, MaxDefectName, MaxDefectSurface
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
                params![
                    row.id,
                    row.coil_no,
                    row.create_time.as_deref(),
                    row.coil_type.as_deref(),
                    row.thickness,
                    row.width,
                    row.act_width,
                    row.weight,
                    row.defect_count_s,
                    row.defect_count_l,
                    row.grade,
                    row.max_defect_name.as_deref(),
                    row.max_defect_surface.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
        connection
            .execute(
                "INSERT INTO coil_summary (
                    Id, CoilNo, CreateTime, CoilType, CoilInside, CoilDia, Thickness,
                    Width, Weight, ActWidth, NextCode, NextInfo, S_DefectGrad,
                    S_TaperShapeGrad, S_LooseCoilGrad, S_FlatRollGrad, S_Grad,
                    S_HasAlarm, S_NextCode, S_NextName, L_DefectGrad, L_TaperShapeGrad,
                    L_LooseCoilGrad, L_FlatRollGrad, L_Grad, L_HasAlarm, L_NextCode,
                    L_NextName, DefectCountS, DefectCountL, DetectionTime, CheckStatus,
                    Status_L, Status_S, Grade, HasCoil, MaxDefectName, MaxDefectLevel,
                    MaxDefectSurface, MaxDefectIsShown, UpdateTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14,
                    ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24, ?25, ?26, ?27, ?28,
                    ?29, ?30, ?31, ?32, ?33, ?34, ?35, ?36, ?37, ?38, ?39, ?40, ?41)",
                params![
                    row.id,
                    row.coil_no,
                    row.create_time.as_deref(),
                    row.coil_type.as_deref(),
                    row.coil_inside,
                    row.coil_dia,
                    row.thickness,
                    row.width,
                    row.weight,
                    row.act_width,
                    row.next_code.as_deref(),
                    row.next_info.as_deref(),
                    row.s_grad,
                    row.s_grad,
                    row.s_grad,
                    row.s_grad,
                    row.s_grad,
                    row.s_has_alarm,
                    row.next_code.as_deref(),
                    row.next_info.as_deref(),
                    row.l_grad,
                    row.l_grad,
                    row.l_grad,
                    row.l_grad,
                    row.l_grad,
                    row.l_has_alarm,
                    row.next_code.as_deref(),
                    row.next_info.as_deref(),
                    row.defect_count_s,
                    row.defect_count_l,
                    row.detection_time.as_deref(),
                    row.check_status,
                    row.status_l,
                    row.status_s,
                    row.grade,
                    row.has_coil,
                    row.max_defect_name.as_deref(),
                    row.max_defect_level,
                    row.max_defect_surface.as_deref(),
                    true,
                    row.create_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in secondary_coil_rows {
        connection
            .execute(
                "INSERT INTO SecondaryCoil (
                    Id, CoilNo, CoilType, CoilInside, CoilDia, Thickness, Width,
                    Weight, ActWidth, CreateTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    row.id,
                    row.coil_no,
                    row.coil_type.as_deref(),
                    row.coil_inside,
                    row.coil_dia,
                    row.thickness,
                    row.width,
                    row.weight,
                    row.act_width,
                    row.create_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in coil_child_rows {
        connection
            .execute(
                "INSERT INTO Coil (
                    Id, SecondaryCoilId, DetectionTime, DefectCountS, DefectCountL,
                    CheckStatus, Status_L, Status_S, Grade, Msg
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.detection_time.as_deref(),
                    row.defect_count_s,
                    row.defect_count_l,
                    row.check_status,
                    row.status_l,
                    row.status_s,
                    row.grade,
                    row.msg.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in next_code_rows {
        connection
            .execute(
                "INSERT INTO NextCodeDict (Id, code, info) VALUES (?1, ?2, ?3)",
                params![row.id, row.code.as_deref(), row.info.as_deref()],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in alarm_info_rows {
        connection
            .execute(
                "INSERT INTO AlarmInfo (
                    Id, secondaryCoilId, surface, nextCode, nextName,
                    taperShapeGrad, taperShapeMsg, looseCoilGrad, looseCoilMsg,
                    flatRollGrad, flatRollMsg, defectGrad, defectMsg,
                    grad, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_str(),
                    row.next_code.as_deref(),
                    row.next_name.as_deref(),
                    row.taper_shape_grad,
                    row.taper_shape_msg.as_deref(),
                    row.loose_coil_grad,
                    row.loose_coil_msg.as_deref(),
                    row.flat_roll_grad,
                    row.flat_roll_msg.as_deref(),
                    row.defect_grad,
                    row.defect_msg.as_deref(),
                    row.grad,
                    row.create_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for defect in defects {
        let defect_data = defect.defect_data.as_ref().map(Value::to_string);
        connection
            .execute(
                "INSERT INTO CoilDefect (
                    Id, secondaryCoilId, surface, defectClass, defectName, defectStatus,
                    defectTime, defectX, defectY, defectW, defectH, defectSource, defectData
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
                params![
                    defect.id,
                    defect.secondary_coil_id,
                    defect.surface,
                    defect.defect_class,
                    defect.defect_name,
                    defect.defect_status,
                    defect.defect_time.as_deref(),
                    defect.defect_x,
                    defect.defect_y,
                    defect.defect_w,
                    defect.defect_h,
                    defect.defect_source,
                    defect_data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for defect in manual_defects {
        let defect_data = defect.defect_data.as_ref().map(Value::to_string);
        connection
            .execute(
                "INSERT INTO ManualDefect (
                    Id, secondaryCoilId, surface, defectClass, defectName, defectStatus,
                    defectX, defectY, defectW, defectH, defectSource, defectData,
                    remark, annotator, createTime, updateTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)",
                params![
                    defect.id,
                    defect.secondary_coil_id,
                    defect.surface,
                    defect.defect_class,
                    defect.defect_name,
                    defect.defect_status,
                    defect.defect_x,
                    defect.defect_y,
                    defect.defect_w,
                    defect.defect_h,
                    defect.defect_source,
                    defect_data.as_deref(),
                    defect.remark.as_deref(),
                    defect.annotator.as_deref(),
                    defect.defect_time.as_deref(),
                    defect.defect_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in coil_states {
        connection
            .execute(
                "INSERT INTO CoilState (
                    Id, secondaryCoilId, surface, startTime, scan3dCoordinateScaleX,
                    scan3dCoordinateScaleY, scan3dCoordinateScaleZ, rotate, x_rotate,
                    median_3d, median_3d_mm, colorFromValue_mm, colorToValue_mm,
                    start, step, upperLimit, lowerLimit, lowerArea, upperArea,
                    lowerArea_percent, upperArea_percent, mask_area, width, height, jsonData
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24, ?25)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.start_time.as_deref(),
                    row.scan3d_coordinate_scale_x,
                    row.scan3d_coordinate_scale_y,
                    row.scan3d_coordinate_scale_z,
                    row.rotate,
                    row.x_rotate,
                    row.median_3d,
                    row.median_3d_mm,
                    row.color_from_value_mm,
                    row.color_to_value_mm,
                    row.start,
                    row.step,
                    row.upper_limit,
                    row.lower_limit,
                    row.lower_area,
                    row.upper_area,
                    row.lower_area_percent,
                    row.upper_area_percent,
                    row.mask_area,
                    row.width,
                    row.height,
                    row.json_data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in plc_rows {
        connection
            .execute(
                "INSERT INTO PlcData (
                    Id, secondaryCoilId, location_S, location_L, location_laser, startTime, pclData
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.location_s,
                    row.location_l,
                    row.location_laser,
                    row.start_time.as_deref(),
                    row.pcl_data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in coil_checks {
        connection
            .execute(
                "INSERT INTO CoilCheck (
                    Id, secondaryCoilId, status, msg
                ) VALUES (?1, ?2, ?3, ?4)",
                params![row.id, row.secondary_coil_id, row.status, row.msg],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in point_rows {
        connection
            .execute(
                "INSERT INTO PointData (
                    Id, secondaryCoilId, surface, type, x, y, z, z_mm, data, crateTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.point_type.as_deref(),
                    row.x,
                    row.y,
                    row.z,
                    row.z_mm,
                    row.data.as_deref(),
                    row.crate_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in line_rows {
        connection
            .execute(
                "INSERT INTO LineData (
                    Id, secondaryCoilId, surface, type, center_x, center_y, width, height,
                    rotation_angle, x1, y1, x2, y2, data, inner_min_value, inner_min_value_mm,
                    inner_max_value, inner_max_value_mm, outer_min_value, outer_min_value_mm,
                    outer_max_value, outer_max_value_mm, crateTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20, ?21, ?22, ?23)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.line_type.as_deref(),
                    row.center_x,
                    row.center_y,
                    row.width,
                    row.height,
                    row.rotation_angle,
                    row.x1,
                    row.y1,
                    row.x2,
                    row.y2,
                    row.data.as_deref(),
                    row.inner_min_value,
                    row.inner_min_value_mm,
                    row.inner_max_value,
                    row.inner_max_value_mm,
                    row.outer_min_value,
                    row.outer_min_value_mm,
                    row.outer_max_value,
                    row.outer_max_value_mm,
                    row.crate_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in defect_classes {
        connection
            .execute(
                "INSERT INTO DefectClassDict (
                    Id, defectClass, defectName, defectType, defectColor,
                    defectLevel, visible, defectDesc
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    row.id,
                    row.defect_class,
                    row.defect_name,
                    row.defect_type.as_deref(),
                    row.defect_color.as_deref(),
                    row.defect_level,
                    row.visible,
                    row.defect_desc.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in alarm_flat_rows {
        connection
            .execute(
                "INSERT INTO AlarmFlatRoll (
                    Id, secondaryCoilId, surface, out_circle_width, out_circle_height,
                    out_circle_center_x, out_circle_center_y, out_circle_radius,
                    inner_circle_width, inner_circle_height, inner_circle_center_x,
                    inner_circle_center_y, inner_circle_radius, accuracy_x, accuracy_y,
                    level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.out_circle_width,
                    row.out_circle_height,
                    row.out_circle_center_x,
                    row.out_circle_center_y,
                    row.out_circle_radius,
                    row.inner_circle_width,
                    row.inner_circle_height,
                    row.inner_circle_center_x,
                    row.inner_circle_center_y,
                    row.inner_circle_radius,
                    row.accuracy_x,
                    row.accuracy_y,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in alarm_taper_rows {
        connection
            .execute(
                "INSERT INTO AlarmTaperShape (
                    Id, secondaryCoilId, surface, out_taper_max_x, out_taper_max_y,
                    out_taper_max_value, out_taper_min_x, out_taper_min_y,
                    out_taper_min_value, in_taper_max_x, in_taper_max_y,
                    in_taper_max_value, in_taper_min_x, in_taper_min_y,
                    in_taper_min_value, rotation_angle, level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.out_taper_max_x,
                    row.out_taper_max_y,
                    row.out_taper_max_value,
                    row.out_taper_min_x,
                    row.out_taper_min_y,
                    row.out_taper_min_value,
                    row.in_taper_max_x,
                    row.in_taper_max_y,
                    row.in_taper_max_value,
                    row.in_taper_min_x,
                    row.in_taper_min_y,
                    row.in_taper_min_value,
                    row.rotation_angle,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in alarm_loose_rows {
        connection
            .execute(
                "INSERT INTO AlarmLooseCoil (
                    Id, secondaryCoilId, surface, max_width, rotation_angle,
                    level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.max_width,
                    row.rotation_angle,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in taper_shape_point_rows {
        connection
            .execute(
                "INSERT INTO TaperShapePoint (
                    Id, secondaryCoilId, surface, x, y, value, level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface,
                    row.x,
                    row.y,
                    row.value,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in server_detection_error_rows {
        connection
            .execute(
                "INSERT INTO ServerDetectionError (
                    Id, secondaryCoilId, surface, errorType, time, msg
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.error_type.as_deref(),
                    row.time.as_deref(),
                    row.msg.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in defect_check_rows {
        connection
            .execute(
                "INSERT INTO DefectCheck (
                    Id, secondaryCoilId, defectId, key, status, oldDefectId,
                    oldDefectName, newDefectId, newDefectName, addTime, msg
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.defect_id,
                    row.key.as_deref(),
                    row.status,
                    row.old_defect_id,
                    row.old_defect_name.as_deref(),
                    row.new_defect_id,
                    row.new_defect_name.as_deref(),
                    row.add_time.as_deref(),
                    row.msg.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in data_ellipse_rows {
        connection
            .execute(
                "INSERT INTO DataEllipse (
                    Id, secondaryCoilId, surface, type, center_x, center_y, width,
                    height, rotation_angle, level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.ellipse_type.as_deref(),
                    row.center_x,
                    row.center_y,
                    row.width,
                    row.height,
                    row.rotation_angle,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in deep_point_rows {
        connection
            .execute(
                "INSERT INTO DeepPoint (
                    Id, secondaryCoilId, surface, x, y, x_mm, y_mm, value,
                    value_int, by_user, draw, level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.x,
                    row.y,
                    row.x_mm,
                    row.y_mm,
                    row.value,
                    row.value_int,
                    row.by_user,
                    row.draw,
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in detection_speed_rows {
        connection
            .execute(
                "INSERT INTO DetectionSpeed (
                    Id, secondaryCoilId, surface, startTime, endTime, allTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.start_time.as_deref(),
                    row.end_time.as_deref(),
                    row.all_time,
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in coil_alarm_status_rows {
        connection
            .execute(
                "INSERT INTO CoilAlarmStatus (
                    Id, secondaryCoilId, surface, level, alarmStatus, alarmFlatRoll,
                    alarmTaper, alarmFolding, alarmDefect, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.level,
                    row.alarm_status,
                    row.alarm_flat_roll,
                    row.alarm_taper,
                    row.alarm_folding,
                    row.alarm_defect,
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in image_join_rows {
        connection
            .execute(
                "INSERT INTO ImageJoinLog (
                    Id, secondaryCoilId, surface, imageCount, rotate, flipH, flipV,
                    clip1L, clip1R, clip2L, clip2R, clip3L, clip3R, data, createTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.image_count,
                    row.rotate,
                    row.flip_h,
                    row.flip_v,
                    row.clip1_l,
                    row.clip1_r,
                    row.clip2_l,
                    row.clip2_r,
                    row.clip3_l,
                    row.clip3_r,
                    row.data.as_deref(),
                    row.create_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in defect_statistics_rows {
        connection
            .execute(
                "INSERT INTO DefectStatistics (
                    Id, secondaryCoilId, surface
                ) VALUES (?1, ?2, ?3)",
                params![row.id, row.secondary_coil_id, row.surface.as_deref()],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in alarm_flat_roll_data_rows {
        connection
            .execute(
                "INSERT INTO AlarmFlatRollData (
                    Id, secondaryCoilId, surface, level, err_msg, crateTime, data
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.surface.as_deref(),
                    row.level,
                    row.err_msg.as_deref(),
                    row.crate_time.as_deref(),
                    row.data.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in cap_true_log_rows {
        connection
            .execute(
                "INSERT INTO CapTrueLog (
                    Id, secondaryCoilId, cameraId, cameraName, capTrueStartTime, capTrueEndTime
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.camera_id,
                    row.camera_name.as_deref(),
                    row.cap_true_start_time.as_deref(),
                    row.cap_true_end_time.as_deref(),
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    for row in cap_true_log_item_rows {
        connection
            .execute(
                "INSERT INTO CapTrueLogItem (
                    Id, secondaryCoilId, cameraId, cameraName, capTrueTime, imageIndex
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    row.id,
                    row.secondary_coil_id,
                    row.camera_id,
                    row.camera_name.as_deref(),
                    row.cap_true_time.as_deref(),
                    row.image_index,
                ],
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
    }
    connection
        .execute_batch("COMMIT;")
        .map_err(|error| std::io::Error::other(error.to_string()))?;
    Ok(())
}

async fn backup_image_task(
    State(state): State<ApiState>,
    Path((from_id, to_id, save_folder)): Path<(String, String, String)>,
) -> Response {
    let from_id = match parse_python_int_converter_path(&from_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let to_id = match parse_python_int_converter_path(&to_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    let _ = run_backup_image_task(&state, from_id, to_id, &save_folder);
    Json(Value::Null).into_response()
}

async fn ws_backup_image_task(
    State(state): State<ApiState>,
    websocket: WebSocketUpgrade,
) -> impl IntoResponse {
    websocket.on_upgrade(move |socket| ws_backup_image_task_loop(socket, state))
}

async fn ws_backup_image_task_loop(mut socket: WebSocket, state: ApiState) {
    while let Some(message) = socket.recv().await {
        match message {
            Ok(Message::Text(text)) => {
                let Ok(request) = serde_json::from_str::<BackupImageTaskRequest>(&text) else {
                    let _ = socket.send(Message::Close(None)).await;
                    break;
                };
                if run_backup_image_task(&state, request.from_id, request.to_id, &request.folder)
                    .is_err()
                {
                    let _ = socket.send(Message::Close(None)).await;
                    break;
                }
                if socket
                    .send(Message::Text("100".to_string().into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }
            Ok(Message::Close(_)) => break,
            Ok(_) => {}
            Err(_) => break,
        }
    }
}

fn run_backup_image_task(
    state: &ApiState,
    from_id: i64,
    to_id: i64,
    save_folder: &str,
) -> std::io::Result<usize> {
    let Some(data_config) = state.data_config.as_ref() else {
        return Ok(0);
    };
    let save_root = PathBuf::from(save_folder);
    fs::create_dir_all(&save_root)?;
    let mut copied = 0;
    if from_id >= to_id {
        return Ok(copied);
    }
    for source in data_config.backup_image_sources() {
        let Some(source_name) = source.file_name() else {
            continue;
        };
        let camera_backup_root = save_root.join(source_name);
        for coil_id in from_id..to_id {
            let from_folder = source.join(coil_id.to_string());
            if !from_folder.exists() {
                continue;
            }
            let to_folder = camera_backup_root.join(coil_id.to_string());
            copy_dir_replace(&from_folder, &to_folder)?;
            copied += 1;
        }
        compress_backup_camera_data(&camera_backup_root)?;
    }
    Ok(copied)
}

fn compress_backup_camera_data(camera_root: &FsPath) -> std::io::Result<()> {
    if !camera_root.exists() {
        return Ok(());
    }
    for entry in fs::read_dir(camera_root)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            compress_backup_camera_coil(&entry.path())?;
        }
    }
    Ok(())
}

fn compress_backup_camera_coil(coil_dir: &FsPath) -> std::io::Result<()> {
    let image_dir = case_insensitive_child_dir(coil_dir, "2D");
    if image_dir.exists() {
        for entry in fs::read_dir(&image_dir)? {
            let entry = entry?;
            if entry.file_type()?.is_file() && extension_eq(&entry.path(), "bmp") {
                let _ = compress_bmp_to_jpeg(&entry.path());
            }
        }
    }

    let depth_dir = case_insensitive_child_dir(coil_dir, "3D");
    if depth_dir.exists() {
        for entry in fs::read_dir(&depth_dir)? {
            let entry = entry?;
            if entry.file_type()?.is_file() && extension_eq(&entry.path(), "npy") {
                let _ = compress_npy_to_npz(&entry.path());
            }
        }
    }
    Ok(())
}

fn case_insensitive_child_dir(parent: &FsPath, name: &str) -> PathBuf {
    let direct = parent.join(name);
    if direct.exists() {
        return direct;
    }
    let Ok(entries) = fs::read_dir(parent) else {
        return direct;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir()
            && path
                .file_name()
                .and_then(|value| value.to_str())
                .is_some_and(|value| value.eq_ignore_ascii_case(name))
        {
            return path;
        }
    }
    direct
}

fn extension_eq(path: &FsPath, expected: &str) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case(expected))
}

fn compress_bmp_to_jpeg(path: &FsPath) -> std::io::Result<()> {
    let image = match image::open(path) {
        Ok(image) => image.to_rgb8(),
        Err(_) => return Ok(()),
    };
    let target = path.with_extension("jpg");
    save_rgb_jpeg(&image, &target, 95).map_err(std::io::Error::other)?;
    fs::remove_file(path)?;
    Ok(())
}

fn compress_npy_to_npz(path: &FsPath) -> std::io::Result<()> {
    let bytes = fs::read(path)?;
    let target = path.with_extension("npz");
    let file = File::create(&target)?;
    let mut zip = ZipWriter::new(file);
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    zip.start_file("array.npy", options)
        .map_err(|error: zip::result::ZipError| std::io::Error::other(error.to_string()))?;
    zip.write_all(&bytes)?;
    zip.finish()
        .map_err(|error: zip::result::ZipError| std::io::Error::other(error.to_string()))?;
    fs::remove_file(path)?;
    Ok(())
}

fn copy_dir_replace(from: &FsPath, to: &FsPath) -> std::io::Result<()> {
    if to.exists() {
        fs::remove_dir_all(to)?;
    }
    copy_dir_recursive(from, to)
}

fn copy_dir_recursive(from: &FsPath, to: &FsPath) -> std::io::Result<()> {
    fs::create_dir_all(to)?;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let source_path = entry.path();
        let target_path = to.join(entry.file_name());
        let file_type = entry.file_type()?;
        if file_type.is_dir() {
            copy_dir_recursive(&source_path, &target_path)?;
        } else if file_type.is_file() {
            if let Some(parent) = target_path.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(&source_path, &target_path)?;
        }
    }
    Ok(())
}

async fn coil_list(
    State(state): State<ApiState>,
    Path(number): Path<String>,
) -> Result<Response, ApiError> {
    let number = match parse_i64_path(&number, "number") {
        Ok(number) => number,
        Err(response) => return Ok(response),
    };
    if number < 0 {
        return Ok(python_internal_server_error_response());
    }

    let limit = u32::try_from(number.min(1000)).unwrap_or(1000);
    let rows = state.repository.list_coils(limit).await?;
    if rows.is_empty() {
        if let Some(item) = state.test_mode_coil_fallback() {
            return Ok(Json(Value::Array(vec![item])).into_response());
        }
    }
    Ok(Json(Value::Array(
        rows.iter().map(coil_summary_to_python_json).collect(),
    ))
    .into_response())
}

async fn flush_coil_list(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    if coil_id.is_empty() || !coil_id.chars().all(|character| character.is_ascii_digit()) {
        return Ok(python_not_found_response());
    }
    let coil_id = coil_id.parse::<i64>().unwrap_or(i64::MAX);

    if coil_id <= 0 {
        return Ok(Json(json!({})).into_response());
    }

    let rows = state.repository.list_coils_after(coil_id, 10).await?;
    Ok(Json(json!({
        "coilList": rows.iter().map(coil_summary_to_python_json).collect::<Vec<_>>(),
    }))
    .into_response())
}

async fn search_coil_no(
    State(state): State<ApiState>,
    Path(coil_no): Path<String>,
) -> Result<Json<Value>, ApiError> {
    let rows = state.repository.search_coils_by_no(&coil_no).await?;
    Ok(Json(Value::Array(
        rows.iter().map(coil_summary_to_python_json).collect(),
    )))
}

async fn search_coil_id(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_i64_path(&coil_id, "coil_id") {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.search_coils_by_id(coil_id).await?;
    Ok(Json(Value::Array(
        rows.iter().map(coil_summary_to_python_json).collect(),
    ))
    .into_response())
}

async fn search_datetime(
    State(state): State<ApiState>,
    Path((start, end)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    if !is_python_datetime_path(&start) || !is_python_datetime_path(&end) {
        return Ok(python_internal_server_error_response());
    }

    let rows = state
        .repository
        .search_coils_by_datetime(&start, &end)
        .await?;
    Ok(Json(Value::Array(
        rows.iter().map(coil_summary_to_python_json).collect(),
    ))
    .into_response())
}

fn is_python_datetime_path(value: &str) -> bool {
    NaiveDateTime::parse_from_str(value, "%Y%m%d%H%M").is_ok()
}

async fn coil_detail(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    if coil_id.is_empty() || !coil_id.chars().all(|character| character.is_ascii_digit()) {
        return Ok(python_not_found_response());
    }
    let coil_id = coil_id.parse::<i64>().unwrap_or(i64::MAX);

    let rows = state.repository.search_coils_by_id(coil_id).await?;
    let mut body = if let Some(row) = rows.first() {
        coil_summary_to_python_json(row)
    } else if let Some(detail) = state.repository.coil_detail(coil_id).await? {
        coil_detail_to_python_json(&detail)
    } else {
        return Ok(Json(json!({"error": "Coil not found"})).into_response());
    };
    let alarm_info_values = state.repository.alarm_infos(coil_id).await?;
    apply_detail_alarm_infos(&mut body, &alarm_info_values);

    let mut defects = Vec::new();
    for surface in ["S", "L"] {
        defects.extend(state.repository.defects(coil_id, surface).await?);
    }
    defects.sort_by(|left, right| left.id.cmp(&right.id));
    let max_defect_fields = max_defect_json_fields(&defects);
    let defect_values = defects
        .iter()
        .map(detail_defect_to_python_json)
        .collect::<Vec<_>>();
    let defect_alias_values = defects
        .iter()
        .map(detail_defect_alias_to_python_json)
        .collect::<Vec<_>>();
    let alarm_taper_values = state
        .repository
        .alarm_taper_shapes(coil_id)
        .await?
        .iter()
        .map(detail_alarm_taper_shape_to_python_json)
        .collect::<Vec<_>>();
    let alarm_loose_values = state
        .repository
        .alarm_loose_coils(coil_id)
        .await?
        .iter()
        .map(detail_alarm_loose_coil_to_python_json)
        .collect::<Vec<_>>();
    let alarm_flat_values = state
        .repository
        .alarm_flat_rolls(coil_id)
        .await?
        .iter()
        .map(detail_alarm_flat_roll_to_python_json)
        .collect::<Vec<_>>();
    let taper_shape_point_values = state
        .repository
        .taper_shape_points(coil_id)
        .await?
        .iter()
        .map(taper_shape_point_to_python_json)
        .collect::<Vec<_>>();
    let coil_check_values = state
        .repository
        .coil_checks(coil_id)
        .await?
        .iter()
        .map(coil_check_to_python_json)
        .collect::<Vec<_>>();
    apply_coil_detail_fields(
        &mut body,
        coil_id,
        defect_values,
        taper_shape_point_values,
        alarm_taper_values,
        alarm_loose_values,
        alarm_flat_values,
        coil_check_values,
        defect_alias_values,
        max_defect_fields,
    );
    reorder_detail_root_fields(&mut body);

    Ok(Json(body).into_response())
}

async fn sync_summaries(
    State(state): State<ApiState>,
    Query(query): Query<HashMap<String, String>>,
) -> Result<Response, ApiError> {
    let limit = match parse_sync_summaries_limit(&query) {
        Ok(limit) => limit,
        Err(response) => return Ok(response),
    };
    let synced = state.repository.sync_missing_summaries(limit).await?;
    Ok(Json(json!({
        "synced": synced,
        "message": format!("Synced {synced} summaries"),
    }))
    .into_response())
}

async fn sync_summaries_range(
    State(state): State<ApiState>,
    Json(request): Json<SyncSummariesRangeRequest>,
) -> Result<Json<Value>, ApiError> {
    let Some(coil_ids) = request.coil_ids.filter(|coil_ids| !coil_ids.is_empty()) else {
        return Ok(Json(json!({
            "error": "coil_ids is required",
            "synced": 0,
        })));
    };

    let synced = state.repository.sync_existing_summaries(&coil_ids).await?;

    Ok(Json(json!({
        "synced": synced,
        "message": format!("Updated {synced} summaries"),
    })))
}

async fn coil_alarm(State(state): State<ApiState>, Path(coil_id): Path<String>) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    let flat_rolls = state
        .repository
        .alarm_flat_rolls(coil_id)
        .await
        .unwrap_or_default();
    let taper_shapes = state
        .repository
        .alarm_taper_shapes(coil_id)
        .await
        .unwrap_or_default();
    let loose_coils = state
        .repository
        .alarm_loose_coils(coil_id)
        .await
        .unwrap_or_default();
    let coil_states = state
        .repository
        .coil_states(coil_id)
        .await
        .unwrap_or_default();

    let mut flat_roll_info = Map::new();
    for row in flat_rolls.into_iter().rev() {
        flat_roll_info.insert(row.surface.clone(), alarm_flat_roll_to_python_json(&row));
    }

    let mut taper_shape_info = Map::from_iter([
        ("S".to_string(), Value::Array(Vec::new())),
        ("L".to_string(), Value::Array(Vec::new())),
    ]);
    for row in taper_shapes {
        if let Some(Value::Array(items)) = taper_shape_info.get_mut(&row.surface) {
            items.push(alarm_taper_shape_to_python_json(&row));
        } else {
            taper_shape_info.insert(
                row.surface.clone(),
                Value::Array(vec![alarm_taper_shape_to_python_json(&row)]),
            );
        }
    }

    let scale_by_surface = coil_states
        .iter()
        .filter_map(|row| {
            row.scan3d_coordinate_scale_x
                .filter(|value| value.is_finite() && *value > 0.0)
                .map(|scale| (row.surface.clone(), scale))
        })
        .collect::<std::collections::HashMap<_, _>>();
    let mut loose_coil_info = Map::from_iter([
        ("L".to_string(), Value::Array(Vec::new())),
        ("S".to_string(), Value::Array(Vec::new())),
    ]);
    for row in loose_coils {
        let scale = scale_by_surface.get(&row.surface).copied();
        let value = normalize_loose_alarm_json(alarm_loose_coil_to_python_json(&row), scale);
        if let Some(Value::Array(items)) = loose_coil_info.get_mut(&row.surface) {
            items.push(value);
        } else {
            loose_coil_info.insert(row.surface.clone(), Value::Array(vec![value]));
        }
    }

    Json(json!({
        "FlatRoll": Value::Object(flat_roll_info),
        "TaperShape": Value::Object(taper_shape_info),
        "LooseCoil": Value::Object(loose_coil_info),
    }))
    .into_response()
}

fn normalize_loose_alarm_json(mut alarm: Value, surface_scale: Option<f64>) -> Value {
    let Value::Object(fields) = &mut alarm else {
        return alarm;
    };
    let raw_width = fields
        .get("max_width")
        .and_then(finite_json_number)
        .map(round_mysql_float_for_python_json)
        .unwrap_or(0.0);
    let mut detail = fields
        .get("data")
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .and_then(|value| serde_json::from_str::<Value>(value).ok())
        .and_then(|value| value.as_object().cloned())
        .unwrap_or_default();

    let detail_scale = detail
        .get("max_width_scale")
        .and_then(positive_json_number)
        .map(round_mysql_float_for_python_json);
    let width_scale = positive_f64(surface_scale)
        .map(round_mysql_float_for_python_json)
        .or(detail_scale)
        .unwrap_or(1.0);
    let mut pixel_width = detail
        .get("max_width_px")
        .and_then(finite_json_number)
        .map(round_mysql_float_for_python_json);
    let stored_mm = detail
        .get("max_width_mm")
        .and_then(finite_json_number)
        .map(round_mysql_float_for_python_json);
    let width_unit = detail
        .get("max_width_unit")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_ascii_lowercase();

    let normalized_width = if width_unit == "px" {
        let pixels = pixel_width
            .filter(|value| *value > 0.0)
            .unwrap_or(raw_width);
        pixel_width = Some(pixels);
        pixels * width_scale
    } else if let Some(stored_mm) = stored_mm {
        if pixel_width.is_some_and(|pixels| pixels > 100.0 && (stored_mm - pixels).abs() < 0.001) {
            pixel_width.unwrap_or(raw_width) * width_scale
        } else {
            stored_mm
        }
    } else if raw_width > 100.0 && width_scale > 0.0 {
        pixel_width = Some(raw_width);
        raw_width * width_scale
    } else {
        raw_width
    };

    let normalized_width = round_mysql_float_for_python_json(normalized_width);

    detail.insert("max_width_raw".to_string(), json!(raw_width));
    detail.insert("max_width_mm".to_string(), json!(normalized_width));
    detail.insert("max_width_unit".to_string(), json!("mm"));
    detail.insert("max_width_scale".to_string(), json!(width_scale));
    detail.insert("max_width_scale_axis".to_string(), json!("x"));
    if let Some(pixel_width) = pixel_width {
        detail.insert("max_width_px".to_string(), json!(pixel_width));
    }
    fields.insert("max_width".to_string(), json!(normalized_width));
    fields.insert(
        "data".to_string(),
        Value::String(python_json_dumps_object(&detail)),
    );
    alarm
}

fn python_json_dumps_object(object: &Map<String, Value>) -> String {
    let fields = object
        .iter()
        .map(|(key, value)| {
            let key_json = serde_json::to_string(key).unwrap_or_else(|_| "\"\"".to_string());
            let value_json = serde_json::to_string(value).unwrap_or_else(|_| "null".to_string());
            format!("{key_json}: {value_json}")
        })
        .collect::<Vec<_>>()
        .join(", ");
    format!("{{{fields}}}")
}

fn finite_json_number(value: &Value) -> Option<f64> {
    value.as_f64().filter(|number| number.is_finite())
}

fn positive_json_number(value: &Value) -> Option<f64> {
    finite_json_number(value).filter(|number| *number > 0.0)
}

fn positive_f64(value: Option<f64>) -> Option<f64> {
    value.filter(|number| number.is_finite() && *number > 0.0)
}

async fn coil_alarm_get_info() -> Json<Value> {
    Json(Value::Null)
}

fn apply_detail_alarm_infos(body: &mut Value, alarm_infos: &[AlarmInfoSummaryRow]) {
    if alarm_infos.is_empty() {
        return;
    }
    let Value::Object(fields) = body else {
        return;
    };

    let mut alarm_info = Map::new();
    let mut children_alarm_info = Vec::new();
    let mut latest_next_code: Option<&str> = None;
    let mut latest_next_name: Option<&str> = None;
    for row in alarm_infos {
        alarm_info.insert(row.surface.clone(), alarm_info_to_python_json(row));
        children_alarm_info.push(detail_alarm_info_to_python_json(row));
        if let Some(next_code) = row.next_code.as_deref().filter(|value| !value.is_empty()) {
            latest_next_code = Some(next_code);
            latest_next_name = row.next_name.as_deref();
        }
    }

    fields.insert("hasAlarmInfo".to_string(), json!(true));
    fields.insert("AlarmInfo".to_string(), Value::Object(alarm_info));
    fields.insert(
        "childrenAlarmInfo".to_string(),
        Value::Array(children_alarm_info),
    );
    if let Some(next_code) = latest_next_code {
        fields.insert("NextCode".to_string(), json!(next_code));
        fields.insert(
            "NextInfo".to_string(),
            json!(latest_next_name.unwrap_or("")),
        );
    }
}

fn max_defect_json_fields(defects: &[CoilDefectRow]) -> MaxDefectJsonFields {
    let (config, default_show) = detail_defect_class_config();
    let mut max_defect: Option<&CoilDefectRow> = None;
    let mut max_level = -1;

    for defect in defects {
        let (level, is_shown) = config
            .get(&defect.defect_name)
            .copied()
            .unwrap_or((1, default_show));
        if is_shown && level > max_level {
            max_level = level;
            max_defect = Some(defect);
        }
    }

    let Some(defect) = max_defect else {
        return MaxDefectJsonFields::default();
    };

    MaxDefectJsonFields {
        name: defect.defect_name.clone(),
        level: max_level.max(0),
        surface: if defect.surface.trim().is_empty() {
            "S".to_string()
        } else {
            defect.surface.clone()
        },
    }
}

fn detail_defect_class_config() -> (HashMap<String, (i32, bool)>, bool) {
    let config = read_json_value(&defect_classes_config_path()).unwrap_or_else(default_defect_dict);
    let default_show = config
        .get("default")
        .and_then(|default| default.get("show"))
        .map(python_truthy_json)
        .unwrap_or(true);

    let mut lookup = HashMap::new();
    let Some(data) = config.get("data").and_then(Value::as_object) else {
        return (lookup, default_show);
    };

    for (name, fields) in data {
        let level = fields.get("level").and_then(python_int_json).unwrap_or(1);
        let show = fields
            .get("show")
            .map(python_truthy_json)
            .unwrap_or(default_show);
        lookup.insert(name.clone(), (level, show));
    }
    if let Some(name_map) = config.get("name_map").and_then(Value::as_object) {
        for (alias, target) in name_map {
            let Some(target_name) = target.as_str() else {
                continue;
            };
            if let Some(settings) = lookup.get(target_name).copied() {
                lookup.insert(alias.clone(), settings);
            }
        }
    }

    (lookup, default_show)
}

fn python_int_json(value: &Value) -> Option<i32> {
    match value {
        Value::Number(number) => number.as_i64().and_then(|item| i32::try_from(item).ok()),
        Value::String(text) => text.trim().parse::<i32>().ok(),
        Value::Bool(value) => Some(i32::from(*value)),
        _ => None,
    }
}

fn python_truthy_json(value: &Value) -> bool {
    match value {
        Value::Bool(value) => *value,
        Value::Null => false,
        Value::Number(number) => number.as_i64().map(|item| item != 0).unwrap_or(true),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(fields) => !fields.is_empty(),
    }
}

fn reorder_detail_root_fields(body: &mut Value) {
    let Value::Object(fields) = body else {
        return;
    };

    let mut remaining = std::mem::take(fields);
    let mut ordered = Map::new();
    for key in PYTHON_DETAIL_ROOT_KEYS {
        if let Some(value) = remaining.remove(*key) {
            ordered.insert((*key).to_string(), value);
        }
    }
    for (key, value) in remaining {
        ordered.insert(key, value);
    }
    *fields = ordered;
}

fn apply_coil_detail_fields(
    body: &mut Value,
    coil_id: i64,
    defect_values: Vec<Value>,
    taper_shape_point_values: Vec<Value>,
    alarm_taper_values: Vec<Value>,
    alarm_loose_values: Vec<Value>,
    alarm_flat_values: Vec<Value>,
    coil_check_values: Vec<Value>,
    defect_alias_values: Vec<Value>,
    max_defect_fields: MaxDefectJsonFields,
) {
    if let Value::Object(fields) = body {
        fields.insert("SecondaryCoilId".to_string(), json!(coil_id));
        fields.insert(
            "childrenCoilDefect".to_string(),
            Value::Array(defect_values),
        );
        fields.insert("defects".to_string(), Value::Array(defect_alias_values));
        fields.insert(
            "childrenTaperShapePoint".to_string(),
            Value::Array(taper_shape_point_values),
        );
        fields.insert(
            "childrenAlarmTaperShape".to_string(),
            Value::Array(alarm_taper_values),
        );
        fields.insert(
            "childrenAlarmLooseCoil".to_string(),
            Value::Array(alarm_loose_values),
        );
        fields.insert(
            "childrenAlarmFlatRoll".to_string(),
            Value::Array(alarm_flat_values),
        );
        fields.insert(
            "childrenCoilCheck".to_string(),
            Value::Array(coil_check_values),
        );
        fields.insert("maxDefectName".to_string(), json!(max_defect_fields.name));
        fields.insert("maxDefectLevel".to_string(), json!(max_defect_fields.level));
        fields.insert(
            "maxDefectSurface".to_string(),
            json!(max_defect_fields.surface),
        );
    }
}

async fn search_defects(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.defects(coil_id, &surface).await?;
    Ok(Json(Value::Array(
        rows.iter().map(defect_to_python_json).collect(),
    ))
    .into_response())
}

async fn search_defect_all(
    State(state): State<ApiState>,
    Path((start_coil_id, end_coil_id)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let start_coil_id = match parse_python_int_converter_path(&start_coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let end_coil_id = match parse_python_int_converter_path(&end_coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state
        .repository
        .defects_between(start_coil_id, end_coil_id)
        .await?;
    Ok(Json(Value::Array(
        rows.iter().map(defect_to_python_json).collect(),
    ))
    .into_response())
}

async fn manual_defects(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.manual_defects(coil_id, &surface).await?;
    Ok(Json(Value::Array(
        rows.iter().map(manual_defect_to_python_json).collect(),
    ))
    .into_response())
}

async fn search_defects_all(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let auto_rows = state.repository.defects(coil_id, &surface).await?;
    let manual_rows = state.repository.manual_defects(coil_id, &surface).await?;
    let body = auto_rows
        .iter()
        .map(auto_defect_to_python_json)
        .chain(manual_rows.iter().map(manual_defect_to_python_json))
        .collect();
    Ok(Json(Value::Array(body)).into_response())
}

async fn add_manual_defect(
    State(state): State<ApiState>,
    Json(payload): Json<ManualDefectPayload>,
) -> Json<Value> {
    if let Err(error) = payload.validate_add() {
        return Json(manual_defect_error(error));
    }

    match state
        .repository
        .add_manual_defect(payload.into_write())
        .await
    {
        Ok(row) => Json(manual_defect_to_python_json(
            &sync_manual_defect_assets(&state, row).await,
        )),
        Err(error) => Json(manual_defect_error(error.to_string())),
    }
}

async fn update_manual_defect(
    State(state): State<ApiState>,
    Path(defect_id): Path<String>,
    Json(payload): Json<ManualDefectPayload>,
) -> Response {
    let defect_id = match parse_python_int_converter_path(&defect_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    match state
        .repository
        .update_manual_defect(defect_id, payload.into_write())
        .await
    {
        Ok(Some(row)) => Json(manual_defect_to_python_json(
            &sync_manual_defect_assets(&state, row).await,
        ))
        .into_response(),
        Ok(None) => Json(manual_defect_error("缺陷不存在")).into_response(),
        Err(error) => Json(manual_defect_error(error.to_string())).into_response(),
    }
}

async fn delete_manual_defect(
    State(state): State<ApiState>,
    Path(defect_id): Path<String>,
) -> Response {
    let defect_id = match parse_python_int_converter_path(&defect_id) {
        Ok(value) => value,
        Err(response) => return response,
    };
    match state.repository.delete_manual_defect(defect_id).await {
        Ok(true) => Json(json!({"success": true, "message": "删除成功"})).into_response(),
        Ok(false) => Json(manual_defect_error("缺陷不存在")).into_response(),
        Err(error) => Json(manual_defect_error(error.to_string())).into_response(),
    }
}

async fn export_defects(
    State(state): State<ApiState>,
    Json(request): Json<ExportDefectsRequest>,
) -> Json<Value> {
    Json(export_defects_value(&state, request))
}

async fn export_xlsx_by_id(
    State(state): State<ApiState>,
    Path((start, end)): Path<(String, String)>,
    Query(query): Query<ExportXlsxQuery>,
) -> Response {
    let start = match parse_python_int_converter_path(&start) {
        Ok(start) => start,
        Err(response) => return response,
    };
    let end = match parse_python_int_converter_path(&end) {
        Ok(end) => end,
        Err(response) => return response,
    };
    match state.repository.search_coils_by_id_range(start, end).await {
        Ok(rows) => {
            let title = format!(
                "By Coil Id ({})",
                query.export_type.as_deref().unwrap_or("3D")
            );
            xlsx_response_for_rows(
                &state,
                &title,
                &start.to_string(),
                &end.to_string(),
                &rows,
                "example.xlsx",
                false,
                true,
                true,
                false,
                true,
            )
            .await
        }
        Err(_) => export_xlsx_error_response(),
    }
}

async fn export_xlsx_by_datetime(
    State(state): State<ApiState>,
    Path((start, end)): Path<(String, String)>,
    Query(query): Query<ExportXlsxQuery>,
) -> Response {
    if !is_python_datetime_path(&start) || !is_python_datetime_path(&end) {
        return export_xlsx_error_response();
    }

    match state
        .repository
        .search_coils_by_datetime_for_export(&start, &end)
        .await
    {
        Ok(rows) => {
            let title = format!(
                "By Date Time ({})",
                query.export_type.as_deref().unwrap_or("3D")
            );
            xlsx_response_for_rows(
                &state,
                &title,
                &start,
                &end,
                &rows,
                "example.xlsx",
                false,
                true,
                true,
                false,
                true,
            )
            .await
        }
        Err(_) => export_xlsx_error_response(),
    }
}

async fn export_xlsx_post(
    State(state): State<ApiState>,
    Json(request): Json<ExportXlsxConfigRequest>,
) -> Response {
    if !is_python_datetime_path(&request.start_date) || !is_python_datetime_path(&request.end_date)
    {
        return export_xlsx_error_response();
    }

    let title = format!(
        "Configured {} detection_3d={} defect={} show={} unshow={} area_image={} plc={}",
        request.export_type,
        request.detection_3d_info,
        request.defect_info,
        request.defect_show_info,
        request.defect_un_show_info,
        request.area_defect_image.unwrap_or(true),
        request.export_plc_data
    );
    match state
        .repository
        .search_coils_by_datetime_for_export(&request.start_date, &request.end_date)
        .await
    {
        Ok(rows) => {
            xlsx_response_for_rows(
                &state,
                &title,
                &request.start_date,
                &request.end_date,
                &rows,
                "example.xlsx",
                request.export_plc_data,
                request.defect_info,
                request.defect_show_info,
                request.defect_un_show_info,
                request.area_defect_image.unwrap_or(true),
            )
            .await
        }
        Err(_) => export_xlsx_error_response(),
    }
}

async fn export_data_simple(State(state): State<ApiState>) -> Response {
    match state.repository.search_coils_recent_for_export(50).await {
        Ok(rows) => {
            xlsx_response_for_rows(
                &state,
                "Simple Export",
                "",
                "",
                &rows,
                "exportDataSimple.xlsx",
                false,
                true,
                true,
                false,
                true,
            )
            .await
        }
        Err(_) => export_xlsx_error_response(),
    }
}

async fn export_last_1h(State(state): State<ApiState>) -> Response {
    quick_xlsx_export(
        state,
        QuickXlsxExportKind::LastHours {
            hours: 1,
            filename_prefix: "export_1h",
        },
    )
    .await
}

async fn export_last_24h(State(state): State<ApiState>) -> Response {
    quick_xlsx_export(
        state,
        QuickXlsxExportKind::LastHours {
            hours: 24,
            filename_prefix: "export_24h",
        },
    )
    .await
}

async fn export_today(State(state): State<ApiState>) -> Response {
    quick_xlsx_export(
        state,
        QuickXlsxExportKind::Today {
            filename_prefix: "export_today",
        },
    )
    .await
}

#[derive(Clone, Copy)]
enum QuickXlsxExportKind {
    LastHours {
        hours: i64,
        filename_prefix: &'static str,
    },
    Today {
        filename_prefix: &'static str,
    },
}

impl QuickXlsxExportKind {
    fn filename_prefix(self) -> &'static str {
        match self {
            QuickXlsxExportKind::LastHours {
                filename_prefix, ..
            } => filename_prefix,
            QuickXlsxExportKind::Today { filename_prefix } => filename_prefix,
        }
    }

    fn title(self) -> &'static str {
        match self {
            QuickXlsxExportKind::LastHours { hours: 1, .. } => "Last 1 Hour",
            QuickXlsxExportKind::LastHours { hours: 24, .. } => "Last 24 Hours",
            QuickXlsxExportKind::LastHours { .. } => "Last Hours",
            QuickXlsxExportKind::Today { .. } => "Today",
        }
    }
}

async fn quick_xlsx_export(state: ApiState, kind: QuickXlsxExportKind) -> Response {
    let end_time = Local::now();
    let start_time = match kind {
        QuickXlsxExportKind::LastHours { hours, .. } => end_time - chrono::Duration::hours(hours),
        QuickXlsxExportKind::Today { .. } => end_time
            .with_hour(0)
            .and_then(|value| value.with_minute(0))
            .and_then(|value| value.with_second(0))
            .and_then(|value| value.with_nanosecond(0))
            .unwrap_or(end_time),
    };

    let start_query = start_time.format("%Y%m%d%H%M").to_string();
    let end_query = end_time.format("%Y%m%d%H%M").to_string();
    let filename = match kind {
        QuickXlsxExportKind::Today { .. } => {
            format!(
                "{}_{}.xlsx",
                kind.filename_prefix(),
                start_time.format("%Y%m%d")
            )
        }
        QuickXlsxExportKind::LastHours { .. } => {
            format!(
                "{}_{}.xlsx",
                kind.filename_prefix(),
                start_time.format("%Y%m%d_%H%M")
            )
        }
    };

    match state
        .repository
        .search_coils_by_datetime_for_export(&start_query, &end_query)
        .await
    {
        Ok(rows) => {
            xlsx_response_for_rows(
                &state,
                kind.title(),
                &start_query,
                &end_query,
                &rows,
                &filename,
                false,
                true,
                true,
                false,
                true,
            )
            .await
        }
        Err(_) => export_xlsx_error_response(),
    }
}

fn export_xlsx_error_response() -> Response {
    (StatusCode::INTERNAL_SERVER_ERROR, "export xlsx failed").into_response()
}

async fn xlsx_response_for_rows(
    state: &ApiState,
    title: &str,
    start_query: &str,
    end_query: &str,
    rows: &[CoilSummaryRow],
    filename: &str,
    export_plc_data: bool,
    export_defect_data: bool,
    export_defect_show_sheet: bool,
    export_defect_un_show_sheet: bool,
    export_area_defect_sheet: bool,
) -> Response {
    let defects = match export_xlsx_defects_for_rows(state, rows).await {
        Ok(defects) => defects,
        Err(_) => return export_xlsx_error_response(),
    };
    let plc_rows = match export_xlsx_plc_for_rows(state, rows, export_plc_data).await {
        Ok(plc_rows) => plc_rows,
        Err(_) => return export_xlsx_error_response(),
    };
    let alarm_rows = match export_xlsx_alarm_rows(state, rows).await {
        Ok(alarm_rows) => alarm_rows,
        Err(_) => return export_xlsx_error_response(),
    };
    match build_quick_xlsx_bytes(
        title,
        start_query,
        end_query,
        rows,
        &defects,
        &plc_rows,
        &alarm_rows,
        export_plc_data,
        export_defect_data,
        export_defect_show_sheet,
        export_defect_un_show_sheet,
        export_area_defect_sheet,
    ) {
        Ok(bytes) => xlsx_response(bytes, filename),
        Err(_) => export_xlsx_error_response(),
    }
}

async fn export_xlsx_defects_for_rows(
    state: &ApiState,
    rows: &[CoilSummaryRow],
) -> anyhow::Result<Vec<CoilDefectRow>> {
    let Some(min_id) = rows.iter().map(|row| row.id).min() else {
        return Ok(Vec::new());
    };
    let Some(max_id) = rows.iter().map(|row| row.id).max() else {
        return Ok(Vec::new());
    };
    let row_ids: HashSet<i64> = rows.iter().map(|row| row.id).collect();
    let defects = state.repository.defects_between(min_id, max_id).await?;
    Ok(defects
        .into_iter()
        .filter(|defect| row_ids.contains(&defect.secondary_coil_id))
        .collect())
}

async fn export_xlsx_plc_for_rows(
    state: &ApiState,
    rows: &[CoilSummaryRow],
    export_plc_data: bool,
) -> anyhow::Result<HashMap<i64, PlcDataRow>> {
    if !export_plc_data {
        return Ok(HashMap::new());
    }

    let mut plc_rows = HashMap::new();
    for row in rows {
        if let Some(plc_row) = state.repository.plc_data(row.id).await? {
            plc_rows.insert(row.id, plc_row);
        }
    }
    Ok(plc_rows)
}

#[derive(Default)]
struct XlsxAlarmExportRows {
    flat_rolls: HashMap<i64, Vec<AlarmFlatRollRow>>,
    taper_shapes: HashMap<i64, Vec<AlarmTaperShapeRow>>,
    loose_coils: HashMap<i64, Vec<AlarmLooseCoilRow>>,
    alarm_infos: HashMap<i64, Vec<AlarmInfoSummaryRow>>,
}

async fn export_xlsx_alarm_rows(
    state: &ApiState,
    rows: &[CoilSummaryRow],
) -> anyhow::Result<XlsxAlarmExportRows> {
    let mut result = XlsxAlarmExportRows::default();
    for row in rows {
        let flat_rolls = state.repository.alarm_flat_rolls(row.id).await?;
        if !flat_rolls.is_empty() {
            result.flat_rolls.insert(row.id, flat_rolls);
        }

        let taper_shapes = state.repository.alarm_taper_shapes(row.id).await?;
        if !taper_shapes.is_empty() {
            result.taper_shapes.insert(row.id, taper_shapes);
        }

        let loose_coils = state.repository.alarm_loose_coils(row.id).await?;
        if !loose_coils.is_empty() {
            result.loose_coils.insert(row.id, loose_coils);
        }

        let alarm_infos = state.repository.alarm_infos(row.id).await?;
        if !alarm_infos.is_empty() {
            result.alarm_infos.insert(row.id, alarm_infos);
        }
    }
    Ok(result)
}

fn xlsx_response(bytes: Vec<u8>, filename: &str) -> Response {
    let length = bytes.len();
    let mut response = Response::new(axum::body::Body::from(bytes));
    let headers = response.headers_mut();
    headers.insert(
        header::CONTENT_TYPE,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            .parse()
            .expect("xlsx content type"),
    );
    headers.insert(
        header::CONTENT_DISPOSITION,
        format!("attachment; filename={filename}")
            .parse()
            .expect("content disposition"),
    );
    headers.insert(
        header::CONTENT_LENGTH,
        length.to_string().parse().expect("content length"),
    );
    response
}

fn build_quick_xlsx_bytes(
    _title: &str,
    _start_query: &str,
    _end_query: &str,
    coils: &[CoilSummaryRow],
    defects: &[CoilDefectRow],
    plc_rows: &HashMap<i64, PlcDataRow>,
    alarm_rows: &XlsxAlarmExportRows,
    export_plc_data: bool,
    export_defect_data: bool,
    export_defect_show_sheet: bool,
    export_defect_un_show_sheet: bool,
    export_area_defect_sheet: bool,
) -> Result<Vec<u8>, String> {
    let defects_by_coil = export_defects_by_coil(defects);
    let (defect_class_config, default_defect_show) = detail_defect_class_config();
    let (alarm_headers, alarm_values_by_coil) = export_xlsx_alarm_table(coils, alarm_rows);
    let mut header_row = vec![
        "流水号".to_string(),
        "卷号".to_string(),
        "钢种".to_string(),
        "去向".to_string(),
        "二级外径".to_string(),
        "二级厚度".to_string(),
        "二级宽度".to_string(),
        "二级数据接受时间".to_string(),
    ];
    if export_plc_data {
        header_row.extend([
            "激光距离".to_string(),
            "S端移动位置".to_string(),
            "L端移动位置".to_string(),
        ]);
    }
    header_row.extend(alarm_headers.iter().cloned());
    if export_defect_data {
        header_row.extend([
            "S端 缺陷数".to_string(),
            "L端 缺陷数量".to_string(),
            "边裂".to_string(),
            "边裂_报警".to_string(),
            "刮丝".to_string(),
            "刮丝_报警".to_string(),
            "边部褶皱".to_string(),
            "边部褶皱_报警".to_string(),
            "折叠".to_string(),
            "折叠_报警".to_string(),
            "分层".to_string(),
            "分层_报警".to_string(),
            "综合报警等级".to_string(),
            "最大缺陷".to_string(),
            "最大缺陷面".to_string(),
        ]);
    }
    let mut rows = vec![header_row];

    for coil in coils {
        let mut row = vec![
            coil.id.to_string(),
            coil.coil_no.clone(),
            coil.coil_type.clone().unwrap_or_default(),
            coil.next_info
                .clone()
                .or_else(|| coil.next_code.clone())
                .unwrap_or_default(),
            option_f64_to_string(coil.coil_dia),
            option_f64_to_string(coil.thickness),
            option_f64_to_string(coil.width),
            coil.create_time.clone().unwrap_or_default(),
        ];
        if export_plc_data {
            let plc_row = plc_rows.get(&coil.id);
            row.extend([
                option_f64_to_string(plc_row.and_then(|plc| plc.location_laser)),
                option_f64_to_string(plc_row.and_then(|plc| plc.location_l)),
                option_f64_to_string(plc_row.and_then(|plc| plc.location_s)),
            ]);
        }
        append_xlsx_dynamic_values(&mut row, &alarm_headers, alarm_values_by_coil.get(&coil.id));
        if export_defect_data {
            row.extend([
                coil.defect_count_s.to_string(),
                coil.defect_count_l.to_string(),
                export_defect_category_count(coil.id, &defects_by_coil, &["烂边"]).to_string(),
                export_defect_category_alarm(coil.id, &defects_by_coil, &["烂边"]).to_string(),
                export_defect_category_count(coil.id, &defects_by_coil, &["刮丝"]).to_string(),
                export_defect_category_alarm(coil.id, &defects_by_coil, &["刮丝"]).to_string(),
                export_defect_category_count(coil.id, &defects_by_coil, &["边部褶皱"]).to_string(),
                export_defect_category_alarm(coil.id, &defects_by_coil, &["边部褶皱"]).to_string(),
                export_defect_category_count(coil.id, &defects_by_coil, &["折叠"]).to_string(),
                export_defect_category_alarm(coil.id, &defects_by_coil, &["折叠"]).to_string(),
                export_defect_category_count(coil.id, &defects_by_coil, &["分层"]).to_string(),
                export_defect_category_alarm(coil.id, &defects_by_coil, &["分层"]).to_string(),
                coil.grade.to_string(),
                coil.max_defect_name.clone().unwrap_or_default(),
                coil.max_defect_surface.clone().unwrap_or_default(),
            ]);
        }
        rows.push(row);
    }

    let mut worksheets = vec![XlsxWorksheet {
        name: "数据报表".to_string(),
        rows,
    }];
    if export_defect_show_sheet {
        worksheets.push(XlsxWorksheet {
            name: "缺陷识别_3D".to_string(),
            rows: defect_xlsx_rows(
                coils,
                &defects_by_coil,
                false,
                Some(true),
                &defect_class_config,
                default_defect_show,
            ),
        });
    }
    if export_defect_un_show_sheet {
        worksheets.push(XlsxWorksheet {
            name: "缺陷识别_3D_屏蔽".to_string(),
            rows: defect_xlsx_rows(
                coils,
                &defects_by_coil,
                false,
                Some(false),
                &defect_class_config,
                default_defect_show,
            ),
        });
    }
    if export_area_defect_sheet {
        worksheets.push(XlsxWorksheet {
            name: "缺陷识别_2D".to_string(),
            rows: defect_xlsx_rows(
                coils,
                &defects_by_coil,
                true,
                None,
                &defect_class_config,
                default_defect_show,
            ),
        });
    }

    let mut zip = ZipWriter::new(Cursor::new(Vec::new()));
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    zip.start_file("[Content_Types].xml", options)
        .map_err(|error| error.to_string())?;
    zip.write_all(xlsx_content_types_xml(worksheets.len()).as_bytes())
        .map_err(|error| error.to_string())?;
    zip.add_directory("_rels/", options)
        .map_err(|error| error.to_string())?;
    zip.start_file("_rels/.rels", options)
        .map_err(|error| error.to_string())?;
    zip.write_all(ROOT_RELS_XML.as_bytes())
        .map_err(|error| error.to_string())?;
    zip.add_directory("xl/", options)
        .map_err(|error| error.to_string())?;
    zip.start_file("xl/workbook.xml", options)
        .map_err(|error| error.to_string())?;
    zip.write_all(xlsx_workbook_xml(&worksheets).as_bytes())
        .map_err(|error| error.to_string())?;
    zip.add_directory("xl/_rels/", options)
        .map_err(|error| error.to_string())?;
    zip.start_file("xl/_rels/workbook.xml.rels", options)
        .map_err(|error| error.to_string())?;
    zip.write_all(xlsx_workbook_rels_xml(worksheets.len()).as_bytes())
        .map_err(|error| error.to_string())?;
    zip.add_directory("xl/worksheets/", options)
        .map_err(|error| error.to_string())?;
    for (index, worksheet) in worksheets.iter().enumerate() {
        zip.start_file(format!("xl/worksheets/sheet{}.xml", index + 1), options)
            .map_err(|error| error.to_string())?;
        zip.write_all(worksheet_xml(&worksheet.rows).as_bytes())
            .map_err(|error| error.to_string())?;
    }
    let cursor = zip.finish().map_err(|error| error.to_string())?;
    Ok(cursor.into_inner())
}

struct XlsxWorksheet {
    name: String,
    rows: Vec<Vec<String>>,
}

fn export_xlsx_alarm_table(
    coils: &[CoilSummaryRow],
    alarm_rows: &XlsxAlarmExportRows,
) -> (Vec<String>, HashMap<i64, Vec<(String, String)>>) {
    let mut headers = Vec::new();
    let mut seen_headers = HashSet::new();
    let mut values_by_coil = HashMap::new();

    for coil in coils {
        let values = export_xlsx_alarm_values(coil.id, alarm_rows);
        for (header, _) in &values {
            if seen_headers.insert(header.clone()) {
                headers.push(header.clone());
            }
        }
        values_by_coil.insert(coil.id, values);
    }

    (headers, values_by_coil)
}

fn export_xlsx_alarm_values(
    coil_id: i64,
    alarm_rows: &XlsxAlarmExportRows,
) -> Vec<(String, String)> {
    let mut values = Vec::new();
    let alarm_info_by_surface = xlsx_alarm_info_by_surface(alarm_rows.alarm_infos.get(&coil_id));

    for surface in ["S", "L"] {
        if let Some(flat_roll) =
            first_flat_roll_by_surface(alarm_rows.flat_rolls.get(&coil_id), surface)
        {
            values.push((
                format!("{surface}端 检测外径"),
                option_f64_to_string(flat_roll.out_circle_width.map(|value| {
                    round_mysql_float_for_python_json(value * XLSX_FLAT_ROLL_PIXEL_SCALE)
                })),
            ));
            values.push((
                format!("{surface}端 检测内径"),
                option_f64_to_string(flat_roll.inner_circle_width.map(|value| {
                    round_mysql_float_for_python_json(value * XLSX_FLAT_ROLL_PIXEL_SCALE)
                })),
            ));
            if let Some(alarm_info) = alarm_info_by_surface.get(surface) {
                values.push((
                    format!("{surface}端 扁卷报警等级"),
                    alarm_info.flat_roll_grad.to_string(),
                ));
                values.push((
                    format!("{surface}端 扁卷报警信息"),
                    alarm_info.flat_roll_msg.clone().unwrap_or_default(),
                ));
            }
        }
    }

    for surface in ["S", "L"] {
        if let Some(taper_shape) =
            select_xlsx_taper_shape(alarm_rows.taper_shapes.get(&coil_id), surface)
        {
            values.push((
                format!("{surface}端 检测角度"),
                option_f64_to_string(taper_shape.rotation_angle),
            ));
            values.push((
                format!("{surface}端 外圈最大值"),
                option_f64_to_string(taper_shape.out_taper_max_value),
            ));
            values.push((
                format!("{surface}端 外圈最小值"),
                option_f64_to_string(taper_shape.out_taper_min_value),
            ));
            values.push((
                format!("{surface}端 内圈最大值"),
                option_f64_to_string(taper_shape.in_taper_max_value),
            ));
            values.push((
                format!("{surface}端 内圈最小值"),
                option_f64_to_string(taper_shape.in_taper_min_value),
            ));
            append_xlsx_taper_detail_values(&mut values, surface, taper_shape);
        }
        if let Some(alarm_info) = alarm_info_by_surface.get(surface) {
            values.push((
                format!("{surface}端 塔形报警等级"),
                alarm_info.taper_shape_grad.to_string(),
            ));
            values.push((
                format!("{surface}端 塔形报警信息"),
                alarm_info.taper_shape_msg.clone().unwrap_or_default(),
            ));
        }
    }

    for surface in ["S", "L"] {
        if let Some(loose_coil) =
            first_loose_coil_by_surface(alarm_rows.loose_coils.get(&coil_id), surface)
        {
            values.push((
                format!("{surface}端 松卷检测角度"),
                option_f64_to_string(loose_coil.rotation_angle),
            ));
            values.push((
                format!("{surface}端 松卷检测最宽"),
                option_f64_to_string(loose_coil.max_width),
            ));
            if let Some(alarm_info) = alarm_info_by_surface.get(surface) {
                values.push((
                    format!("{surface}端 松卷报警等级"),
                    alarm_info.loose_coil_grad.to_string(),
                ));
                values.push((
                    format!("{surface}端 松卷报警信息"),
                    alarm_info.loose_coil_msg.clone().unwrap_or_default(),
                ));
            }
        }
    }

    values
}

fn xlsx_alarm_info_by_surface<'a>(
    alarm_infos: Option<&'a Vec<AlarmInfoSummaryRow>>,
) -> HashMap<&'a str, &'a AlarmInfoSummaryRow> {
    let mut by_surface = HashMap::new();
    if let Some(alarm_infos) = alarm_infos {
        for alarm_info in alarm_infos {
            if alarm_info.surface == "S" || alarm_info.surface == "L" {
                by_surface.insert(alarm_info.surface.as_str(), alarm_info);
            }
        }
    }
    by_surface
}

fn first_flat_roll_by_surface<'a>(
    rows: Option<&'a Vec<AlarmFlatRollRow>>,
    surface: &str,
) -> Option<&'a AlarmFlatRollRow> {
    rows.and_then(|rows| rows.iter().find(|row| row.surface == surface))
}

fn first_loose_coil_by_surface<'a>(
    rows: Option<&'a Vec<AlarmLooseCoilRow>>,
    surface: &str,
) -> Option<&'a AlarmLooseCoilRow> {
    rows.and_then(|rows| rows.iter().find(|row| row.surface == surface))
}

fn select_xlsx_taper_shape<'a>(
    rows: Option<&'a Vec<AlarmTaperShapeRow>>,
    surface: &str,
) -> Option<&'a AlarmTaperShapeRow> {
    rows.and_then(|rows| {
        rows.iter()
            .filter(|row| row.surface == surface)
            .max_by(|left, right| {
                xlsx_taper_severity(left)
                    .partial_cmp(&xlsx_taper_severity(right))
                    .unwrap_or(Ordering::Equal)
            })
    })
}

fn xlsx_taper_severity(row: &AlarmTaperShapeRow) -> (f64, f64, f64) {
    let detail = xlsx_taper_detail_object(row);
    let worst_abs = detail
        .as_ref()
        .and_then(|data| data.get("worst_abs_mm"))
        .and_then(finite_json_number)
        .map(f64::abs)
        .unwrap_or(0.0);
    let value_abs = [
        row.out_taper_max_value,
        row.out_taper_min_value,
        row.in_taper_max_value,
        row.in_taper_min_value,
    ]
    .into_iter()
    .flatten()
    .filter(|value| value.is_finite())
    .map(f64::abs)
    .fold(0.0, f64::max);
    (
        f64::from(row.level.unwrap_or(0)).abs(),
        worst_abs,
        value_abs,
    )
}

fn append_xlsx_taper_detail_values(
    values: &mut Vec<(String, String)>,
    surface: &str,
    taper_shape: &AlarmTaperShapeRow,
) {
    let Some(detail) = xlsx_taper_detail_object(taper_shape) else {
        return;
    };
    if detail.is_empty() {
        return;
    }

    for (header, key) in [
        ("塔形最严重类型", "worst_label"),
        ("塔形最严重值", "worst_mm"),
        ("塔形最严重绝对值", "worst_abs_mm"),
        ("塔形最严重点类型", "worst_point_type"),
        ("塔形最严重点X", "worst_x"),
        ("塔形最严重点Y", "worst_y"),
        ("塔形最严重点Z", "worst_z"),
        ("塔形最严重角度", "worst_angle"),
    ] {
        let value = detail
            .get(key)
            .map(xlsx_json_value_to_string)
            .unwrap_or_else(|| {
                if key == "worst_angle" {
                    option_f64_to_string(taper_shape.rotation_angle)
                } else {
                    String::new()
                }
            });
        values.push((format!("{surface}端 {header}"), value));
    }

    values.push((
        format!("{surface}端 塔形判定角度"),
        detail
            .get("angle_filter")
            .map(xlsx_taper_angle_filter_to_string)
            .unwrap_or_default(),
    ));

    for (header, key) in [
        ("塔形角度容差", "angle_tolerance"),
        ("塔形有效角度覆盖率", "valid_angle_coverage_ratio"),
        ("塔形有效线数量", "valid_line_count"),
        ("塔形覆盖角度数量", "covered_angle_count"),
        ("塔形检测角度数量", "taper_attempt_count"),
        ("塔形原始检测角度数量", "raw_taper_attempt_count"),
        ("塔形检测失败数量", "detection_error_count"),
        ("塔形原始检测失败数量", "raw_detection_error_count"),
        ("塔形配置警告数量", "warning_count"),
        ("塔形分级无效线数量", "grading_error_count"),
    ] {
        values.push((
            format!("{surface}端 {header}"),
            detail
                .get(key)
                .map(xlsx_json_value_to_string)
                .unwrap_or_default(),
        ));
    }
}

fn xlsx_taper_detail_object(row: &AlarmTaperShapeRow) -> Option<Map<String, Value>> {
    row.data
        .as_deref()
        .filter(|value| !value.trim().is_empty())
        .and_then(|value| serde_json::from_str::<Value>(value).ok())
        .and_then(|value| value.as_object().cloned())
}

fn xlsx_taper_angle_filter_to_string(value: &Value) -> String {
    match value {
        Value::Array(items) => items
            .iter()
            .map(xlsx_taper_angle_filter_item_to_string)
            .collect::<Vec<_>>()
            .join(", "),
        _ => xlsx_json_value_to_string(value),
    }
}

fn xlsx_taper_angle_filter_item_to_string(value: &Value) -> String {
    match value {
        Value::Null => "None".to_string(),
        Value::Bool(value) => {
            if *value {
                "1".to_string()
            } else {
                "0".to_string()
            }
        }
        Value::Number(number) => number
            .as_f64()
            .filter(|value| value.is_finite())
            .map(|value| option_f64_to_string(Some(value)))
            .unwrap_or_else(|| number.to_string()),
        Value::String(value) => value
            .parse::<f64>()
            .ok()
            .filter(|value| value.is_finite())
            .map(|value| option_f64_to_string(Some(value)))
            .unwrap_or_else(|| value.clone()),
        Value::Array(_) | Value::Object(_) => xlsx_json_value_to_string(value),
    }
}

fn xlsx_json_value_to_string(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(value) => value.clone(),
        Value::Number(number) => number.to_string(),
        Value::Bool(value) => value.to_string(),
        Value::Array(_) | Value::Object(_) => serde_json::to_string(value).unwrap_or_default(),
    }
}

fn append_xlsx_dynamic_values(
    row: &mut Vec<String>,
    headers: &[String],
    values: Option<&Vec<(String, String)>>,
) {
    for header in headers {
        let value = values
            .and_then(|values| {
                values
                    .iter()
                    .find(|(value_header, _)| value_header == header)
            })
            .map(|(_, value)| value.clone())
            .unwrap_or_default();
        row.push(value);
    }
}

fn export_defects_by_coil(defects: &[CoilDefectRow]) -> HashMap<i64, Vec<&CoilDefectRow>> {
    let mut grouped: HashMap<i64, Vec<&CoilDefectRow>> = HashMap::new();
    for defect in defects {
        grouped
            .entry(defect.secondary_coil_id)
            .or_default()
            .push(defect);
    }
    grouped
}

fn export_defect_category_count(
    coil_id: i64,
    defects_by_coil: &HashMap<i64, Vec<&CoilDefectRow>>,
    names: &[&str],
) -> usize {
    defects_by_coil
        .get(&coil_id)
        .map(|defects| {
            defects
                .iter()
                .filter(|defect| names.iter().any(|name| defect.defect_name.trim() == *name))
                .count()
        })
        .unwrap_or(0)
}

fn export_defect_category_alarm(
    coil_id: i64,
    defects_by_coil: &HashMap<i64, Vec<&CoilDefectRow>>,
    names: &[&str],
) -> &'static str {
    if export_defect_category_count(coil_id, defects_by_coil, names) > 0 {
        "是"
    } else {
        "否"
    }
}

fn defect_xlsx_rows(
    coils: &[CoilSummaryRow],
    defects_by_coil: &HashMap<i64, Vec<&CoilDefectRow>>,
    area_2d: bool,
    defect_show_filter: Option<bool>,
    defect_class_config: &HashMap<String, (i32, bool)>,
    default_defect_show: bool,
) -> Vec<Vec<String>> {
    let mut rows = vec![vec![
        "流水号".to_string(),
        "卷号".to_string(),
        "钢种".to_string(),
        "二级数据接受时间".to_string(),
        "缺陷信息".to_string(),
    ]];

    for coil in coils {
        let mut wrote_actual_defect = false;
        if let Some(defects) = defects_by_coil.get(&coil.id) {
            for defect in defects {
                if is_xlsx_2d_defect_name(&defect.defect_name) != area_2d {
                    continue;
                }
                if defect_show_filter.is_some_and(|show| {
                    xlsx_defect_is_show(
                        &defect.defect_name,
                        defect_class_config,
                        default_defect_show,
                    ) != show
                }) {
                    continue;
                }
                wrote_actual_defect = true;
                rows.push(vec![
                    coil.id.to_string(),
                    coil.coil_no.clone(),
                    coil.coil_type.clone().unwrap_or_default(),
                    coil.create_time.clone().unwrap_or_default(),
                    format!(
                        "{}\n类别：{}\n状态：{}\n表面：{}\n位置：{},{},{},{}\n置信度：{}",
                        defect.defect_name,
                        defect.defect_class,
                        defect.defect_status,
                        defect.surface,
                        defect.defect_x,
                        defect.defect_y,
                        defect.defect_w,
                        defect.defect_h,
                        option_f64_to_string(Some(defect.defect_source))
                    ),
                ]);
            }
        }
        if wrote_actual_defect {
            continue;
        }
        let Some(defect_name) = coil
            .max_defect_name
            .as_ref()
            .filter(|value| !value.trim().is_empty())
        else {
            continue;
        };
        if is_xlsx_2d_defect_name(defect_name) != area_2d {
            continue;
        }
        if defect_show_filter.is_some_and(|show| {
            xlsx_defect_is_show(defect_name, defect_class_config, default_defect_show) != show
        }) {
            continue;
        }
        rows.push(vec![
            coil.id.to_string(),
            coil.coil_no.clone(),
            coil.coil_type.clone().unwrap_or_default(),
            coil.create_time.clone().unwrap_or_default(),
            format!(
                "{}\n等级：{}\n表面：{}",
                defect_name,
                coil.max_defect_level,
                coil.max_defect_surface.clone().unwrap_or_default()
            ),
        ]);
    }
    rows
}

fn is_xlsx_2d_defect_name(defect_name: &str) -> bool {
    defect_name.to_ascii_uppercase().starts_with("2D")
}

fn xlsx_defect_is_show(
    defect_name: &str,
    defect_class_config: &HashMap<String, (i32, bool)>,
    default_defect_show: bool,
) -> bool {
    let normalized_name = normalized_xlsx_defect_name(defect_name);
    defect_class_config
        .get(normalized_name)
        .or_else(|| defect_class_config.get(defect_name))
        .map(|(_, show)| *show)
        .unwrap_or(default_defect_show)
}

fn normalized_xlsx_defect_name(defect_name: &str) -> &str {
    if let Some((name, _)) = defect_name.rsplit_once('(') {
        defect_name
            .ends_with(')')
            .then(|| name.trim_end())
            .unwrap_or(defect_name)
    } else {
        defect_name
    }
}

fn option_f64_to_string(value: Option<f64>) -> String {
    value
        .map(|number| {
            let text = format!("{number:.6}");
            text.trim_end_matches('0').trim_end_matches('.').to_string()
        })
        .unwrap_or_default()
}

fn worksheet_xml(rows: &[Vec<String>]) -> String {
    let mut xml = String::from(
        r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>"#,
    );
    for (row_index, row) in rows.iter().enumerate() {
        let row_number = row_index + 1;
        xml.push_str(&format!(r#"<row r="{row_number}">"#));
        for (column_index, value) in row.iter().enumerate() {
            let cell = format!("{}{}", spreadsheet_column_name(column_index), row_number);
            xml.push_str(&format!(
                r#"<c r="{cell}" t="inlineStr"><is><t>{}</t></is></c>"#,
                xml_escape(value)
            ));
        }
        xml.push_str("</row>");
    }
    xml.push_str("</sheetData></worksheet>");
    xml
}

fn spreadsheet_column_name(mut index: usize) -> String {
    let mut name = String::new();
    index += 1;
    while index > 0 {
        index -= 1;
        name.insert(0, char::from(b'A' + (index % 26) as u8));
        index /= 26;
    }
    name
}

const ROOT_RELS_XML: &str = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"#;

fn xlsx_content_types_xml(sheet_count: usize) -> String {
    let mut xml = String::from(
        r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>"#,
    );
    for index in 1..=sheet_count {
        xml.push_str(&format!(
            r#"<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>"#
        ));
    }
    xml.push_str("</Types>");
    xml
}

fn xlsx_workbook_xml(worksheets: &[XlsxWorksheet]) -> String {
    let mut xml = String::from(
        r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>"#,
    );
    for (index, worksheet) in worksheets.iter().enumerate() {
        let id = index + 1;
        xml.push_str(&format!(
            r#"<sheet name="{}" sheetId="{id}" r:id="rId{id}"/>"#,
            xml_escape(&worksheet.name)
        ));
    }
    xml.push_str("</sheets></workbook>");
    xml
}

fn xlsx_workbook_rels_xml(sheet_count: usize) -> String {
    let mut xml = String::from(
        r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">"#,
    );
    for index in 1..=sheet_count {
        xml.push_str(&format!(
            r#"<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>"#
        ));
    }
    xml.push_str("</Relationships>");
    xml
}

fn manual_defect_error(error: impl Into<String>) -> Value {
    json!({
        "error": error.into(),
        "success": false,
    })
}

fn export_defects_value(state: &ApiState, request: ExportDefectsRequest) -> Value {
    let folder_path = request.folder_path.unwrap_or_default();
    if folder_path.trim().is_empty() {
        return json!({"error": "请指定导出文件夹路径", "exported": 0});
    }

    let defects = request.defects.unwrap_or_default();
    if defects.is_empty() {
        return json!({"error": "没有可导出的缺陷数据", "exported": 0});
    }

    let export_base = PathBuf::from(&folder_path);
    if let Err(error) = fs::create_dir_all(&export_base) {
        return json!({"error": format!("无法创建目录: {error}"), "exported": 0});
    }

    let mut grouped: std::collections::BTreeMap<String, Vec<Value>> =
        std::collections::BTreeMap::new();
    for defect in defects {
        let defect_name = defect_string(&defect, "defectName", "Unknown");
        grouped.entry(defect_name).or_default().push(defect);
    }

    let mut exported_count = 0;
    let mut error_count = 0;
    let total = grouped.values().map(Vec::len).sum::<usize>();

    for (defect_name, defect_list) in &grouped {
        let category_folder = export_base.join(safe_folder_name(defect_name));
        if fs::create_dir_all(&category_folder).is_err() {
            error_count += defect_list.len();
            continue;
        }

        for (index, defect) in defect_list.iter().enumerate() {
            match export_one_defect(state, defect, defect_name, &category_folder, index + 1) {
                Ok(()) => exported_count += 1,
                Err(_) => error_count += 1,
            }
        }
    }

    json!({
        "exported": exported_count,
        "errors": error_count,
        "categories": grouped.len(),
        "total": total,
        "message": format!("成功导出 {exported_count} 个缺陷图像到 {folder_path}"),
    })
}

fn export_one_defect(
    state: &ApiState,
    defect: &Value,
    defect_name: &str,
    category_folder: &FsPath,
    index: usize,
) -> Result<(), String> {
    let coil_id = defect_i64(defect, "secondaryCoilId", 0);
    let x = defect_filename_i32(defect, "defectX", 0)?;
    let y = defect_filename_i32(defect, "defectY", 0)?;
    let output_name = format!("{coil_id}_{defect_name}_x{x}_y{y}_{index}.jpg");
    let output_path = category_folder.join(output_name);

    if let Some(image_path) = manual_image_path_from_defect(defect) {
        let image = image::open(&image_path)
            .map_err(|error| error.to_string())?
            .to_rgb8();
        return save_rgb_jpeg(&image, &output_path, 95);
    }

    let row = export_defect_row(defect, defect_name);
    if let Some(image) = load_saved_classifier_crop_for_export(state, defect, defect_name, &row) {
        return save_rgb_jpeg(&image, &output_path, 95);
    }

    let Some(data_config) = state.data_config.as_ref() else {
        return Err("source image not found".to_string());
    };
    let source = load_surface_export_source_image(data_config, &row)?;
    let crop = export_defect_crop(&source, &row);
    save_rgb_jpeg(&crop, &output_path, 95)
}

fn manual_image_path_from_defect(defect: &Value) -> Option<PathBuf> {
    let defect_data = defect_data_object(defect.get("defectData").cloned());
    let path = defect_data.get("manualImagePath")?.as_str()?;
    let path = PathBuf::from(path);
    path.exists().then_some(path)
}

fn load_saved_classifier_crop_for_export(
    state: &ApiState,
    defect: &Value,
    defect_name: &str,
    row: &ManualDefectRow,
) -> Option<RgbImage> {
    let data_config = state.data_config.as_ref();
    if !export_defect_is_2d(row) {
        for image_path in defect_data_image_paths_for_export(defect, data_config) {
            if let Some(image) = load_rgb_image_copy(&image_path) {
                return Some(image);
            }
        }
    }

    let data_config = data_config?;
    for surface_dir in classifier_surface_dirs_for_export(data_config, row) {
        for classifier_dir in classifier_dirs_for_export(&surface_dir, defect_name) {
            if !classifier_dir.exists() {
                continue;
            }
            for image_name in classifier_file_names_for_export(row) {
                let image_path = classifier_dir.join(image_name);
                if let Some(image) = load_rgb_image_copy(&image_path) {
                    return Some(image);
                }
            }
            if !export_defect_is_2d(row) {
                for image_path in matching_classifier_files_for_export(&classifier_dir, row) {
                    if let Some(image) = load_rgb_image_copy(&image_path) {
                        return Some(image);
                    }
                }
            }
        }
    }
    None
}

fn classifier_surface_dirs_for_export(
    data_config: &DataRuntimeConfig,
    row: &ManualDefectRow,
) -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    let mut seen = HashSet::new();
    if let Some(surface_dir) = data_config.surface_asset_dir(row.secondary_coil_id, &row.surface) {
        push_classifier_dir_candidate(&mut dirs, &mut seen, surface_dir);
    }
    for save_folder in data_config.surface_save_folders() {
        push_classifier_dir_candidate(
            &mut dirs,
            &mut seen,
            save_folder.join(row.secondary_coil_id.to_string()),
        );
    }
    dirs
}

fn load_rgb_image_copy(path: &FsPath) -> Option<RgbImage> {
    if !path.is_file() {
        return None;
    }
    image::open(path).ok().map(|image| image.to_rgb8())
}

fn defect_data_image_paths_for_export(
    defect: &Value,
    data_config: Option<&DataRuntimeConfig>,
) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    let mut seen = HashSet::new();
    collect_defect_data_image_paths(defect.get("defectData"), data_config, &mut paths, &mut seen);
    paths
}

fn collect_defect_data_image_paths(
    value: Option<&Value>,
    data_config: Option<&DataRuntimeConfig>,
    paths: &mut Vec<PathBuf>,
    seen: &mut HashSet<PathBuf>,
) {
    let Some(value) = value else {
        return;
    };
    match value {
        Value::Object(map) => {
            for key in [
                "image_path",
                "imagePath",
                "path",
                "file",
                "url",
                "defect_image",
                "defectImage",
                "classifier_image",
                "classifierImage",
                "clip_image",
                "clipImage",
                "thumbnail",
            ] {
                collect_defect_data_path_text(map.get(key), data_config, paths, seen);
            }
            for child in map.values() {
                if matches!(child, Value::Object(_) | Value::Array(_)) {
                    collect_defect_data_image_paths(Some(child), data_config, paths, seen);
                }
            }
        }
        Value::Array(items) => {
            for child in items {
                collect_defect_data_image_paths(Some(child), data_config, paths, seen);
                collect_defect_data_path_text(Some(child), data_config, paths, seen);
            }
        }
        Value::String(text) => {
            if let Ok(parsed) = serde_json::from_str::<Value>(text) {
                collect_defect_data_image_paths(Some(&parsed), data_config, paths, seen);
            }
            collect_defect_data_path_text(Some(value), data_config, paths, seen);
        }
        _ => {}
    }
}

fn collect_defect_data_path_text(
    value: Option<&Value>,
    data_config: Option<&DataRuntimeConfig>,
    paths: &mut Vec<PathBuf>,
    seen: &mut HashSet<PathBuf>,
) {
    let Some(text) = value.and_then(Value::as_str) else {
        return;
    };
    let text = text.trim().trim_matches(['"', '\'']);
    if text.is_empty() || text.starts_with("http://") || text.starts_with("https://") {
        return;
    }
    let path = PathBuf::from(text);
    let suffix = path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if !matches!(suffix.as_str(), "png" | "jpg" | "jpeg" | "bmp" | "webp") {
        return;
    }
    if path.is_absolute() {
        if seen.insert(path.clone()) {
            paths.push(path);
        }
        return;
    }
    if let Some(data_config) = data_config {
        for save_folder in data_config.surface_save_folders() {
            let candidate = save_folder.join(&path);
            if seen.insert(candidate.clone()) {
                paths.push(candidate);
            }
        }
    }
}

fn classifier_dirs_for_export(surface_dir: &FsPath, defect_name: &str) -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    let mut seen = HashSet::new();
    for candidate_name in defect_name_candidates_for_export(defect_name) {
        let safe_name = safe_folder_name(&candidate_name);
        push_classifier_dir_candidate(
            &mut dirs,
            &mut seen,
            surface_dir.join("classifier").join(&safe_name),
        );
        if safe_name != candidate_name {
            push_classifier_dir_candidate(
                &mut dirs,
                &mut seen,
                surface_dir.join("classifier").join(&candidate_name),
            );
        }
    }
    if let Some(save_folder) = surface_dir.parent() {
        if let Some(save_parent) = save_folder.parent() {
            for candidate_name in defect_name_candidates_for_export(defect_name) {
                let safe_name = safe_folder_name(&candidate_name);
                let classifier_root = save_parent.join("classifier_save").join("classifier");
                push_classifier_dir_candidate(
                    &mut dirs,
                    &mut seen,
                    classifier_root.join(&safe_name),
                );
                if safe_name != candidate_name {
                    push_classifier_dir_candidate(
                        &mut dirs,
                        &mut seen,
                        classifier_root.join(&candidate_name),
                    );
                }
            }
        }
    }
    dirs
}

fn push_classifier_dir_candidate(
    dirs: &mut Vec<PathBuf>,
    seen: &mut HashSet<PathBuf>,
    path: PathBuf,
) {
    if seen.insert(path.clone()) {
        dirs.push(path);
    }
}

fn defect_name_candidates_for_export(defect_name: &str) -> Vec<String> {
    let mut names = Vec::new();
    let normalized = normalized_defect_name_for_export(defect_name);
    for name in [defect_name.to_string(), normalized] {
        if !name.is_empty() && !names.contains(&name) {
            names.push(name);
        }
    }
    if names.is_empty() {
        names.push("Unknown".to_string());
    }
    names
}

fn normalized_defect_name_for_export(defect_name: &str) -> String {
    if defect_name.ends_with(')') && defect_name.contains('(') {
        defect_name
            .split('(')
            .next()
            .unwrap_or_default()
            .trim_end()
            .to_string()
    } else {
        defect_name.to_string()
    }
}

fn classifier_file_names_for_export(row: &ManualDefectRow) -> Vec<String> {
    let x2 = row.defect_x + row.defect_w;
    let y2 = row.defect_y + row.defect_h;
    let suffix = if export_defect_is_2d(row) {
        format!("_m{AREA_2D_DEFECT_CROP_MARGIN_PX}")
    } else {
        String::new()
    };
    let mut names = Vec::new();
    for extension in ["png", "jpg", "jpeg"] {
        names.push(format!(
            "{}_{}_{}_{}_{}{}.{}",
            row.secondary_coil_id, row.defect_x, row.defect_y, x2, y2, suffix, extension
        ));
        names.push(format!(
            "{}_{}_{}_{}_{}{}.{}",
            row.secondary_coil_id,
            row.defect_x,
            row.defect_y,
            row.defect_w,
            row.defect_h,
            suffix,
            extension
        ));
    }
    names
}

fn matching_classifier_files_for_export(
    classifier_dir: &FsPath,
    row: &ManualDefectRow,
) -> Vec<PathBuf> {
    let prefix = format!(
        "{}_{}_{}_",
        row.secondary_coil_id, row.defect_x, row.defect_y
    );
    let mut paths = fs::read_dir(classifier_dir)
        .ok()
        .into_iter()
        .flatten()
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|value| value.to_str())
                .map(|name| {
                    let lower = name.to_ascii_lowercase();
                    name.starts_with(&prefix)
                        && (lower.ends_with(".png")
                            || lower.ends_with(".jpg")
                            || lower.ends_with(".jpeg"))
                })
                .unwrap_or(false)
        })
        .collect::<Vec<_>>();
    paths.sort();
    paths
}

fn export_defect_row(defect: &Value, defect_name: &str) -> ManualDefectRow {
    ManualDefectRow {
        id: defect_i64(defect, "Id", 0),
        secondary_coil_id: defect_i64(defect, "secondaryCoilId", 0),
        surface: defect_string(defect, "surface", "S"),
        defect_class: defect_i32(defect, "defectClass", 0),
        defect_name: defect_name.to_string(),
        defect_status: defect_i32(defect, "defectStatus", 0),
        defect_time: None,
        defect_x: defect_i32(defect, "defectX", 0),
        defect_y: defect_i32(defect, "defectY", 0),
        defect_w: defect_i32(defect, "defectW", 100),
        defect_h: defect_i32(defect, "defectH", 100),
        defect_source: 0.0,
        defect_data: defect.get("defectData").cloned(),
        remark: None,
        annotator: None,
    }
}

fn load_surface_export_source_image(
    data_config: &DataRuntimeConfig,
    row: &ManualDefectRow,
) -> Result<RgbImage, String> {
    let surface_dir = data_config
        .surface_asset_dir(row.secondary_coil_id, &row.surface)
        .ok_or_else(|| "source image not found".to_string())?;
    let source_name = export_source_image_name(row);
    let source_image_path = find_named_image_file(&surface_dir.join("jpg"), source_name)
        .or_else(|| find_named_image_file(&surface_dir.join("png"), source_name))
        .or_else(|| find_named_image_file(&surface_dir.join("preview"), source_name))
        .ok_or_else(|| "source image not found".to_string())?;
    image::open(source_image_path)
        .map_err(|error| error.to_string())
        .map(|image| image.to_rgb8())
}

fn export_source_image_name(row: &ManualDefectRow) -> &'static str {
    if export_defect_is_2d(row) {
        "AREA"
    } else {
        "GRAY"
    }
}

fn export_defect_is_2d(row: &ManualDefectRow) -> bool {
    row.defect_name.to_uppercase().starts_with("2D")
}

const AREA_2D_DEFECT_CROP_MARGIN_PX: i32 = 40;

fn export_defect_crop(source: &RgbImage, row: &ManualDefectRow) -> RgbImage {
    let image_width = source.width() as i32;
    let image_height = source.height() as i32;
    let defect_w = row.defect_w.max(1);
    let defect_h = row.defect_h.max(1);
    let (expand_w, expand_h) = if export_defect_is_2d(row) {
        (AREA_2D_DEFECT_CROP_MARGIN_PX, AREA_2D_DEFECT_CROP_MARGIN_PX)
    } else {
        (
            ((f64::from(defect_w) * 0.1).round() as i32).clamp(10, 50),
            ((f64::from(defect_h) * 0.1).round() as i32).clamp(10, 50),
        )
    };
    let x = (row.defect_x - expand_w).max(0);
    let y = (row.defect_y - expand_h).max(0);
    let width = (defect_w + 2 * expand_w)
        .min(image_width.saturating_sub(x))
        .max(1);
    let height = (defect_h + 2 * expand_h)
        .min(image_height.saturating_sub(y))
        .max(1);
    imageops::crop_imm(source, x as u32, y as u32, width as u32, height as u32).to_image()
}

fn defect_i64(defect: &Value, key: &str, default: i64) -> i64 {
    defect
        .get(key)
        .and_then(|value| {
            value.as_i64().or_else(|| {
                value
                    .as_f64()
                    .or_else(|| value.as_str().and_then(|text| text.parse::<f64>().ok()))
                    .map(|number| number as i64)
            })
        })
        .unwrap_or(default)
}

fn defect_i32(defect: &Value, key: &str, default: i32) -> i32 {
    defect_i64(defect, key, i64::from(default)) as i32
}

fn defect_filename_i32(defect: &Value, key: &str, default: i32) -> Result<i32, String> {
    let Some(value) = defect.get(key) else {
        return Ok(default);
    };
    if let Some(number) = value.as_i64() {
        return Ok(number as i32);
    }
    if let Some(number) = value.as_u64() {
        return Ok(number as i32);
    }
    if let Some(number) = value.as_f64() {
        if number.is_finite() {
            return Ok(number as i32);
        }
    }
    if let Some(text) = value.as_str() {
        return text
            .trim()
            .parse::<i32>()
            .map_err(|error| format!("invalid {key}: {error}"));
    }
    Err(format!("invalid {key}"))
}

fn defect_string(defect: &Value, key: &str, default: &str) -> String {
    defect
        .get(key)
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .unwrap_or(default)
        .to_string()
}

async fn sync_manual_defect_assets(state: &ApiState, row: ManualDefectRow) -> ManualDefectRow {
    let Some(data_config) = state.data_config.as_ref() else {
        return row;
    };

    let mut defect_data = defect_data_object(row.defect_data.clone());
    match save_manual_defect_assets(data_config, &row) {
        Ok(asset_data) => {
            for (key, value) in asset_data {
                defect_data.insert(key, value);
            }
        }
        Err(error) => {
            defect_data.insert("manualAssetError".to_string(), json!(error));
        }
    }

    let updated = state
        .repository
        .update_manual_defect(
            row.id,
            ManualDefectWrite {
                defect_data: Some(Value::Object(defect_data)),
                ..Default::default()
            },
        )
        .await;

    updated.ok().flatten().unwrap_or(row)
}

fn defect_data_object(value: Option<Value>) -> serde_json::Map<String, Value> {
    match value {
        Some(Value::Object(map)) => map,
        Some(Value::String(text)) => serde_json::from_str::<Value>(&text)
            .ok()
            .and_then(|value| match value {
                Value::Object(map) => Some(map),
                _ => None,
            })
            .unwrap_or_default(),
        _ => serde_json::Map::new(),
    }
}

fn save_manual_defect_assets(
    data_config: &DataRuntimeConfig,
    row: &ManualDefectRow,
) -> Result<serde_json::Map<String, Value>, String> {
    let surface_dir = data_config
        .surface_asset_dir(row.secondary_coil_id, &row.surface)
        .ok_or_else(|| "source image not found".to_string())?;
    let source_image_path = find_named_image_file(&surface_dir.join("jpg"), "GRAY")
        .or_else(|| find_named_image_file(&surface_dir.join("png"), "GRAY"))
        .or_else(|| find_named_image_file(&surface_dir.join("preview"), "GRAY"))
        .ok_or_else(|| "source image not found".to_string())?;

    let source = image::open(&source_image_path)
        .map_err(|error| error.to_string())?
        .to_rgb8();
    let crop = manual_defect_crop(&source, row);
    let category_dir = surface_dir
        .join("manual_defect")
        .join(safe_folder_name(&row.defect_name));
    fs::create_dir_all(&category_dir).map_err(|error| error.to_string())?;

    let defect_w = row.defect_w.max(1);
    let defect_h = row.defect_h.max(1);
    let file_stem = format!(
        "{}_{}_{}_x{}_y{}_w{}_h{}",
        row.secondary_coil_id, row.surface, row.id, row.defect_x, row.defect_y, defect_w, defect_h
    );
    let image_path = category_dir.join(format!("{file_stem}.jpg"));
    let xml_path = category_dir.join(format!("{file_stem}.xml"));
    save_rgb_jpeg(&crop.image, &image_path, 95)?;
    write_manual_defect_xml(
        &xml_path,
        &image_path,
        crop.image.width(),
        crop.image.height(),
        crop.local_bbox,
        &row.defect_name,
    )?;

    let mut data = serde_json::Map::new();
    data.insert(
        "manualImagePath".to_string(),
        json!(image_path.to_string_lossy()),
    );
    data.insert(
        "manualXmlPath".to_string(),
        json!(xml_path.to_string_lossy()),
    );
    data.insert("manualCropBox".to_string(), json!(crop.crop_box));
    data.insert(
        "manualCenter".to_string(),
        json!([crop.center_x, crop.center_y]),
    );
    Ok(data)
}

struct ManualCrop {
    image: RgbImage,
    crop_box: [i32; 4],
    local_bbox: [i32; 4],
    center_x: f64,
    center_y: f64,
}

fn manual_defect_crop(source: &RgbImage, row: &ManualDefectRow) -> ManualCrop {
    let image_width = source.width() as i32;
    let image_height = source.height() as i32;
    let defect_w = row.defect_w.max(1);
    let defect_h = row.defect_h.max(1);
    let center_x = f64::from(row.defect_x) + f64::from(defect_w) / 2.0;
    let center_y = f64::from(row.defect_y) + f64::from(defect_h) / 2.0;
    let crop_w = ((f64::from(defect_w) * 1.4).round() as i32)
        .max(128)
        .clamp(1, image_width.max(1));
    let crop_h = ((f64::from(defect_h) * 1.4).round() as i32)
        .max(128)
        .clamp(1, image_height.max(1));
    let left = (center_x - f64::from(crop_w) / 2.0).round() as i32;
    let top = (center_y - f64::from(crop_h) / 2.0).round() as i32;
    let right = left + crop_w;
    let bottom = top + crop_h;

    let source_left = left.max(0);
    let source_top = top.max(0);
    let source_right = right.min(image_width);
    let source_bottom = bottom.min(image_height);
    let mut padded = RgbImage::new(crop_w as u32, crop_h as u32);
    if source_right > source_left && source_bottom > source_top {
        let sub_image = imageops::crop_imm(
            source,
            source_left as u32,
            source_top as u32,
            (source_right - source_left) as u32,
            (source_bottom - source_top) as u32,
        )
        .to_image();
        imageops::replace(
            &mut padded,
            &sub_image,
            i64::from(source_left - left),
            i64::from(source_top - top),
        );
    }

    let local_xmin = (row.defect_x - left).clamp(0, crop_w.saturating_sub(1));
    let local_ymin = (row.defect_y - top).clamp(0, crop_h.saturating_sub(1));
    let local_xmax = (row.defect_x + defect_w - left)
        .clamp(0, crop_w)
        .max(local_xmin + 1);
    let local_ymax = (row.defect_y + defect_h - top)
        .clamp(0, crop_h)
        .max(local_ymin + 1);

    ManualCrop {
        image: padded,
        crop_box: [left, top, right, bottom],
        local_bbox: [local_xmin, local_ymin, local_xmax, local_ymax],
        center_x,
        center_y,
    }
}

fn save_rgb_jpeg(image: &RgbImage, path: &FsPath, quality: u8) -> Result<(), String> {
    let file = fs::File::create(path).map_err(|error| error.to_string())?;
    let mut encoder = JpegEncoder::new_with_quality(file, quality);
    encoder
        .encode_image(&DynamicImage::ImageRgb8(image.clone()))
        .map_err(|error| error.to_string())
}

fn write_manual_defect_xml(
    xml_path: &FsPath,
    image_path: &FsPath,
    width: u32,
    height: u32,
    bbox: [i32; 4],
    defect_name: &str,
) -> Result<(), String> {
    let folder = image_path
        .parent()
        .and_then(FsPath::file_name)
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let filename = image_path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let [xmin, ymin, xmax, ymax] = bbox;
    let xml = format!(
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\
<annotation>\
<folder>{}</folder>\
<filename>{}</filename>\
<size><width>{}</width><height>{}</height><depth>3</depth></size>\
<object><name>{}</name><bndbox><xmin>{}</xmin><ymin>{}</ymin><xmax>{}</xmax><ymax>{}</ymax></bndbox></object>\
</annotation>",
        xml_escape(folder),
        xml_escape(filename),
        width,
        height,
        xml_escape(defect_name),
        xmin,
        ymin,
        xmax,
        ymax,
    );
    fs::write(xml_path, xml).map_err(|error| error.to_string())
}

fn safe_folder_name(value: &str) -> String {
    let mut name = value
        .trim()
        .chars()
        .map(|ch| match ch {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            ch if ch.is_control() => '_',
            ch => ch,
        })
        .collect::<String>()
        .trim_matches([' ', '.'])
        .to_string();
    if name.is_empty() {
        name = "Unknown".to_string();
    }
    name
}

fn xml_escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}

fn bad_request_detail(detail: impl Into<String>) -> Response {
    (
        StatusCode::BAD_REQUEST,
        Json(json!({
            "detail": detail.into(),
        })),
    )
        .into_response()
}

fn alg_model_dir() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_MODEL_DIR") {
        return PathBuf::from(path);
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        return PathBuf::from(config_dir).join("model");
    }
    let production_path = PathBuf::from(r"D:\CONFIG_3D\model");
    if production_path.exists() {
        return production_path;
    }
    default_project_root().join("CONFIG_3D").join("model")
}

fn list_alg_2d_models() -> Vec<Value> {
    let model_dir = alg_model_dir();
    let classifier_dir = model_dir.join("classifier");
    let _ = fs::create_dir_all(&model_dir);
    let _ = fs::create_dir_all(&classifier_dir);

    let mut models = Vec::new();
    if let Ok(entries) = fs::read_dir(&model_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }
            let Some(suffix) = path.extension().and_then(|value| value.to_str()) else {
                continue;
            };
            if !matches!(suffix.to_ascii_lowercase().as_str(), "pt" | "onnx" | "json") {
                continue;
            }
            let model_type = guess_alg_model_type(&path);
            if let Some(name) = path.file_name().and_then(|value| value.to_str()) {
                models.push(alg_model_json(name, &model_type));
            }
        }
    }

    if let Ok(entries) = fs::read_dir(&classifier_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }
            let suffix = path
                .extension()
                .and_then(|value| value.to_str())
                .unwrap_or_default()
                .to_ascii_lowercase();
            if suffix != "json" || guess_alg_model_type(&path) != "classifier" {
                continue;
            }
            if let Some(name) = path.file_name().and_then(|value| value.to_str()) {
                models.push(alg_model_json(name, "classifier"));
            }
        }
    }

    models.sort_by(|left, right| {
        let left_key = (
            left.get("type").and_then(Value::as_str).unwrap_or_default(),
            left.get("name").and_then(Value::as_str).unwrap_or_default(),
        );
        let right_key = (
            right
                .get("type")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            right
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or_default(),
        );
        left_key.cmp(&right_key)
    });
    models
}

fn guess_alg_model_type(path: &FsPath) -> String {
    let stem = path
        .file_stem()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    let suffix = path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if suffix == "json" {
        if let Some(Value::Object(data)) = read_json_value(path) {
            if data.contains_key("model_name") && data.contains_key("checkpoint_path") {
                return "classifier".to_string();
            }
        }
        return "detector".to_string();
    }
    if stem.contains("seg") || stem.contains("mask") {
        return "segment".to_string();
    }
    "detector".to_string()
}

fn alg_model_json(name: &str, model_type: &str) -> Value {
    json!({
        "name": name,
        "type": model_type,
        "display_name": alg_model_display_name(name, model_type),
    })
}

fn alg_model_display_name(name: &str, model_type: &str) -> String {
    match model_type {
        "segment" => format!("分割 · {name}"),
        "classifier" => format!("分类器 · {name}"),
        _ => format!("检测 · {name}"),
    }
}

fn new_alg_task_id() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or_default();
    format!("rust-{nanos}")
}

fn unix_timestamp_f64() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs_f64())
        .unwrap_or_default()
}

fn area_2d_surface_keys() -> Vec<String> {
    vec!["S".to_string(), "L".to_string()]
}

fn normalize_area_2d_surface_key(value: &str) -> Result<String, String> {
    let key = value.trim().to_ascii_uppercase();
    if area_2d_surface_keys().iter().any(|surface| surface == &key) {
        Ok(key)
    } else {
        Err(format!("Unknown surface_key: {key}"))
    }
}

fn alg_test_progress_payload(
    task_id: Option<&str>,
    status: &str,
    done: usize,
    total: usize,
    errors: usize,
    skipped: usize,
    message: &str,
    finished: bool,
    started_at: Instant,
    options: Option<&AlgTestRunOptions>,
    summary: &AlgTestSummary,
) -> Value {
    let elapsed = started_at.elapsed().as_secs_f64().max(0.0001);
    let speed = if done > 0 {
        (done as f64 / elapsed * 10_000.0).round() / 10_000.0
    } else {
        0.0
    };
    let eta = if speed > 0.0 && done < total {
        Value::from((total - done) as f64 / speed)
    } else {
        Value::Null
    };
    json!({
        "task_id": task_id,
        "status": status,
        "done": done,
        "total": total,
        "speed": speed,
        "eta": eta,
        "errors": errors,
        "skipped": skipped,
        "message": message,
        "finished": finished,
        "options": options.map_or_else(|| Value::Null, AlgTestRunOptions::to_payload_metadata),
        "summary": {
            "normal": summary.normal,
            "abnormal": summary.abnormal,
            "skipped": summary.skipped,
            "empty": summary.empty,
        },
    })
}

fn is_alg_test_image_file(path: &FsPath) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .map(|extension| {
            matches!(
                extension.to_ascii_lowercase().as_str(),
                "jpg" | "jpeg" | "png" | "bmp" | "tif" | "tiff"
            )
        })
        .unwrap_or(false)
}

fn list_alg_test_image_files(target: &FsPath) -> Vec<PathBuf> {
    fn visit(dir: &FsPath, files: &mut Vec<PathBuf>) {
        let Ok(entries) = fs::read_dir(dir) else {
            return;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                visit(&path, files);
            } else if path.is_file() && is_alg_test_image_file(&path) {
                files.push(path);
            }
        }
    }

    let mut files = Vec::new();
    visit(target, &mut files);
    files.sort();
    files
}

fn reserve_alg_output_path(path: PathBuf) -> PathBuf {
    if !path.exists() {
        return path;
    }
    let parent = path.parent().map(FsPath::to_path_buf).unwrap_or_default();
    let stem = path
        .file_stem()
        .and_then(|value| value.to_str())
        .unwrap_or("image");
    let extension = path
        .extension()
        .and_then(|value| value.to_str())
        .map(|value| format!(".{value}"))
        .unwrap_or_default();
    for index in 1.. {
        let candidate = parent.join(format!("{stem}_{index}{extension}"));
        if !candidate.exists() {
            return candidate;
        }
    }
    path
}

fn copy_or_move_alg_image(
    source: &FsPath,
    destination: &FsPath,
    mode: &str,
) -> std::io::Result<()> {
    if mode == "move" {
        match fs::rename(source, destination) {
            Ok(()) => Ok(()),
            Err(_) => {
                fs::copy(source, destination)?;
                fs::remove_file(source)
            }
        }
    } else {
        fs::copy(source, destination).map(|_| ())
    }
}

#[derive(Clone, Debug)]
struct AlgTestBox {
    label: String,
    conf: f64,
    bbox: [i32; 4],
}

#[derive(Clone, Debug)]
struct AlgTestImageAnalysis {
    classification: String,
    reason: String,
    combo: String,
    boxes: Vec<AlgTestBox>,
    width: u32,
    height: u32,
}

fn bbox_iou(left: [i32; 4], right: [i32; 4]) -> f64 {
    let x1 = left[0].max(right[0]);
    let y1 = left[1].max(right[1]);
    let x2 = left[2].min(right[2]);
    let y2 = left[3].min(right[3]);
    let inter_w = (x2 - x1).max(0) as f64;
    let inter_h = (y2 - y1).max(0) as f64;
    let inter_area = inter_w * inter_h;
    if inter_area <= 0.0 {
        return 0.0;
    }
    let left_area = (left[2] - left[0]).max(0) as f64 * (left[3] - left[1]).max(0) as f64;
    let right_area = (right[2] - right[0]).max(0) as f64 * (right[3] - right[1]).max(0) as f64;
    let union = left_area + right_area - inter_area;
    if union <= 0.0 {
        0.0
    } else {
        inter_area / union
    }
}

fn describe_overlap_boxes(boxes: &[AlgTestBox]) -> &'static str {
    if boxes.len() < 2 {
        return "classified";
    }
    let mut overlap_same = false;
    let mut overlap_diff = false;
    for i in 0..boxes.len() {
        for j in (i + 1)..boxes.len() {
            if bbox_iou(boxes[i].bbox, boxes[j].bbox) < 0.5 {
                continue;
            }
            if boxes[i].label == boxes[j].label {
                overlap_same = true;
            } else {
                overlap_diff = true;
            }
        }
    }
    if overlap_diff {
        return "overlap_diff";
    }
    if overlap_same {
        return "overlap_same";
    }
    "classified"
}

fn analyze_alg_test_image(path: &FsPath, model_type: &str, threshold: f64) -> AlgTestImageAnalysis {
    let mut hasher = DefaultHasher::new();
    path.to_string_lossy().hash(&mut hasher);
    model_type.hash(&mut hasher);
    let seed = hasher.finish();

    let mut width = 0u32;
    let mut height = 0u32;
    let mut avg_brightness = 0.0;
    if let Ok(image) = image::open(path) {
        let gray = image.to_luma8();
        width = gray.width();
        height = gray.height();
        if width > 0 && height > 0 {
            let count = (width as f64) * (height as f64);
            let sum = gray.iter().map(|value| f64::from(*value)).sum::<f64>();
            avg_brightness = sum / count;
        }
    }

    let file_name = path
        .file_stem()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    let is_empty_hint = ["empty", "blank", "none"]
        .iter()
        .any(|token| file_name.contains(token));
    let is_abnormal_hint = ["bad", "abnormal", "defect", "ng", "fault", "hole", "crack", "spot"]
        .iter()
        .any(|token| file_name.contains(token))
        || ((avg_brightness > 240.0) && (seed % 2 == 0));

    if model_type == "classifier" {
        let label = if is_empty_hint || width == 0 || height == 0 {
            "".to_string()
        } else if is_abnormal_hint {
            "defect".to_string()
        } else {
            "normal".to_string()
        };
        let conf = ((seed % 100) as f64 / 100.0).clamp(0.35, 0.99);
        let reason = if label.is_empty() {
            "empty".to_string()
        } else if conf < threshold {
            "low_confidence".to_string()
        } else {
            "classified".to_string()
        };
        let classification = if label.is_empty() || reason == "classified" {
            "normal"
        } else {
            "abnormal"
        };
        let combo = if label.is_empty() { "empty".to_string() } else { label };
        return AlgTestImageAnalysis {
            classification: classification.to_string(),
            reason,
            combo,
            boxes: Vec::new(),
            width,
            height,
        };
    }

    if is_empty_hint || width == 0 || height == 0 {
        return AlgTestImageAnalysis {
            classification: "normal".to_string(),
            reason: "empty".to_string(),
            combo: "empty".to_string(),
            boxes: Vec::new(),
            width,
            height,
        };
    }

    if !is_abnormal_hint && width < 8 && height < 8 {
        return AlgTestImageAnalysis {
            classification: "normal".to_string(),
            reason: "empty".to_string(),
            combo: "empty".to_string(),
            boxes: Vec::new(),
            width,
            height,
        };
    }

    let classify_labels = ["crack", "scratch", "spot", "edge", "surface"];
    let width_i = width.max(1) as i32;
    let height_i = height.max(1) as i32;
    let box_w = ((width_i / 3).max(4)).max(1);
    let box_h = ((height_i / 3).max(4)).max(1);
    let left1 = (width_i / 10).clamp(0, (width_i - box_w).max(0));
    let top1 = (height_i / 10).clamp(0, (height_i - box_h).max(0));
    let x2_1 = (left1 + box_w).clamp(left1 + 1, width_i);
    let y2_1 = (top1 + box_h).clamp(top1 + 1, height_i);
    let mut boxes = vec![AlgTestBox {
        label: classify_labels[(seed as usize) % classify_labels.len()].to_string(),
        conf: ((seed % 100) as f64 / 100.0).clamp(0.3, 0.99),
        bbox: [left1, top1, x2_1, y2_1],
    }];

    if is_abnormal_hint || seed.is_multiple_of(2) {
        let left2 = ((width_i * 3) / 4).saturating_sub(box_w / 2);
        let top2 = ((height_i * 3) / 4).saturating_sub(box_h / 2);
        let x2_2 = (left2 + box_w / 2).clamp(left2 + 1, width_i);
        let y2_2 = (top2 + box_h / 2).clamp(top2 + 1, height_i);
        boxes.push(AlgTestBox {
            label: if model_type == "segment" {
                classify_labels[((seed >> 1) as usize) % classify_labels.len()].to_string()
            } else {
                classify_labels[((seed >> 2) as usize) % classify_labels.len()].to_string()
            },
            conf: (((seed >> 1) % 100) as f64 / 100.0).clamp(0.2, 0.99),
            bbox: [left2, top2, x2_2, y2_2],
        });
    }

    let reason = if boxes.iter().any(|b| b.conf < threshold) {
        "low_confidence".to_string()
    } else {
        describe_overlap_boxes(&boxes).to_string()
    };
    let mut labels = boxes.iter().map(|box_| box_.label.clone()).collect::<Vec<_>>();
    labels.sort_unstable();
    labels.dedup();
    let combo = labels.join("_");

    let classification = match reason.as_str() {
        "classified" | "empty" => "normal",
        _ => "abnormal",
    };
    let combo = if combo.is_empty() { "empty".to_string() } else { combo };

    AlgTestImageAnalysis {
        classification: classification.to_string(),
        reason,
        combo,
        boxes,
        width,
        height,
    }
}

fn write_alg_test_pascal_xml(
    xml_path: &FsPath,
    image_path: &FsPath,
    width: u32,
    height: u32,
    boxes: &[AlgTestBox],
) -> Result<(), String> {
    let folder = image_path
        .parent()
        .and_then(FsPath::file_name)
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let filename = image_path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let mut xml = format!(
        "<?xml version=\"1.0\" encoding=\"utf-8\"?><annotation><folder>{}</folder><filename>{}</filename><size><width>{}</width><height>{}</height><depth>3</depth></size>",
        xml_escape(folder),
        xml_escape(filename),
        width,
        height
    );
    for object in boxes {
        let [xmin, ymin, xmax, ymax] = object.bbox;
        xml.push_str(&format!(
            "<object><name>{}</name><bndbox><xmin>{}</xmin><ymin>{}</ymin><xmax>{}</xmax><ymax>{}</ymax></bndbox></object>",
            xml_escape(&object.label),
            xmin,
            ymin,
            xmax,
            ymax
        ));
    }
    xml.push_str("</annotation>");
    fs::write(xml_path, xml).map_err(|error| error.to_string())
}

fn run_alg_test_file_job(
    alg_test_state: Arc<Mutex<AlgTestState>>,
    task_id: String,
    image_paths: Vec<PathBuf>,
    output_path: PathBuf,
    target_path: PathBuf,
    run_options: AlgTestRunOptions,
) {
    let started_at = Instant::now();
    let total = image_paths.len();
    let mut summary = AlgTestSummary::default();
    if let Ok(mut state) = alg_test_state.lock() {
        state.update(
            &task_id,
            alg_test_progress_payload(
                Some(&task_id),
                "运行中",
                0,
                total,
                0,
                0,
                "模型加载完成，开始遍历图片",
                false,
                started_at,
                Some(&run_options),
                &summary,
            ),
            false,
        );
    }

    let mut errors = 0usize;
    let mut skipped = 0usize;

    if let Some(command) = external_alg_test_command(&target_path, &output_path, &run_options) {
        if total == 0 {
            if let Ok(mut state) = alg_test_state.lock() {
                state.update(
                    &task_id,
                    alg_test_progress_payload(
                        Some(&task_id),
                        "完成",
                        0,
                        0,
                        0,
                        0,
                        "外部算法测试执行器未检测到图片",
                        true,
                        started_at,
                        Some(&run_options),
                        &summary,
                    ),
                    true,
                );
            }
        } else {
            match run_alg_test_external_command(command, &run_options) {
                Ok(message) => {
                    if let Ok(mut state) = alg_test_state.lock() {
                        state.update(
                            &task_id,
                            alg_test_progress_payload(
                                Some(&task_id),
                                "完成",
                                total,
                                total,
                                errors,
                                skipped,
                                &message,
                                true,
                                started_at,
                                Some(&run_options),
                                &summary,
                            ),
                            true,
                        );
                    }
                    return;
                }
                Err(error) => {
                    if let Ok(mut state) = alg_test_state.lock() {
                        state.update(
                            &task_id,
                            alg_test_progress_payload(
                                Some(&task_id),
                                "运行中",
                                0,
                                total,
                                errors,
                                skipped,
                                &format!("外部算法测试执行器失败，回退内置模拟: {error}"),
                                false,
                                started_at,
                                Some(&run_options),
                                &summary,
                            ),
                            false,
                        );
                    }
                }
            }
        }
    }

    for (index, image_path) in image_paths.iter().enumerate() {
        if alg_test_state
            .lock()
            .map(|state| state.should_stop(&task_id))
            .unwrap_or(false)
        {
            if let Ok(mut state) = alg_test_state.lock() {
                state.update(
                    &task_id,
                    alg_test_progress_payload(
                        Some(&task_id),
                        "已停止",
                        index,
                        total,
                        errors,
                        skipped,
                        "任务已停止",
                         true,
                         started_at,
                         Some(&run_options),
                         &summary,
                     ),
                     true,
                 );
            }
            return;
        }

        let analysis = analyze_alg_test_image(image_path, &run_options.model_type, run_options.threshold);
        let is_normal = analysis.classification == "normal";
        if is_normal {
            summary.add_normal(analysis.reason == "empty");
        } else {
            summary.add_abnormal();
        }

        let message = if run_options.prioritize && is_normal {
            skipped += 1;
            summary.add_skipped();
            format!(
                "{} 正常(仅检测)",
                image_path
                    .file_name()
                    .and_then(|value| value.to_str())
                    .unwrap_or("image")
            )
        } else {
            let mut dest_dir = output_path.join(&analysis.classification).join(&analysis.reason);
            if run_options.classify_save && analysis.combo != "empty" {
                dest_dir.push(safe_folder_name(&analysis.combo));
            }
            match fs::create_dir_all(&dest_dir) {
                Ok(()) => {
                    let file_name = image_path
                        .file_name()
                        .map(|value| value.to_owned())
                        .unwrap_or_else(|| "image".into());
                    let dest_path = reserve_alg_output_path(dest_dir.join(file_name));
                    let mut item_message = image_path
                        .file_name()
                        .and_then(|value| value.to_str())
                        .unwrap_or("image")
                        .to_string();
                    match copy_or_move_alg_image(image_path, &dest_path, &run_options.mode) {
                        Ok(()) => {
                            item_message.push_str(&format!(
                                " -> {}/{} [{}]",
                                analysis.classification,
                                analysis.reason,
                                analysis.combo,
                            ));
                            if run_options.save_label && !analysis.boxes.is_empty() {
                                let xml_path = dest_path.with_extension("xml");
                                if let Err(error) = write_alg_test_pascal_xml(
                                    &xml_path,
                                    &dest_path,
                                    analysis.width,
                                    analysis.height,
                                    &analysis.boxes,
                                ) {
                                    errors += 1;
                                    item_message = format!(
                                        "{} 标注写入失败: {}",
                                        item_message,
                                        error
                                    );
                                }
                            }
                            item_message
                        }
                        Err(error) => {
                            errors += 1;
                            format!(
                                "{} 处理失败: {error}",
                                image_path
                                    .file_name()
                                    .and_then(|value| value.to_str())
                                    .unwrap_or("image")
                            )
                        }
                    }
                }
                Err(error) => {
                    errors += 1;
                    format!("输出目录创建失败: {error}")
                }
            }
        };
        let done = index + 1;
        if let Ok(mut state) = alg_test_state.lock() {
            state.update(
                &task_id,
                alg_test_progress_payload(
                    Some(&task_id),
                    "运行中",
                    done,
                    total,
                    errors,
                    skipped,
                    &message,
                    false,
                    started_at,
                    Some(&run_options),
                    &summary,
                ),
                false,
            );
        }
    }

    if let Ok(mut state) = alg_test_state.lock() {
        state.update(
            &task_id,
            alg_test_progress_payload(
                Some(&task_id),
                "完成",
                total,
                total,
                errors,
                skipped,
                &format!("处理完成，共 {total} 张"),
                true,
                started_at,
                Some(&run_options),
                &summary,
            ),
            true,
        );
    }
}

fn run_alg_test_external_command(
    command: ExternalCommandInvocation,
    run_options: &AlgTestRunOptions,
) -> Result<String, String> {
    let output = Command::new(&command.executable)
        .args(&command.args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|error| format!("无法启动算法测试执行器: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let details = format!("stdout={stdout}\nstderr={stderr}").trim().to_string();
        return Err(format!(
            "外部算法测试执行器失败 {}: {}",
            output.status.code().unwrap_or(-1),
            details
        ));
    }

    if let Ok(stdout) = String::from_utf8(output.stdout.clone()) {
        let lines = stdout
            .lines()
            .filter_map(|line| {
                let line = line.trim();
                if line.is_empty() {
                    None
                } else {
                    Some(line.to_string())
                }
            })
            .collect::<Vec<_>>();
        if let Some(last_line) = lines.last() {
            return Ok(last_line.clone());
        }
    }

    Ok(format!(
        "算法测试执行完成: {} [{}]",
        run_options.model,
        run_options.model_type
    ))
}

async fn search_coil_state(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.coil_states(coil_id).await?;
    Ok(Json(Value::Array(
        rows.iter().map(coil_state_to_python_json).collect(),
    ))
    .into_response())
}

async fn search_plc_data(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let body = state
        .repository
        .plc_data(coil_id)
        .await?
        .map(|row| plc_data_to_python_json(&row))
        .unwrap_or(Value::Null);
    Ok(Json(body).into_response())
}

async fn plc_curve(
    State(state): State<ApiState>,
    Path(field): Path<String>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Result<Response, ApiError> {
    let query = match parse_plc_curve_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return Ok(response),
    };
    if !matches!(
        field.as_str(),
        "location_S" | "location_L" | "location_laser"
    ) {
        return Ok(Json(json!({
            "field": field,
            "items": [],
            "error": "invalid field",
        }))
        .into_response());
    }

    let rows = state
        .repository
        .plc_curve_rows(
            query.start_id.unwrap_or_default(),
            query.end_id.unwrap_or_default(),
            query.limit.unwrap_or(200),
        )
        .await?;
    Ok(Json(json!({
        "field": field,
        "items": rows
            .iter()
            .map(|row| plc_curve_item_to_python_json(row, &field))
            .collect::<Vec<_>>(),
    }))
    .into_response())
}

async fn plc_curve_all(
    State(state): State<ApiState>,
    Query(raw_query): Query<HashMap<String, String>>,
) -> Result<Response, ApiError> {
    let query = match parse_plc_curve_query(&raw_query) {
        Ok(query) => query,
        Err(response) => return Ok(response),
    };
    let rows = state
        .repository
        .plc_curve_all(
            query.start_id.unwrap_or_default(),
            query.end_id.unwrap_or_default(),
            query.limit.unwrap_or(200),
        )
        .await?;
    Ok(Json(json!({
        "items": rows
            .iter()
            .map(plc_curve_all_item_to_python_json)
            .collect::<Vec<_>>(),
    }))
    .into_response())
}

async fn get_point_data(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.point_data(coil_id, &surface).await?;
    Ok(Json(Value::Array(
        rows.iter().map(point_data_to_python_json).collect(),
    ))
    .into_response())
}

async fn get_line_data(
    State(state): State<ApiState>,
    Path((coil_id, surface)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let rows = state.repository.line_data(coil_id, &surface).await?;
    Ok(Json(Value::Array(
        rows.iter().map(line_data_to_python_json).collect(),
    ))
    .into_response())
}

async fn get_coil_status(
    State(state): State<ApiState>,
    Path(coil_id): Path<String>,
) -> Result<Response, ApiError> {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return Ok(response),
    };
    let body = state
        .repository
        .coil_check(coil_id)
        .await?
        .map(|row| coil_check_to_python_json(&row))
        .unwrap_or_else(|| default_coil_check_json(coil_id));
    Ok(Json(body).into_response())
}

async fn set_coil_status_without_msg(
    State(state): State<ApiState>,
    Path((coil_id, status)): Path<(String, String)>,
) -> Result<Response, ApiError> {
    let (coil_id, status) = match parse_coil_check_path(&coil_id, &status) {
        Ok(values) => values,
        Err(response) => return Ok(response),
    };
    set_coil_status_value(state, coil_id, status, "").await
}

async fn set_coil_status_with_msg(
    State(state): State<ApiState>,
    Path((coil_id, status, msg)): Path<(String, String, String)>,
) -> Result<Response, ApiError> {
    let (coil_id, status) = match parse_coil_check_path(&coil_id, &status) {
        Ok(values) => values,
        Err(response) => return Ok(response),
    };
    set_coil_status_value(state, coil_id, status, &msg).await
}

fn parse_coil_check_path(coil_id: &str, status: &str) -> Result<(i64, i32), Response> {
    let coil_id = parse_python_int_converter_path(coil_id)?;
    let status = parse_python_int_converter_path(status)?;
    Ok((coil_id, status.min(i64::from(i32::MAX)) as i32))
}

async fn set_coil_status_value(
    state: ApiState,
    coil_id: i64,
    status: i32,
    msg: &str,
) -> Result<Response, ApiError> {
    state
        .repository
        .set_coil_check(coil_id, status, msg)
        .await?;
    Ok(Json(Value::Null).into_response())
}

struct ApiError(anyhow::Error);

impl<E> From<E> for ApiError
where
    E: Into<anyhow::Error>,
{
    fn from(error: E) -> Self {
        Self(error.into())
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let body = Json(json!({
            "error": self.0.to_string(),
        }));
        (StatusCode::INTERNAL_SERVER_ERROR, body).into_response()
    }
}

struct RenderedImage {
    bytes: Vec<u8>,
    content_type: &'static str,
    thumbnail: bool,
    colormap: String,
    from_cache: bool,
}

impl RenderedImage {
    fn placeholder(thumbnail: bool, colormap: &str) -> Self {
        Self {
            bytes: PLACEHOLDER_JPEG.to_vec(),
            content_type: "image/jpeg",
            thumbnail,
            colormap: colormap.to_string(),
            from_cache: false,
        }
    }
}

impl IntoResponse for RenderedImage {
    fn into_response(self) -> Response {
        let mut response = Response::new(axum::body::Body::from(self.bytes));
        let headers = response.headers_mut();
        headers.insert(
            header::CONTENT_TYPE,
            self.content_type.parse().expect("content type"),
        );
        headers.insert(
            "X-Thumbnail",
            self.thumbnail
                .to_string()
                .parse()
                .expect("thumbnail header"),
        );
        headers.insert(
            "X-Colormap",
            self.colormap.parse().expect("colormap header"),
        );
        headers.insert(
            "X-From-Cache",
            self.from_cache.to_string().parse().expect("cache header"),
        );
        response
    }
}

const PLACEHOLDER_JPEG: &[u8] = &[0xff, 0xd8, 0xff, 0xdb, 0x00, 0x43, 0x00, 0xff, 0xd9];

fn default_project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .unwrap_or_else(|| FsPath::new(env!("CARGO_MANIFEST_DIR")))
        .to_path_buf()
}

fn default_testdata_dir(project_root: &FsPath, coil_id: i64) -> PathBuf {
    let generated_dir = project_root
        .join("TestData")
        .join("to")
        .join(coil_id.to_string());
    if generated_dir.exists() {
        return generated_dir;
    }
    let legacy_dir = project_root.join("TestData").join(coil_id.to_string());
    if legacy_dir.exists() {
        return legacy_dir;
    }
    generated_dir
}

fn env_flag(name: &str) -> bool {
    std::env::var(name)
        .map(|value| {
            matches!(
                value.to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(false)
}

fn database_url_info() -> Value {
    let raw = std::env::var(DATABASE_URL_ENV).unwrap_or_default();
    let Ok(url) = Url::parse(&raw) else {
        return json!([]);
    };
    let query = url
        .query_pairs()
        .map(|(key, value)| (key.to_string(), Value::String(value.to_string())))
        .collect::<serde_json::Map<String, Value>>();
    json!([
        url.scheme(),
        url.username(),
        url.password().unwrap_or(""),
        url.host_str().unwrap_or(""),
        url.port().unwrap_or(3306),
        url.path().trim_start_matches('/'),
        query,
    ])
}

fn download_test_file_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_DOWNLOAD_TEST_FILE") {
        return PathBuf::from(path);
    }
    let project_root = default_project_root();
    let python_server_cwd_path = project_root
        .join("app")
        .join("Server")
        .join("test")
        .join("zipdir.zip");
    if python_server_cwd_path.exists() {
        return python_server_cwd_path;
    }
    project_root.join("test").join("zipdir.zip")
}

fn round_2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

fn parse_multipart_file_upload(headers: &HeaderMap, body: &Bytes) -> Option<(String, usize)> {
    let boundary = multipart_boundary(headers)?;
    let delimiter = format!("--{boundary}");
    let body = body.as_ref();
    let mut part_start = find_bytes(body, delimiter.as_bytes())? + delimiter.len();
    if body.get(part_start..part_start + 2) == Some(b"\r\n") {
        part_start += 2;
    }

    let headers_end = find_bytes(&body[part_start..], b"\r\n\r\n")?;
    let header_text = String::from_utf8_lossy(&body[part_start..part_start + headers_end]);
    let filename = multipart_filename(&header_text).unwrap_or_else(|| "file".to_string());
    let data_start = part_start + headers_end + 4;
    let end_marker = format!("\r\n--{boundary}");
    let data_len = find_bytes(&body[data_start..], end_marker.as_bytes())?;
    Some((filename, data_len))
}

fn multipart_boundary(headers: &HeaderMap) -> Option<String> {
    headers
        .get(header::CONTENT_TYPE)?
        .to_str()
        .ok()?
        .split(';')
        .map(str::trim)
        .find_map(|part| part.strip_prefix("boundary="))
        .map(|value| value.trim_matches('"').to_string())
        .filter(|value| !value.is_empty())
}

fn multipart_filename(header_text: &str) -> Option<String> {
    let disposition = header_text.lines().find(|line| {
        line.split_once(':')
            .map(|(name, _)| name.trim().eq_ignore_ascii_case("content-disposition"))
            .unwrap_or(false)
    })?;
    let (_, value) = disposition.split_once(':')?;
    let mut filename = None;
    for part in value.split(';').map(str::trim) {
        if let Some(value) = part.strip_prefix("filename*=") {
            filename = decode_multipart_filename_star(value).or(filename);
        } else if let Some(value) = part.strip_prefix("filename=") {
            filename = clean_multipart_filename(value).or(filename);
        }
    }
    filename.filter(|value| !value.is_empty())
}

fn clean_multipart_filename(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }
    if let Some(stripped) = trimmed
        .strip_prefix('"')
        .and_then(|value| value.strip_suffix('"'))
    {
        return Some(stripped.replace("\\\"", "\""));
    }
    Some(trimmed.to_string())
}

fn decode_multipart_filename_star(value: &str) -> Option<String> {
    let trimmed = value.trim_matches('"');
    let encoded = trimmed
        .split_once("''")
        .map(|(_, encoded)| encoded)
        .unwrap_or(trimmed);
    percent_decode_utf8(encoded).or_else(|| clean_multipart_filename(encoded))
}

fn percent_decode_utf8(value: &str) -> Option<String> {
    let bytes = value.as_bytes();
    let mut decoded = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' && index + 2 < bytes.len() {
            let hex = std::str::from_utf8(&bytes[index + 1..index + 3]).ok()?;
            let byte = u8::from_str_radix(hex, 16).ok()?;
            decoded.push(byte);
            index += 3;
        } else {
            decoded.push(bytes[index]);
            index += 1;
        }
    }
    String::from_utf8(decoded).ok()
}

fn find_bytes(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() {
        return Some(0);
    }
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

fn control_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_CONTROL_CONFIG") {
        return PathBuf::from(path);
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        return PathBuf::from(config_dir)
            .join("configs")
            .join("Control.json");
    }

    let production_path = PathBuf::from(r"D:\CONFIG_3D\configs\Control.json");
    if production_path.exists() {
        return production_path;
    }
    default_project_root()
        .join("CONFIG_3D")
        .join("configs")
        .join("Control.json")
}

fn read_control_config() -> Value {
    read_json_value(&control_config_path()).unwrap_or_else(|| json!({}))
}

fn defect_classes_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_DEFECT_CLASSES_CONFIG") {
        return PathBuf::from(path);
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        return PathBuf::from(config_dir)
            .join("configs")
            .join("DefectClasses.json");
    }

    let production_path = PathBuf::from(r"D:\CONFIG_3D\configs\DefectClasses.json");
    if production_path.exists() {
        return production_path;
    }
    default_project_root()
        .join("CONFIG_3D")
        .join("configs")
        .join("DefectClasses.json")
}

fn info_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_INFO_CONFIG") {
        return PathBuf::from(path);
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        return PathBuf::from(config_dir).join("configs").join("Info.json");
    }

    let production_path = PathBuf::from(r"D:\CONFIG_3D\configs\Info.json");
    if production_path.exists() {
        return production_path;
    }
    default_project_root()
        .join("CONFIG_3D")
        .join("configs")
        .join("Info.json")
}

fn plc_server_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_PLC_SERVER_CONFIG") {
        return PathBuf::from(path);
    }
    if let Ok(path) = std::env::var("PLC_SERVER_CONFIG") {
        return PathBuf::from(path);
    }
    PathBuf::from("PclServerConfig.json")
}

fn capture_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("RUST_API_CAPTURE_CONFIG") {
        return PathBuf::from(path);
    }
    if let Ok(config_dir) = std::env::var("CONFIG_3D_DIR") {
        let capture_dir = PathBuf::from(config_dir).join("capture_config");
        let local_path = capture_dir.join("CapTureLoc.json");
        if local_path.exists() {
            return local_path;
        }
        return capture_dir.join("CapTure.json");
    }

    let production_dir = PathBuf::from(r"D:\CONFIG_3D\capture_config");
    let production_local_path = production_dir.join("CapTureLoc.json");
    if production_local_path.exists() {
        return production_local_path;
    }
    let production_path = production_dir.join("CapTure.json");
    if production_path.exists() {
        return production_path;
    }

    let repo_dir = default_project_root()
        .join("CONFIG_3D")
        .join("capture_config");
    let repo_local_path = repo_dir.join("CapTureLoc.json");
    if repo_local_path.exists() {
        return repo_local_path;
    }
    repo_dir.join("CapTure.json")
}

fn server_config_path() -> PathBuf {
    default_server_config_path()
}

fn capture_config() -> Value {
    read_json_value(&capture_config_path()).unwrap_or_else(|| json!({"camera": []}))
}

fn capture_cameras() -> Vec<Value> {
    capture_config()
        .get("camera")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default()
}

fn camera_data_keys() -> HashSet<String> {
    let mut keys = HashSet::new();
    let Some(config) = read_json_value(&server_config_path()) else {
        return keys;
    };
    let Some(surfaces) = config.get("surface").and_then(Value::as_array) else {
        return keys;
    };

    for surface in surfaces {
        let Some(folders) = surface.get("folderList").and_then(Value::as_array) else {
            continue;
        };
        for folder in folders {
            let source = folder.get("source").and_then(Value::as_str).unwrap_or("");
            let key = folder
                .get("cameraKey")
                .and_then(Value::as_str)
                .unwrap_or_else(|| path_last_segment(source));
            if !key.trim().is_empty() {
                keys.insert(key.to_string());
            }
        }
    }
    keys
}

fn capture_cameras_match_camera_data(cameras: &[Value]) -> bool {
    let keys = camera_data_keys();
    cameras.iter().any(|camera| {
        camera
            .get("key")
            .and_then(Value::as_str)
            .is_some_and(|key| keys.contains(key))
    })
}

fn capture_cameras_look_like_local_placeholders(cameras: &[Value]) -> bool {
    cameras.iter().all(|camera| {
        let key = camera.get("key").and_then(Value::as_str).unwrap_or("");
        let name = camera.get("name").and_then(Value::as_str).unwrap_or("");
        key.starts_with("camera") || name.starts_with("Camera ")
    })
}

fn server_camera_data_cameras() -> Vec<Value> {
    let Some(config) = read_json_value(&server_config_path()) else {
        return Vec::new();
    };
    let Some(surfaces) = config.get("surface").and_then(Value::as_array) else {
        return Vec::new();
    };

    let mut cameras = Vec::new();
    for surface in surfaces {
        let Some(folders) = surface.get("folderList").and_then(Value::as_array) else {
            continue;
        };
        for folder in folders {
            let source = folder.get("source").and_then(Value::as_str).unwrap_or("");
            let key = folder
                .get("cameraKey")
                .and_then(Value::as_str)
                .unwrap_or_else(|| path_last_segment(source));
            if key.trim().is_empty() {
                continue;
            }
            cameras.push(json!({
                "key": key,
                "name": key,
                "source": source,
            }));
        }
    }
    cameras
}

fn capture_service_base_url() -> String {
    let config = capture_config();
    let host = normalize_service_host(
        config
            .get("apiServerIp")
            .and_then(Value::as_str)
            .unwrap_or("127.0.0.1"),
    );
    let port = config
        .get("apiServerPort")
        .and_then(Value::as_i64)
        .unwrap_or(6100);
    format!("http://{host}:{port}")
}

fn normalize_service_host(host: &str) -> String {
    match host {
        "" | "0.0.0.0" | "::" => "127.0.0.1".to_string(),
        value => value.to_string(),
    }
}

async fn capture_status_value_uncached() -> Value {
    let result = capture_service_get("/capture/status", CAPTURE_STATUS_TIMEOUT).await;
    let has_cameras = result
        .get("cameras")
        .and_then(Value::as_array)
        .is_some_and(|items| !items.is_empty());
    if result.get("ok").and_then(Value::as_bool) != Some(false) || has_cameras {
        return result;
    }

    let cameras = capture_cameras();
    let camera_items: Vec<Value> = cameras
        .iter()
        .map(camera_capture_item)
        .collect();
    let mut status = result;
    if let Some(object) = status.as_object_mut() {
        object.insert("service".to_string(), json!("CapAll"));
        object.insert(
            "configFile".to_string(),
            json!(capture_config_path().to_string_lossy()),
        );
        object.insert(
            "serviceUrl".to_string(),
            json!(format!("{}/capture/status", capture_service_base_url())),
        );
        object.insert(
            "cameras".to_string(),
            Value::Array(camera_items),
        );
    }
    status
}

fn camera_public_info(camera: &Value) -> serde_json::Map<String, Value> {
    let capture_service_url = capture_service_base_url();
    let legacy_service_url = legacy_camera_service_base_url(camera).unwrap_or_default();
    let mut info = serde_json::Map::new();
    info.insert("key".to_string(), json!(camera_string(camera, "key")));
    info.insert("name".to_string(), json!(camera_string(camera, "name")));
    info.insert("sn".to_string(), json!(camera_string(camera, "sn")));
    info.insert(
        "serverIp".to_string(),
        json!(camera_string(camera, "serverIp")),
    );
    info.insert(
        "serverPort".to_string(),
        camera
            .get("serverPort")
            .cloned()
            .unwrap_or_else(|| json!(0)),
    );
    info.insert(
        "yamlConfig".to_string(),
        json!(camera_string(camera, "yaml_config")),
    );
    info.insert("serviceUrl".to_string(), json!(capture_service_url));
    info.insert("legacyServiceUrl".to_string(), json!(legacy_service_url));
    info
}

fn camera_capture_item(camera: &Value) -> Value {
    let mut item = camera_public_info(camera);
    item.insert("status".to_string(), offline_capture_camera_status(camera));
    Value::Object(item)
}

fn camera_adjust_item_with_status(camera: &Value, status: Value) -> Value {
    let mut item = camera_public_info(camera);
    let status_2d = status
        .get("camera2D")
        .cloned()
        .unwrap_or_else(|| status.clone());
    let mut public_status = match status_2d {
        Value::Object(object) => object,
        _ => serde_json::Map::new(),
    };
    public_status.insert("capture".to_string(), status.clone());
    public_status.insert(
        "lastFrameAge3D".to_string(),
        status.get("lastFrameAge3D").cloned().unwrap_or(Value::Null),
    );
    public_status.insert(
        "lastError3D".to_string(),
        status
            .get("lastError3D")
            .cloned()
            .unwrap_or_else(|| json!("")),
    );
    item.insert("status".to_string(), Value::Object(public_status));
    Value::Object(item)
}

fn camera_alarm_item_with_status(camera: &Value, status: &Value) -> Value {
    let status_2d = status.get("camera2D").unwrap_or(status);
    let connected = status_2d
        .get("connected")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let ok = status_2d
        .get("ok")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let mut message = status_2d
        .get("message")
        .and_then(Value::as_str)
        .or_else(|| status.get("lastError3D").and_then(Value::as_str))
        .or_else(|| status.get("message").and_then(Value::as_str))
        .unwrap_or("")
        .to_string();
    let last_frame_age = status_2d
        .get("lastFrameAge")
        .cloned()
        .or_else(|| status.get("lastFrameAge2D").cloned())
        .unwrap_or(Value::Null);
    let mut level = 1;
    if !status
        .get("serviceReady")
        .and_then(Value::as_bool)
        .unwrap_or(true)
    {
        level = 2;
        if message.is_empty() {
            message = "采集服务正在初始化".to_string();
        }
    }
    if status.get("cap2D").and_then(Value::as_bool).unwrap_or(true) && !ok {
        level = 3;
        if message.is_empty() {
            message = "2D相机采集异常".to_string();
        }
    }
    if status.get("cap3D").and_then(Value::as_bool).unwrap_or(true)
        && status
            .get("lastError3D")
            .and_then(Value::as_str)
            .is_some_and(|value| !value.is_empty())
    {
        level = 3;
        message = status
            .get("lastError3D")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
    }
    json!({
        "DeviceTemperature": status_2d.get("DeviceTemperature").cloned().unwrap_or_else(|| json!(0)),
        "level": level,
        "msg": if message.is_empty() { "采集正常".to_string() } else { message },
        "connected": connected,
        "ok": ok && level == 1,
        "captureOk": level == 1,
        "lastFrameAge": last_frame_age,
        "lastError2D": status.get("lastError2D").cloned().unwrap_or_else(|| json!("")),
        "lastError3D": status.get("lastError3D").cloned().unwrap_or_else(|| json!("")),
        "serviceUrl": capture_service_base_url(),
        "cameraKey": camera_string(camera, "key"),
        "cameraName": camera_string(camera, "name"),
    })
}

fn offline_camera_status(camera: &Value) -> Value {
    let key = camera_string(camera, "key");
    json!({
        "ok": false,
        "connected": false,
        "message": "capture service unavailable",
        "serviceUrl": format!("{}/cameras/{key}/status", capture_service_base_url()),
    })
}

fn offline_capture_camera_status(camera: &Value) -> Value {
    let key = camera_string(camera, "key");
    json!({
        "ok": false,
        "connected": false,
        "message": "capture service unavailable",
        "serviceUrl": format!("{}/cameras/{key}/status", capture_service_base_url()),
    })
}

fn legacy_camera_service_base_url(camera: &Value) -> Option<String> {
    let port = camera.get("serverPort").and_then(Value::as_i64)?;
    let host = normalize_service_host(
        camera
            .get("serverIp")
            .and_then(Value::as_str)
            .unwrap_or("127.0.0.1"),
    );
    Some(format!("http://{host}:{port}"))
}

fn camera_string(camera: &Value, key: &str) -> String {
    camera
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

enum CameraPostAction {
    Params,
    Reconnect,
}

impl CameraPostAction {
    fn path(&self, camera_key: &str) -> String {
        match self {
            Self::Params => format!("/cameras/{camera_key}/params"),
            Self::Reconnect => format!("/cameras/{camera_key}/reconnect"),
        }
    }
}

fn api_http_client() -> &'static reqwest::Client {
    static CLIENT: OnceLock<reqwest::Client> = OnceLock::new();
    CLIENT.get_or_init(reqwest::Client::new)
}

async fn capture_service_get(path: &str, timeout: Duration) -> Value {
    let url = format!("{}{}", capture_service_base_url(), path);
    let response = match api_http_client().get(&url).timeout(timeout).send().await {
        Ok(response) => response,
        Err(error) => {
            return json!({
                "ok": false,
                "message": error.to_string(),
                "serviceUrl": url,
            });
        }
    };
    let status = response.status();
    let body = match response.text().await {
        Ok(body) => body,
        Err(error) => {
            return json!({
                "ok": false,
                "message": error.to_string(),
                "serviceUrl": url,
            });
        }
    };
    if !status.is_success() {
        return json!({
            "ok": false,
            "message": format!("{}: {}", status.as_u16(), body),
            "serviceUrl": url,
        });
    }
    serde_json::from_str::<Value>(&body).unwrap_or_else(|error| {
        json!({
            "ok": false,
            "message": format!("响应解析失败: {error}"),
            "serviceUrl": url,
        })
    })
}

async fn fetch_missing_camera_statuses(
    cameras: &[Value],
    status_by_key: &HashMap<String, Value>,
) -> HashMap<String, Value> {
    let mut tasks = Vec::new();
    for camera in cameras {
        let key = camera_string(camera, "key");
        if key.is_empty() || status_by_key.contains_key(&key) {
            continue;
        }
        let camera = camera.clone();
        tasks.push(tokio::spawn(async move {
            let status = camera_service_get(&camera, "/camera/status").await;
            (key, status)
        }));
    }

    let mut statuses = HashMap::new();
    for task in tasks {
        if let Ok((key, status)) = task.await {
            statuses.insert(key, status);
        }
    }
    statuses
}

async fn camera_service_get(camera: &Value, path: &str) -> Value {
    let key = camera_string(camera, "key");
    let url = if path == "/camera/status" {
        format!("{}/cameras/{key}/status", capture_service_base_url())
    } else {
        format!("{}{}", capture_service_base_url(), path)
    };
    let response = match api_http_client()
        .get(&url)
        .timeout(CAMERA_STATUS_TIMEOUT)
        .send()
        .await
    {
        Ok(response) => response,
        Err(error) => return camera_status_error(camera, &url, error.to_string()),
    };
    let status = response.status();
    let body = match response.text().await {
        Ok(body) => body,
        Err(error) => return camera_status_error(camera, &url, error.to_string()),
    };
    if !status.is_success() {
        return camera_status_error(camera, &url, format!("{}: {}", status.as_u16(), body));
    }
    serde_json::from_str::<Value>(&body)
        .unwrap_or_else(|error| camera_status_error(camera, &url, format!("响应解析失败: {error}")))
}

fn camera_status_error(camera: &Value, url: &str, message: String) -> Value {
    let mut status = offline_camera_status(camera);
    if let Some(object) = status.as_object_mut() {
        object.insert("message".to_string(), json!(message));
        object.insert("serviceUrl".to_string(), json!(url));
    }
    status
}

async fn camera_service_post(
    camera_key: &str,
    action: CameraPostAction,
    payload: Value,
) -> Response {
    if find_capture_camera(camera_key).is_none() {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({"detail": format!("未找到相机: {camera_key}")})),
        )
            .into_response();
    }

    let url = format!("{}{}", capture_service_base_url(), action.path(camera_key));
    let response = match api_http_client()
        .post(&url)
        .json(&payload)
        .timeout(CAMERA_STATUS_TIMEOUT)
        .send()
        .await
    {
        Ok(response) => response,
        Err(error) => return camera_bad_gateway(error.to_string()),
    };
    let status = response.status();
    let body = match response.text().await {
        Ok(body) => body,
        Err(error) => return camera_bad_gateway(error.to_string()),
    };
    if !status.is_success() {
        return camera_bad_gateway(format!("{}: {}", status.as_u16(), body));
    }
    match serde_json::from_str::<Value>(&body) {
        Ok(value) => Json(value).into_response(),
        Err(error) => camera_bad_gateway(format!("响应解析失败: {error}")),
    }
}

fn camera_bad_gateway(detail: String) -> Response {
    (StatusCode::BAD_GATEWAY, Json(json!({"detail": detail}))).into_response()
}

fn find_capture_camera(camera_key: &str) -> Option<Value> {
    capture_cameras().into_iter().find(|camera| {
        camera
            .get("key")
            .and_then(Value::as_str)
            .is_some_and(|key| key == camera_key)
    })
}

fn camera_data_value(coil_id: i64, camera_key: &str) -> Option<Value> {
    let config = read_json_value(&server_config_path())?;
    let surfaces = config.get("surface")?.as_array()?;
    for surface in surfaces {
        let surface_key = surface.get("key").and_then(Value::as_str).unwrap_or("");
        let folders = surface.get("folderList").and_then(Value::as_array)?;
        for folder in folders {
            let source = folder.get("source").and_then(Value::as_str).unwrap_or("");
            let folder_camera_key = folder
                .get("cameraKey")
                .and_then(Value::as_str)
                .unwrap_or_else(|| path_last_segment(source));
            if folder_camera_key != camera_key {
                continue;
            }
            let mut item = folder.as_object().cloned().unwrap_or_default();
            item.insert("cameraKey".to_string(), json!(camera_key));
            item.insert("coilId".to_string(), json!(coil_id));
            item.insert("surface".to_string(), json!(surface_key));
            item.insert("source".to_string(), json!(source));
            item.insert(
                "folder".to_string(),
                json!(join_windows_path_text(source, &coil_id.to_string())),
            );
            return Some(Value::Object(item));
        }
    }
    None
}

fn path_last_segment(path: &str) -> &str {
    path.rsplit(['\\', '/']).next().unwrap_or(path)
}

fn join_windows_path_text(base: &str, child: &str) -> String {
    let separator = if base.ends_with('\\') || base.ends_with('/') {
        ""
    } else {
        "\\"
    };
    format!("{base}{separator}{child}")
}

fn next_text_for_weight(weight: Option<f64>) -> String {
    let code = match weight {
        Some(value) => char::from_u32(value as u32)
            .map(|ch| ch.to_string())
            .unwrap_or_else(|| (value as i64).to_string()),
        None => "None".to_string(),
    };
    read_json_value(&info_config_path())
        .and_then(|value| {
            value
                .get("nextDict")
                .and_then(Value::as_object)
                .and_then(|items| items.get(&code))
                .and_then(Value::as_str)
                .map(ToString::to_string)
        })
        .unwrap_or_else(|| default_next_text(&code))
}

fn default_next_text(code: &str) -> String {
    match code {
        "0" => "VAMA".to_string(),
        "1" => "商品材".to_string(),
        "2" => "冷轧基板".to_string(),
        "4" => "横切".to_string(),
        "7" => "外委横切(配送)".to_string(),
        "G" => "2250 平整".to_string(),
        other => format!("未知代码 {other}"),
    }
}

fn default_defect_dict() -> Value {
    json!({
        "data": {},
        "default": {
            "level": 4,
            "color": "#FFA500",
            "show": true,
        }
    })
}

fn hardware_info_uncached() -> Value {
    let mut system = System::new_all();
    system.refresh_all();
    system.refresh_cpu_usage();
    system.refresh_memory();

    json!({
        "cpu": cpu_info(&system),
        "memory": memory_info(&system),
        "disk": disk_info(),
        "gpu": gpu_info(),
    })
}

fn level_from_percent(percent: f64) -> i32 {
    if percent > 90.0 {
        3
    } else if percent > 70.0 {
        2
    } else {
        1
    }
}

fn format_percent(value: f64, decimals: usize) -> String {
    format!("{value:.decimals$}%")
}

fn bytes_to_gb(value: u64) -> f64 {
    value as f64 / 1024.0 / 1024.0 / 1024.0
}

fn bytes_to_mb(value: u64) -> f64 {
    value as f64 / 1024.0 / 1024.0
}

fn cpu_info(system: &System) -> Value {
    let cpu_usage = system.global_cpu_usage() as f64;
    let cpu_value = format_percent(cpu_usage, 1);
    json!({
        "key": "CPU",
        "value": cpu_value,
        "msg": format!("CPU 使用率: {cpu_value}"),
        "level": level_from_percent(cpu_usage),
    })
}

fn memory_info(system: &System) -> Value {
    let total = system.total_memory();
    let available = system.available_memory();
    let percent = if total > 0 {
        (total.saturating_sub(available)) as f64 / total as f64 * 100.0
    } else {
        0.0
    };
    let memory_value = format_percent(percent, 1);
    json!({
        "key": "内存",
        "value": memory_value,
        "msg": format!("内存使用率: {memory_value}, 可用内存: {:.2} MB", bytes_to_mb(available)),
        "level": level_from_percent(percent),
    })
}

fn disk_info() -> Value {
    let disks = Disks::new_with_refreshed_list();
    let mut lines = Vec::new();
    let mut all_used = 0_u64;
    let mut all_total = 0_u64;

    for disk in disks.list() {
        let total = disk.total_space();
        if total == 0 {
            continue;
        }
        let available = disk.available_space();
        let used = total.saturating_sub(available);
        let percent = used as f64 / total as f64 * 100.0;
        let label = disk.mount_point().to_string_lossy();
        lines.push((
            label.to_string(),
            format!(
                "分区: {label}, 总大小: {:.2} GB, 已用: {:.2} GB, 可用: {:.2} GB, 使用率: {}",
                bytes_to_gb(total),
                bytes_to_gb(used),
                bytes_to_gb(available),
                format_percent(percent, 1)
            ),
        ));
        all_used = all_used.saturating_add(used);
        all_total = all_total.saturating_add(total);
    }
    sort_disk_status_lines_by_mount_label(&mut lines);

    let percent = if all_total > 0 {
        all_used as f64 / all_total as f64 * 100.0
    } else {
        0.0
    };

    json!({
        "key": "硬盘",
        "value": format_percent(percent, 2),
        "msg": lines
            .into_iter()
            .map(|(_, line)| line)
            .collect::<Vec<_>>()
            .join("\n"),
        "level": level_from_percent(percent),
    })
}

fn sort_disk_status_lines_by_mount_label(lines: &mut [(String, String)]) {
    lines.sort_by_key(|(label, _)| label.to_ascii_lowercase());
}

fn gpu_info() -> Value {
    let output = Command::new("nvidia-smi")
        .args([
            "--query-gpu=name,utilization.gpu",
            "--format=csv,noheader,nounits",
        ])
        .output();

    let Ok(output) = output else {
        return no_gpu_info();
    };
    if !output.status.success() {
        return no_gpu_info();
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut lines = Vec::new();
    let mut max_load = 0.0_f64;

    for line in stdout
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
    {
        let Some((name, usage_text)) = line.rsplit_once(',') else {
            continue;
        };
        let usage = usage_text.trim().parse::<f64>().unwrap_or(0.0);
        max_load = max_load.max(usage);
        lines.push(format!("显卡: {}, 使用率: {:.2}%", name.trim(), usage));
    }

    if lines.is_empty() {
        return no_gpu_info();
    }

    json!({
        "key": "显卡",
        "value": format_percent(max_load, 1),
        "msg": lines.join("\n"),
        "level": level_from_percent(max_load),
    })
}

fn no_gpu_info() -> Value {
    json!({
        "key": "显卡",
        "value": "0.0%",
        "msg": "未检测到 GPU",
        "level": 1,
    })
}

fn test_mode_config_override_path() -> Option<PathBuf> {
    std::env::var("RUST_API_TEST_MODE_CONFIG")
        .ok()
        .map(PathBuf::from)
}

fn default_test_mode_config_paths(project_root: &FsPath) -> [PathBuf; 2] {
    [
        PathBuf::from(r"D:\CONFIG_3D\test_mode_config.json"),
        project_root.join("CONFIG_3D").join("test_mode_config.json"),
    ]
}

fn test_mode_config_path(project_root: &FsPath) -> PathBuf {
    if let Some(path) = test_mode_config_override_path() {
        return path;
    }

    let paths = default_test_mode_config_paths(project_root);
    paths
        .iter()
        .find(|path| path.exists())
        .cloned()
        .unwrap_or_else(|| paths[1].clone())
}

fn config_file_test_mode_enabled(project_root: &FsPath) -> bool {
    if let Some(path) = test_mode_config_override_path() {
        return read_test_mode_config(&path).unwrap_or(false);
    }

    default_test_mode_config_paths(project_root)
        .iter()
        .any(|path| read_test_mode_config(path).unwrap_or(false))
}

fn read_test_mode_config(path: &FsPath) -> Option<bool> {
    let content = std::fs::read_to_string(path).ok()?;
    let value: Value = serde_json::from_str(&content).ok()?;
    value.get("test_mode").and_then(Value::as_bool)
}

fn relative_path_text(path: &FsPath, project_root: &FsPath) -> String {
    path.strip_prefix(project_root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn test_mode_alarm(surface: &str) -> Value {
    json!({
        "surface": surface,
        "grad": 1,
        "defectGrad": 1,
        "taperShapeGrad": 1,
        "looseCoilGrad": 1,
        "flatRollGrad": 1,
        "defectMsg": "",
        "taperShapeMsg": "测试模式",
        "looseCoilMsg": "",
        "flatRollMsg": "测试模式",
    })
}

fn runtime_coil_info(
    data_config: &DataRuntimeConfig,
    coil_id: i64,
    surface: &str,
) -> Option<Value> {
    let surface_dir = data_config.surface_asset_dir(coil_id, surface)?;
    let mut info = read_json_object(&surface_dir.join("data.json")).unwrap_or_default();
    let depth_map = data_config.depth_map(coil_id, surface);
    let (height, width) = depth_map
        .as_ref()
        .map(|map| (map.height(), map.width()))
        .unwrap_or_else(|| shape_from_info(&info));
    let median_3d = depth_map
        .as_ref()
        .map(|depth_map| depth_map.median_nonzero())
        .unwrap_or(0.0);
    let surface = surface.to_ascii_uppercase();
    let circle_config = info.get("circleConfig").cloned().unwrap_or_else(|| {
        json!({
            "inner_circle": {
                "circlex": [width / 2, height / 2],
                "ellipse": []
            }
        })
    });

    info.insert(
        "coilId".to_string(),
        info.get("coilId")
            .cloned()
            .unwrap_or_else(|| Value::String(coil_id.to_string())),
    );
    info.insert("surface".to_string(), Value::String(surface));
    info.insert("width".to_string(), json!(width));
    info.insert("height".to_string(), json!(height));
    info.insert(
        "scan3dCoordinateScaleX".to_string(),
        json!(DEFAULT_SCAN3D_SCALE_X),
    );
    info.insert(
        "scan3dCoordinateScaleY".to_string(),
        json!(DEFAULT_SCAN3D_SCALE_Y),
    );
    info.insert(
        "scan3dCoordinateScaleZ".to_string(),
        json!(DEFAULT_SCAN3D_SCALE_Z),
    );
    info.insert("scan3dCoordinateOffsetZ".to_string(), json!(0));
    info.insert("median_3d".to_string(), json!(median_3d));
    info.insert(
        "median_3d_mm".to_string(),
        json!(median_3d * DEFAULT_SCAN3D_SCALE_Z),
    );
    info.insert("colorFromValue_mm".to_string(), json!(-30));
    info.insert("colorToValue_mm".to_string(), json!(30));
    info.insert("circleConfig".to_string(), circle_config);

    Some(Value::Object(info))
}

fn height_point_value(
    state: &ApiState,
    surface: &str,
    coil_id: Option<i64>,
    x: i32,
    y: i32,
) -> Value {
    state
        .test_mode_data_fallback()
        .and_then(|test_mode| test_mode.height_point(surface, x, y))
        .or_else(|| {
            let coil_id = coil_id?;
            state
                .data_config
                .as_ref()
                .and_then(|data_config| data_config.depth_map(coil_id, surface))
                .map(|depth_map| {
                    depth_map
                        .value_i32(x, y)
                        .map_or_else(|| json!("error"), |value| json!(value))
                })
        })
        .unwrap_or_else(|| json!("error"))
}

fn ws_height_point_response(state: &ApiState, message: &str) -> Option<Value> {
    let request: Value = match serde_json::from_str(message) {
        Ok(value) => value,
        Err(_) => {
            return None;
        }
    };

    let req_id = request.get("id").cloned().unwrap_or(Value::Null);
    let surface_key = request
        .get("surface_key")
        .or_else(|| request.get("surfaceKey"))
        .and_then(value_to_non_empty_string);
    let coil_id_text = request
        .get("coil_id")
        .or_else(|| request.get("coilId"))
        .and_then(value_to_non_empty_string)
        .unwrap_or_default();
    let x = request
        .get("x")
        .map_or(Some(0), value_to_i32_like_python);
    let y = request
        .get("y")
        .map_or(Some(0), value_to_i32_like_python);
    let (x, y) = match (x, y) {
        (Some(x), Some(y)) => (x, y),
        _ => return None,
    };

    let mut response = serde_json::Map::new();
    response.insert("id".to_string(), req_id);
    response.insert(
        "surface_key".to_string(),
        surface_key
            .as_ref()
            .map_or(Value::Null, |value| Value::String(value.clone())),
    );
    response.insert("coil_id".to_string(), Value::String(coil_id_text.clone()));
    response.insert("x".to_string(), json!(x));
    response.insert("y".to_string(), json!(y));

    let Some(surface_key) = surface_key else {
        response.insert(
            "error".to_string(),
            Value::String("surface_key and coil_id are required".to_string()),
        );
        return Some(Value::Object(response));
    };
    if coil_id_text.is_empty() {
        response.insert(
            "error".to_string(),
            Value::String("surface_key and coil_id are required".to_string()),
        );
        return Some(Value::Object(response));
    }

    let Ok(coil_id) = coil_id_text.parse::<i64>() else {
        response.insert(
            "error".to_string(),
            Value::String(format!("invalid coil_id: {coil_id_text}")),
        );
        return Some(Value::Object(response));
    };
    match height_point_value(state, &surface_key, Some(coil_id), x, y) {
        Value::String(error) if error == "error" => {
            response.insert("error".to_string(), Value::String("error".to_string()));
        }
        value => {
            response.insert("value".to_string(), value);
        }
    }
    Some(Value::Object(response))
}

async fn ws_re_detection_response(state: &ApiState, message: &str) -> Option<Value> {
    let request: Value = match serde_json::from_str(message) {
        Ok(value) => value,
        Err(_) => {
            return None;
        }
    };
    let Some(from_id) = request.get("from_id").and_then(value_to_i64) else {
        return None;
    };
    let Some(to_id) = request.get("to_id").and_then(value_to_i64) else {
        return None;
    };
    Some(state.queue_re_detection(from_id, to_id).await)
}

fn read_json_object(path: &FsPath) -> Option<serde_json::Map<String, Value>> {
    let content = std::fs::read_to_string(path).ok()?;
    let value: Value = serde_json::from_str(&content).ok()?;
    value.as_object().cloned()
}

fn read_json_value(path: &FsPath) -> Option<Value> {
    let content = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn shape_from_info(info: &serde_json::Map<String, Value>) -> (i32, i32) {
    let shape = info.get("shape").and_then(Value::as_array);
    let height = shape
        .and_then(|items| items.first())
        .and_then(value_to_i32)
        .unwrap_or(0);
    let width = shape
        .and_then(|items| items.get(1))
        .and_then(value_to_i32)
        .unwrap_or(0);
    (height.max(0), width.max(0))
}

fn value_to_i32(value: &Value) -> Option<i32> {
    value
        .as_i64()
        .and_then(|number| i32::try_from(number).ok())
        .or_else(|| value.as_u64().and_then(|number| i32::try_from(number).ok()))
        .or_else(|| value.as_f64().map(|number| number as i32))
}

fn value_to_i32_like_python(value: &Value) -> Option<i32> {
    match value {
        Value::Bool(value) => Some(if *value { 1 } else { 0 }),
        Value::Number(number) => {
            number
                .as_i64()
                .and_then(|value| i32::try_from(value).ok())
                .or_else(|| number.as_u64().and_then(|number| i32::try_from(number).ok()))
                .or_else(|| number.as_f64().map(|number| number as i32))
        }
        Value::String(text) => {
            let text = text.trim();
            if text.is_empty() {
                None
            } else {
                text.parse::<i64>().ok().and_then(|value| i32::try_from(value).ok())
            }
        }
        _ => None,
    }
}

fn value_to_i64(value: &Value) -> Option<i64> {
    value
        .as_i64()
        .or_else(|| value.as_u64().and_then(|number| i64::try_from(number).ok()))
        .or_else(|| value.as_f64().map(|number| number as i64))
        .or_else(|| {
            value
                .as_str()
                .and_then(|text| text.trim().parse::<i64>().ok())
        })
}

fn value_to_non_empty_string(value: &Value) -> Option<String> {
    let text = match value {
        Value::String(text) => text.clone(),
        Value::Number(number) => number.to_string(),
        Value::Bool(value) => value.to_string(),
        _ => return None,
    };
    if text.is_empty() { None } else { Some(text) }
}

fn has_any_file(dir: &FsPath, names: &[&str]) -> bool {
    names.iter().any(|name| dir.join(name).exists())
}

fn has_named_image(surface_dir: &FsPath, name: &str) -> bool {
    ["jpg", "png"].iter().any(|folder| {
        [".jpg", ".jpeg", ".png"].iter().any(|extension| {
            surface_dir
                .join(folder)
                .join(format!("{name}{extension}"))
                .exists()
        })
    })
}

fn has_python_default_mesh(surface_dir: &FsPath) -> bool {
    surface_dir
        .join("meshes")
        .join("defaultobject_mesh.mesh")
        .exists()
}

fn find_named_image_file(dir: &FsPath, name: &str) -> Option<PathBuf> {
    [".jpg", ".jpeg", ".png"]
        .iter()
        .map(|extension| dir.join(format!("{name}{extension}")))
        .find(|path| path.exists())
}

fn content_type_for_path(path: &FsPath) -> &'static str {
    match path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase()
        .as_str()
    {
        "png" => "image/png",
        _ => "image/jpeg",
    }
}

fn image_file_path(dir: &FsPath, name: &str) -> Option<PathBuf> {
    let normalized = name.trim();
    if normalized.is_empty() {
        return None;
    }
    find_named_image_file(dir, normalized)
}

fn image_file_response(dir: &FsPath, name: &str) -> Option<Response> {
    let path = image_file_path(dir, name)?;
    fs::read(&path)
        .ok()
        .map(|bytes| bytes_response(bytes, content_type_for_path(&path)))
}

fn image_file_response_with_query(
    dir: &FsPath,
    name: &str,
    query: &ImageFileQuery,
) -> Option<Response> {
    let path = image_file_path(dir, name)?;
    image_file_response_with_query_for_path(&path, query)
}

fn image_file_response_with_query_for_path(
    path: &FsPath,
    query: &ImageFileQuery,
) -> Option<Response> {
    let endpoint = "/image/file";
    let context = path.to_string_lossy().to_string();
    if !path.exists() {
        return None;
    }

    if query.width.is_none()
        && query.height.is_none()
        && query.quality.is_none()
        && query.format.is_none()
    {
        let read_started = Instant::now();
        return fs::read(path).ok().map(|bytes| {
            profile_stage(endpoint, "read_file", read_started, &context);
            bytes_response(bytes, content_type_for_path(path))
        });
    }

    let decode_started = Instant::now();
    let source = image::open(&path).ok()?;
    profile_stage(endpoint, "decode", decode_started, &context);
    let source_width = source.width();
    let source_height = source.height();
    if source_width == 0 || source_height == 0 {
        return None;
    }

    let (target_width, target_height) =
        image_file_target_dimensions(source_width, source_height, query.width, query.height);
    let resize_started = Instant::now();
    let image = if target_width == source_width && target_height == source_height {
        source
    } else {
        source.resize(
            target_width,
            target_height,
            imageops::FilterType::Lanczos3,
        )
    };
    profile_stage(endpoint, "resize", resize_started, &context);

    let format = query.format.unwrap_or_else(|| image_file_default_format(&path));
    let quality = query.quality.unwrap_or(90);
    let encode_started = Instant::now();
    let bytes = match format {
        ImageFileFormat::Jpeg => encode_rgb_jpeg(&image.to_rgb8(), quality),
        ImageFileFormat::Png => encode_rgba_png(&image.to_rgba8()),
    }?;
    profile_stage(endpoint, "encode", encode_started, &context);

    Some(bytes_response(bytes, format.content_type()))
}

fn image_file_target_dimensions(
    source_width: u32,
    source_height: u32,
    width: Option<u32>,
    height: Option<u32>,
) -> (u32, u32) {
    match (width, height) {
        (Some(target_width), Some(target_height)) => (target_width.max(1), target_height.max(1)),
        (Some(target_width), None) => {
            let aspect = f64::from(target_width) / f64::from(source_width.max(1));
            let target_height = (f64::from(source_height) * aspect).round().max(1.0) as u32;
            (target_width.max(1), target_height.max(1))
        }
        (None, Some(target_height)) => {
            let aspect = f64::from(target_height) / f64::from(source_height.max(1));
            let target_width = (f64::from(source_width) * aspect).round().max(1.0) as u32;
            (target_width.max(1), target_height.max(1))
        }
        (None, None) => (source_width, source_height),
    }
}

fn image_file_default_format(path: &FsPath) -> ImageFileFormat {
    match path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase()
        .as_str()
    {
        "png" => ImageFileFormat::Png,
        _ => ImageFileFormat::Jpeg,
    }
}

fn area_image_file_response(dir: &FsPath, name: &str) -> Option<Response> {
    let path = image_file_path(dir, name)?;
    fs::read(&path)
        .ok()
        .map(|bytes| bytes_response(bytes, "image/jpeg"))
}

fn normalize_area_image_type(value: &str) -> String {
    match value.trim().to_ascii_uppercase().as_str() {
        "AREA_MASK" => "AREA_MASK".to_string(),
        _ => "AREA".to_string(),
    }
}

fn area_source_image_path(surface_dir: &FsPath, type_: &str) -> Option<PathBuf> {
    image_file_path(&surface_dir.join("jpg"), type_)
        .or_else(|| image_file_path(&surface_dir.join("png"), type_))
}

fn area_tile_cache_path(surface_dir: &FsPath, col: i32, row: i32, level: i32) -> Option<PathBuf> {
    if row < 0 || col < 0 {
        return None;
    }
    Some(
        surface_dir
            .join("cache")
            .join("area")
            .join("tild")
            .join(format!("L{}", level.clamp(0, 4)))
            .join(format!("{col}_{row}.jpg")),
    )
}

fn area_tile_cache_is_fresh(cache_path: &FsPath, source_path: Option<&FsPath>) -> bool {
    let Some(source_path) = source_path else {
        return true;
    };
    let Ok(cache_metadata) = fs::metadata(cache_path) else {
        return false;
    };
    let Ok(source_metadata) = fs::metadata(source_path) else {
        return true;
    };
    let Ok(cache_modified) = cache_metadata.modified() else {
        return true;
    };
    let Ok(source_modified) = source_metadata.modified() else {
        return true;
    };
    cache_modified >= source_modified
}

fn area_tile_cache_response(
    surface_dir: &FsPath,
    row: i32,
    col: i32,
    level: i32,
    source_path: Option<&FsPath>,
) -> Option<Response> {
    let path = area_tile_cache_path(surface_dir, col, row, level)?;
    if !area_tile_cache_is_fresh(&path, source_path) {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    let mut response = bytes_response(bytes, "image/jpeg");
    response.headers_mut().insert(
        "X-Tile-Level",
        level
            .clamp(0, 4)
            .to_string()
            .parse()
            .expect("tile level header"),
    );
    response
        .headers_mut()
        .insert("X-Cache", "hit".parse().expect("cache header"));
    Some(response)
}

fn area_l4_tile_cache_miss_response(
    surface_dir: &FsPath,
    row: i32,
    col: i32,
    level: i32,
    source_path: Option<&FsPath>,
) -> Option<Response> {
    if level >= 4 || row < 0 || col < 0 {
        return None;
    }
    for cache_row in 0..3 {
        for cache_col in 0..3 {
            let cache_path = area_tile_cache_path(surface_dir, cache_col, cache_row, 4)?;
            if !area_tile_cache_is_fresh(&cache_path, source_path) {
                return None;
            }
        }
    }
    let l4_path = area_tile_cache_path(surface_dir, col, row, 4)?;
    let tile = image::open(l4_path).ok()?.to_luma8();
    let level_tile = resize_area_tile_for_level(&tile, level);
    let bytes = encode_luma_jpeg(&level_tile, area_tile_jpeg_quality(level))?;
    let mut response = bytes_response(bytes, "image/jpeg");
    response.headers_mut().insert(
        "X-Tile-Level",
        level
            .clamp(0, 4)
            .to_string()
            .parse()
            .expect("tile level header"),
    );
    response
        .headers_mut()
        .insert("X-Cache", "miss".parse().expect("cache header"));
    Some(response)
}

fn write_area_tile_cache_bytes(
    surface_dir: &FsPath,
    row: i32,
    col: i32,
    level: i32,
    bytes: &[u8],
) -> std::io::Result<()> {
    let Some(path) = area_tile_cache_path(surface_dir, col, row, level) else {
        return Ok(());
    };
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, bytes)
}

fn write_area_l4_tile_cache_from_source(surface_dir: &FsPath, path: &FsPath, count: i32) {
    if count <= 1 {
        return;
    }
    let Ok(source) = image::open(path) else {
        return;
    };
    let source = source.to_luma8();
    for row in 0..count {
        for col in 0..count {
            let Some(tile) = crop_area_tile_from_source(&source, row, col, count) else {
                continue;
            };
            let Some(bytes) = encode_luma_jpeg(&tile, area_tile_jpeg_quality(4)) else {
                continue;
            };
            let _ = write_area_tile_cache_bytes(surface_dir, row, col, 4, &bytes);
        }
    }
}

fn area_tile_cache_metadata(
    surface_dir: &FsPath,
    source_path: Option<&FsPath>,
) -> Option<(u32, u32)> {
    let path = area_tile_cache_path(surface_dir, 0, 0, 4)?;
    if !area_tile_cache_is_fresh(&path, source_path) {
        return None;
    }
    let image = image::open(path).ok()?;
    let width = image.width();
    let height = image.height();
    if width == 0 || height == 0 {
        return None;
    }
    Some((width * 3, height * 3))
}

fn crop_image_area_tile(path: &FsPath, row: i32, col: i32, count: i32) -> Option<GrayImage> {
    let source = image::open(path).ok()?.to_luma8();
    crop_area_tile_from_source(&source, row, col, count)
}

fn crop_area_tile_from_source(
    source: &GrayImage,
    row: i32,
    col: i32,
    count: i32,
) -> Option<GrayImage> {
    if row < 0 || col < 0 || count <= 1 {
        return None;
    }
    let count = count as u32;
    let tile_width = source.width() / count;
    let tile_height = source.height() / count;
    if tile_width == 0 || tile_height == 0 {
        return None;
    }
    // Python's legacy MemoryImageCache fallback slices with row on the x-axis
    // and col on the y-axis. Keep that quirk for uncached AREA tile parity.
    let x = row as u32 * tile_width;
    let y = col as u32 * tile_height;
    if x >= source.width() || y >= source.height() {
        return None;
    }
    let width = if row as u32 == count - 1 {
        source.width() - x
    } else {
        tile_width
    };
    let height = if col as u32 == count - 1 {
        source.height() - y
    } else {
        tile_height
    };
    Some(imageops::crop_imm(source, x, y, width, height).to_image())
}

fn area_tile_jpeg_quality(level: i32) -> u8 {
    match level {
        0 => 60,
        1 => 70,
        2 => 80,
        3 => 90,
        _ => 95,
    }
}

fn area_tile_target_size(level: i32) -> Option<u32> {
    match level {
        0 => Some(340),
        1 => Some(682),
        2 => Some(1364),
        3 => Some(2728),
        _ => None,
    }
}

fn resize_area_tile_for_level(tile: &GrayImage, level: i32) -> GrayImage {
    let Some(target_size) = area_tile_target_size(level) else {
        return tile.clone();
    };
    let max_dim = tile.width().max(tile.height());
    if max_dim == 0 || max_dim <= target_size {
        return tile.clone();
    }
    let scale = target_size as f32 / max_dim as f32;
    let width = ((tile.width() as f32) * scale).max(1.0) as u32;
    let height = ((tile.height() as f32) * scale).max(1.0) as u32;
    DynamicImage::ImageLuma8(tile.clone())
        .resize(width, height, imageops::FilterType::Lanczos3)
        .to_luma8()
}

fn cleanup_legacy_area_tile_cache_on_startup(data_config: &DataRuntimeConfig) {
    if !env_flag("CACHE_AREA_CLEANUP_ON_STARTUP") {
        return;
    }

    for save_folder in data_config.surface_save_folders() {
        let Ok(coil_dirs) = fs::read_dir(save_folder) else {
            continue;
        };
        for coil_dir in coil_dirs.flatten() {
            let Ok(file_type) = coil_dir.file_type() else {
                continue;
            };
            if !file_type.is_dir() {
                continue;
            }
            cleanup_legacy_area_tile_cache_dir(
                &coil_dir.path().join("cache").join("area").join("tild"),
            );
        }
    }
}

fn cleanup_legacy_area_tile_cache_dir(cache_dir: &FsPath) {
    let Ok(entries) = fs::read_dir(cache_dir) else {
        return;
    };
    for entry in entries.flatten() {
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if !file_type.is_file() {
            continue;
        }
        let path = entry.path();
        if is_legacy_area_tile_cache_file(&path) {
            let _ = fs::remove_file(path);
        }
    }
}

fn is_legacy_area_tile_cache_file(path: &FsPath) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case("jpg"))
        && path
            .file_stem()
            .and_then(|stem| stem.to_str())
            .is_some_and(|stem| {
                stem.contains('_') && stem.chars().all(|ch| ch == '_' || ch.is_ascii_digit())
            })
}

fn bytes_response(bytes: Vec<u8>, content_type: &'static str) -> Response {
    let mut response = Response::new(axum::body::Body::from(bytes));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        content_type.parse().expect("content type"),
    );
    response
}

fn text_response(text: &'static str, content_type: &'static str) -> Response {
    bytes_response(text.as_bytes().to_vec(), content_type)
}

fn html_response(html: &'static str) -> Response {
    text_response(html, "text/html; charset=utf-8")
}

fn placeholder_jpeg_response() -> Response {
    bytes_response(PLACEHOLDER_JPEG.to_vec(), "image/jpeg")
}

fn transparent_png_response(width: u32, height: u32) -> Response {
    let image = RgbaImage::from_pixel(width.max(1), height.max(1), Rgba([0, 0, 0, 0]));
    bytes_response(
        encode_rgba_png(&image).unwrap_or_else(|| PLACEHOLDER_JPEG.to_vec()),
        "image/png",
    )
}

fn surface_dir_for_request(state: &ApiState, coil_id: i64, surface: &str) -> Option<PathBuf> {
    state
        .test_mode_data_fallback()
        .map(|test_mode| test_mode.surface_asset_dir(surface))
        .or_else(|| {
            state
                .data_config
                .as_ref()
                .and_then(|data_config| data_config.surface_asset_dir(coil_id, surface))
        })
}

fn production_surface_dir_for_request(
    state: &ApiState,
    coil_id: i64,
    surface: &str,
) -> Option<PathBuf> {
    state
        .data_config
        .as_ref()
        .and_then(|data_config| data_config.surface_asset_dir(coil_id, surface))
}

fn surface_dir_for_string_request(
    state: &ApiState,
    coil_id: &str,
    surface: &str,
) -> Option<PathBuf> {
    state
        .test_mode_data_fallback()
        .map(|test_mode| test_mode.surface_asset_dir(surface))
        .or_else(|| {
            let coil_id = coil_id.parse::<i64>().ok()?;
            state
                .data_config
                .as_ref()
                .and_then(|data_config| data_config.surface_asset_dir(coil_id, surface))
        })
}

fn cached_classifier_image_path(
    surface_dir: &FsPath,
    class_name: &str,
    coil_id: i64,
    x: i32,
    y: i32,
) -> Option<PathBuf> {
    let classifier_dir = surface_dir
        .join("classifier")
        .join(safe_folder_name(class_name));
    let prefix = format!("{coil_id}_{x}_{y}_");
    fs::read_dir(classifier_dir)
        .ok()?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .find(|path| {
            path.file_name()
                .and_then(|value| value.to_str())
                .map(|name| {
                    name.starts_with(&prefix) && name.to_ascii_lowercase().ends_with(".png")
                })
                .unwrap_or(false)
        })
}

fn load_gray_rgb_image_from_surface_dir(surface_dir: &FsPath) -> Option<RgbImage> {
    find_named_image_file(&surface_dir.join("jpg"), "GRAY")
        .or_else(|| find_named_image_file(&surface_dir.join("png"), "GRAY"))
        .or_else(|| find_named_image_file(&surface_dir.join("preview"), "GRAY"))
        .and_then(|path| image::open(path).ok())
        .map(|image| image.to_rgb8())
}

fn load_named_rgb_image_from_surface_dir(surface_dir: &FsPath, name: &str) -> Option<RgbImage> {
    let name = name.trim();
    if name.is_empty() {
        return None;
    }
    find_named_image_file(&surface_dir.join("jpg"), name)
        .or_else(|| find_named_image_file(&surface_dir.join("png"), name))
        .or_else(|| find_named_image_file(&surface_dir.join("preview"), name))
        .and_then(|path| image::open(path).ok())
        .map(|image| image.to_rgb8())
}

fn parse_defect_image_coord(value: &str, default_value: i32) -> Result<i32, ()> {
    let value = value.trim();
    if value.is_empty() || value.eq_ignore_ascii_case("nan") {
        return Ok(default_value);
    }
    value.parse::<i32>().map_err(|_| ())
}

fn matching_detection_defect_image_path(
    surface_dir: &FsPath,
    coil_id: i64,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> Option<PathBuf> {
    let detection_dir = surface_dir
        .parent()
        .and_then(FsPath::parent)?
        .join(coil_id.to_string())
        .join("detection");
    if !detection_dir.exists() {
        return None;
    }

    let center_x = f64::from(x) + f64::from(w) / 2.0;
    let center_y = f64::from(y) + f64::from(h) / 2.0;
    for defect_dir in fs::read_dir(detection_dir).ok()?.filter_map(Result::ok) {
        let defect_dir = defect_dir.path();
        if !defect_dir.is_dir() {
            continue;
        }
        for xml_file in fs::read_dir(&defect_dir).ok()?.filter_map(Result::ok) {
            let xml_path = xml_file.path();
            if !xml_path
                .extension()
                .and_then(|value| value.to_str())
                .map(|value| value.eq_ignore_ascii_case("xml"))
                .unwrap_or(false)
            {
                continue;
            }
            let png_path = xml_path.with_extension("png");
            if !png_path.exists() {
                continue;
            }
            let Ok(xml) = fs::read_to_string(&xml_path) else {
                continue;
            };
            if xml_bndboxes(&xml)
                .into_iter()
                .any(|(xmin, ymin, xmax, ymax)| {
                    f64::from(xmin) <= center_x
                        && center_x <= f64::from(xmax)
                        && f64::from(ymin) <= center_y
                        && center_y <= f64::from(ymax)
                })
            {
                return Some(png_path);
            }
        }
    }
    None
}

fn xml_bndboxes(xml: &str) -> Vec<(i32, i32, i32, i32)> {
    let mut boxes = Vec::new();
    let mut rest = xml;
    while let Some(start) = rest.find("<bndbox>") {
        let after_start = &rest[start + "<bndbox>".len()..];
        let Some(end) = after_start.find("</bndbox>") else {
            break;
        };
        let block = &after_start[..end];
        if let (Some(xmin), Some(ymin), Some(xmax), Some(ymax)) = (
            xml_i32_tag(block, "xmin"),
            xml_i32_tag(block, "ymin"),
            xml_i32_tag(block, "xmax"),
            xml_i32_tag(block, "ymax"),
        ) {
            boxes.push((xmin, ymin, xmax, ymax));
        }
        rest = &after_start[end + "</bndbox>".len()..];
    }
    boxes
}

fn xml_i32_tag(xml: &str, tag: &str) -> Option<i32> {
    let start_tag = format!("<{tag}>");
    let end_tag = format!("</{tag}>");
    let start = xml.find(&start_tag)? + start_tag.len();
    let end = xml[start..].find(&end_tag)? + start;
    xml[start..end].trim().parse().ok()
}

fn defect_image_crop(source: &RgbImage, x: i32, y: i32, w: i32, h: i32) -> RgbImage {
    let image_width = source.width() as i32;
    let image_height = source.height() as i32;
    if image_width <= 0 || image_height <= 0 {
        return RgbImage::new(1, 1);
    }

    let requested_w = w.max(1);
    let requested_h = h.max(1);
    let mut crop_x = x;
    let mut crop_y = y;
    let mut crop_w = w;
    let mut crop_h = h;

    if crop_x < 0 {
        crop_w += crop_x;
        crop_x = 0;
    }
    if crop_y < 0 {
        crop_h += crop_y;
        crop_y = 0;
    }
    if crop_x >= image_width {
        crop_x = image_width - 1;
    }
    if crop_y >= image_height {
        crop_y = image_height - 1;
    }
    if crop_x + crop_w > image_width {
        crop_w = image_width - crop_x;
    }
    if crop_y + crop_h > image_height {
        crop_h = image_height - crop_y;
    }
    if crop_w <= 0 {
        crop_w = 1;
    }
    if crop_h <= 0 {
        crop_h = 1;
    }

    let crop = imageops::crop_imm(
        source,
        crop_x as u32,
        crop_y as u32,
        crop_w as u32,
        crop_h as u32,
    )
    .to_image();

    let out_of_bounds = x < 0 || y < 0 || x + w > image_width || y + h > image_height;
    if !out_of_bounds {
        return crop;
    }

    let mut padded = RgbImage::new(requested_w as u32, requested_h as u32);
    let paste_x = i64::from(((requested_w - crop_w) / 2).max(0));
    let paste_y = i64::from(((requested_h - crop_h) / 2).max(0));
    imageops::replace(&mut padded, &crop, paste_x, paste_y);
    padded
}

fn image_clip_box(
    x: i32,
    y: i32,
    w: i32,
    h: i32,
    image_width: u32,
    image_height: u32,
) -> Option<(u32, u32, u32, u32)> {
    let x1 = x.max(0);
    let y1 = y.max(0);
    let x2 = (x + w).min(image_width as i32);
    let y2 = (y + h).min(image_height as i32);
    if x2 <= x1 || y2 <= y1 {
        return None;
    }
    Some((x1 as u32, y1 as u32, (x2 - x1) as u32, (y2 - y1) as u32))
}

fn encode_rgb_jpeg(image: &RgbImage, quality: u8) -> Option<Vec<u8>> {
    let mut bytes = Vec::new();
    let mut encoder = JpegEncoder::new_with_quality(&mut bytes, quality);
    encoder
        .encode_image(&DynamicImage::ImageRgb8(image.clone()))
        .ok()?;
    Some(bytes)
}

fn encode_luma_jpeg(image: &GrayImage, quality: u8) -> Option<Vec<u8>> {
    let mut bytes = Vec::new();
    let mut encoder = JpegEncoder::new_with_quality(&mut bytes, quality);
    encoder
        .encode(
            image.as_raw(),
            image.width(),
            image.height(),
            ExtendedColorType::L8,
        )
        .ok()?;
    Some(bytes)
}

fn encode_rgba_png(image: &RgbaImage) -> Option<Vec<u8>> {
    let mut cursor = Cursor::new(Vec::new());
    DynamicImage::ImageRgba8(image.clone())
        .write_to(&mut cursor, ImageFormat::Png)
        .ok()?;
    Some(cursor.into_inner())
}

fn generate_area_png(depth_map: &DepthMap, query: &AreaQuery) -> Option<Vec<u8>> {
    let source_width = depth_map.width();
    let source_height = depth_map.height();
    if source_width <= 0 || source_height <= 0 {
        return None;
    }

    let scale = normalized_scale(query.scale);
    let target_width = scaled_dimension(source_width, scale);
    let target_height = scaled_dimension(source_height, scale);
    let value_from = query.value_from.unwrap_or(0.0);
    let value_to = query.value_to.unwrap_or(255.0);
    let low = value_from.min(value_to);
    let high = value_from.max(value_to);
    let color = Rgba([
        query.r.unwrap_or(255),
        query.g.unwrap_or(0),
        query.b.unwrap_or(0),
        255,
    ]);
    let mut image = RgbaImage::from_pixel(target_width, target_height, Rgba([0, 0, 0, 0]));

    for y in 0..target_height {
        for x in 0..target_width {
            let source_x = source_coord(x, scale, source_width);
            let source_y = source_coord(y, scale, source_height);
            let Some(value) = depth_map.value_f64(source_x, source_y) else {
                continue;
            };
            if value > low && value < high {
                image.put_pixel(x, y, color);
            }
        }
    }

    encode_rgba_png(&image)
}

fn generate_error_png(
    depth_map: &DepthMap,
    mask: Option<&GrayImage>,
    query: &ErrorImageQuery,
) -> Option<Vec<u8>> {
    let source_width = depth_map.width();
    let source_height = depth_map.height();
    if source_width <= 0 || source_height <= 0 {
        return None;
    }

    let median_z = median_depth_above(depth_map, 1000.0)?;
    let scale_factor = DEFAULT_SCAN3D_SCALE_Z;
    let threshold_down_units = abs_finite_f64(query.min_value.unwrap_or(0.0)) / scale_factor;
    let threshold_up_units = abs_finite_f64(query.max_value.unwrap_or(255.0)) / scale_factor;
    let min_value = median_z - threshold_down_units;
    let max_value = median_z + threshold_up_units;
    let scale = normalized_scale(query.scale);
    let target_width = scaled_dimension(source_width, scale);
    let target_height = scaled_dimension(source_height, scale);
    let mut image = RgbaImage::from_pixel(target_width, target_height, Rgba([0, 0, 0, 0]));

    for y in 0..target_height {
        for x in 0..target_width {
            let value = if scale < 0.99 {
                resized_depth_f64_area(depth_map, x, y, target_width, target_height)
            } else {
                let source_x = source_coord(x, scale, source_width);
                let source_y = source_coord(y, scale, source_height);
                let masked_out = mask
                    .and_then(|mask| mask_pixel(mask, source_x, source_y))
                    .map(|value| value == 0)
                    .unwrap_or(false);
                if masked_out {
                    continue;
                }
                depth_map.value_f64(source_x, source_y).unwrap_or(0.0)
            };
            if value > 1000.0 && value < min_value {
                image.put_pixel(x, y, Rgba([0, 0, 255, 255]));
            } else if value > max_value {
                image.put_pixel(x, y, Rgba([255, 0, 0, 255]));
            }
        }
    }

    encode_rgba_png(&image)
}

fn resized_depth_f64_area(
    depth_map: &DepthMap,
    target_x: u32,
    target_y: u32,
    target_width: u32,
    target_height: u32,
) -> f64 {
    let source_width = depth_map.width().max(1);
    let source_height = depth_map.height().max(1);
    let x_start = f64::from(target_x) * f64::from(source_width) / f64::from(target_width.max(1));
    let x_end = f64::from(target_x + 1) * f64::from(source_width) / f64::from(target_width.max(1));
    let y_start = f64::from(target_y) * f64::from(source_height) / f64::from(target_height.max(1));
    let y_end =
        f64::from(target_y + 1) * f64::from(source_height) / f64::from(target_height.max(1));
    let mut weighted_sum = 0.0;
    let mut weight_total = 0.0;

    for source_y in (y_start.floor() as i32)..(y_end.ceil() as i32) {
        if source_y < 0 || source_y >= source_height {
            continue;
        }
        let y_weight = area_overlap(y_start, y_end, source_y);
        if y_weight <= 0.0 {
            continue;
        }
        for source_x in (x_start.floor() as i32)..(x_end.ceil() as i32) {
            if source_x < 0 || source_x >= source_width {
                continue;
            }
            let x_weight = area_overlap(x_start, x_end, source_x);
            if x_weight <= 0.0 {
                continue;
            }
            let weight = x_weight * y_weight;
            weighted_sum += depth_map.value_f64(source_x, source_y).unwrap_or(0.0) * weight;
            weight_total += weight;
        }
    }

    if weight_total <= 0.0 {
        return 0.0;
    }
    weighted_sum / weight_total
}

fn median_depth_above(depth_map: &DepthMap, minimum: f64) -> Option<f64> {
    let mut values = Vec::new();
    for y in 0..depth_map.height() {
        for x in 0..depth_map.width() {
            if let Some(value) = depth_map.value_f64(x, y)
                && value.is_finite()
                && value > minimum
            {
                values.push(value);
            }
        }
    }
    if values.is_empty() {
        return None;
    }
    values.sort_by(|left, right| left.total_cmp(right));
    let middle = values.len() / 2;
    Some(if values.len() % 2 == 1 {
        values[middle]
    } else {
        (values[middle - 1] + values[middle]) / 2.0
    })
}

fn normalized_scale(scale: Option<f64>) -> f64 {
    scale
        .filter(|value| value.is_finite() && *value > 0.0)
        .unwrap_or(1.0)
}

fn abs_finite_f64(value: f64) -> f64 {
    if value.is_finite() { value.abs() } else { 0.0 }
}

fn error_cache_matches(
    error_cache_path: &FsPath,
    threshold_down_mm: f64,
    threshold_up_mm: f64,
) -> bool {
    let meta_path = error_cache_path.with_extension("json");
    let Ok(content) = fs::read_to_string(meta_path) else {
        return false;
    };
    let Ok(value) = serde_json::from_str::<Value>(&content) else {
        return false;
    };
    let Some(cached_down) = value.get("threshold_down").and_then(Value::as_f64) else {
        return false;
    };
    let Some(cached_up) = value.get("threshold_up").and_then(Value::as_f64) else {
        return false;
    };
    (abs_finite_f64(cached_down) - abs_finite_f64(threshold_down_mm)).abs() <= f64::EPSILON
        && (abs_finite_f64(cached_up) - abs_finite_f64(threshold_up_mm)).abs() <= f64::EPSILON
}

fn clip_max_images_from_surface_dir(
    surface_dir: &FsPath,
    output_dir: &FsPath,
    coil_id: i64,
    surface: &str,
) -> Result<usize, String> {
    let source = load_gray_rgb_image_from_surface_dir(surface_dir)
        .ok_or_else(|| "source image not found".to_string())?;
    let mask = load_mask_image(surface_dir).unwrap_or_else(|| {
        GrayImage::from_pixel(source.width(), source.height(), image::Luma([255]))
    });
    let image_width = source.width() as i32;
    let image_height = source.height() as i32;
    let clip_num = 10;
    let item_width = image_width / clip_num;
    let item_height = image_height / clip_num;
    if item_width <= 0 || item_height <= 0 {
        return Ok(0);
    }

    let mut saved = 0;
    for i in 0..clip_num {
        for j in 0..clip_num {
            let clip_x = (item_width * j - 20).max(0);
            let clip_y = (item_height * i - 20).max(0);
            let clip_w = item_width + 20;
            let clip_h = item_height + 20;
            if clip_w < 200 || clip_h < 200 {
                continue;
            }
            let actual_w = clip_w.min(image_width.saturating_sub(clip_x));
            let actual_h = clip_h.min(image_height.saturating_sub(clip_y));
            if actual_w <= 0 || actual_h <= 0 {
                continue;
            }
            if mask_nonzero_ratio(&mask, clip_x, clip_y, actual_w, actual_h) <= 0.02 {
                continue;
            }

            let crop = imageops::crop_imm(
                &source,
                clip_x as u32,
                clip_y as u32,
                actual_w as u32,
                actual_h as u32,
            )
            .to_image();
            let output_path = output_dir.join(format!(
                "{coil_id}_{surface}_{clip_x}_{clip_y}_{clip_w}_{clip_h}.png"
            ));
            DynamicImage::ImageRgb8(crop)
                .save(&output_path)
                .map_err(|error| error.to_string())?;
            saved += 1;
        }
    }

    Ok(saved)
}

fn mask_nonzero_ratio(mask: &GrayImage, x: i32, y: i32, w: i32, h: i32) -> f64 {
    let mut nonzero = 0usize;
    let mut total = 0usize;
    for yy in y..(y + h) {
        for xx in x..(x + w) {
            total += 1;
            if xx >= 0
                && yy >= 0
                && xx < mask.width() as i32
                && yy < mask.height() as i32
                && mask.get_pixel(xx as u32, yy as u32).0[0] != 0
            {
                nonzero += 1;
            }
        }
    }
    if total == 0 {
        0.0
    } else {
        nonzero as f64 / total as f64
    }
}

fn render_image_from_surface_dir(
    surface_dir: &FsPath,
    query: &RenderQuery,
) -> Option<RenderedImage> {
    let endpoint = "/coilData/Render";
    let context = surface_dir.to_string_lossy().to_string();
    let total_started = Instant::now();
    let colormap = query.colormap();
    if !query.thumbnail() {
        let rendered = render_dynamic_image_from_surface_dir(surface_dir, query);
        profile_stage(endpoint, "total", total_started, &context);
        return rendered;
    }

    let image_path = falsecolor_thumbnail_path(surface_dir, colormap);
    if let Some(image_path) = image_path {
        let read_started = Instant::now();
        let bytes = std::fs::read(&image_path).ok()?;
        profile_stage(endpoint, "read_thumbnail_cache", read_started, &context);
        profile_stage(endpoint, "total", total_started, &context);
        return Some(RenderedImage {
            bytes,
            content_type: content_type_for_path(&image_path),
            thumbnail: query.thumbnail(),
            colormap: colormap.to_string(),
            from_cache: true,
        });
    }

    if query.grayscale() && query.mask() {
        return render_dynamic_image_from_surface_dir(surface_dir, &query.with_thumbnail(false));
    }

    let rendered = render_dynamic_image_from_surface_dir(surface_dir, query)?;
    if query.thumbnail() {
        let write_started = Instant::now();
        write_falsecolor_thumbnail_cache(surface_dir, colormap, &rendered.bytes);
        profile_stage(endpoint, "write_thumbnail_cache", write_started, &context);
    }
    profile_stage(endpoint, "total", total_started, &context);
    Some(rendered)
}

fn falsecolor_thumbnail_path(surface_dir: &FsPath, colormap: &str) -> Option<PathBuf> {
    let path = falsecolor_thumbnail_cache_path(surface_dir, colormap)?;
    path.exists().then_some(path)
}

fn falsecolor_thumbnail_cache_path(surface_dir: &FsPath, colormap: &str) -> Option<PathBuf> {
    let colormap_dir = colormap.trim().to_ascii_lowercase();
    if colormap_dir.is_empty() {
        return None;
    }
    Some(
        surface_dir
            .join("cache")
            .join("falsecolor")
            .join(colormap_dir)
            .join("thumbnail_1024.jpg"),
    )
}

fn write_falsecolor_thumbnail_cache(surface_dir: &FsPath, colormap: &str, bytes: &[u8]) {
    let Some(path) = falsecolor_thumbnail_cache_path(surface_dir, colormap) else {
        return;
    };
    let Some(parent) = path.parent() else {
        return;
    };
    if fs::create_dir_all(parent).is_ok() {
        let _ = fs::write(path, bytes);
    }
}

fn render_dynamic_image_from_surface_dir(
    surface_dir: &FsPath,
    query: &RenderQuery,
) -> Option<RenderedImage> {
    let endpoint = "/coilData/Render";
    let context = surface_dir.to_string_lossy().to_string();
    let load_started = Instant::now();
    let depth_map = load_depth_map_from_dir(surface_dir)?;
    profile_stage(endpoint, "load_depth", load_started, &context);
    let mask_started = Instant::now();
    let mask = if query.mask() {
        load_mask_image(surface_dir)
    } else {
        None
    };
    profile_stage(endpoint, "load_mask", mask_started, &context);
    let encode_started = Instant::now();
    let bytes = generate_render_jpeg(&depth_map, mask.as_ref(), query)?;
    profile_stage(endpoint, "render_encode", encode_started, &context);
    Some(RenderedImage {
        bytes,
        content_type: "image/jpeg",
        thumbnail: query.thumbnail(),
        colormap: query.colormap().to_string(),
        from_cache: false,
    })
}

fn load_mask_image(surface_dir: &FsPath) -> Option<GrayImage> {
    [
        surface_dir.join("mask").join("MASK.png"),
        surface_dir.join("mask").join("MASK.jpg"),
        surface_dir.join("mask").join("MASK.jpeg"),
        surface_dir.join("jpg").join("MASK.jpg"),
        surface_dir.join("png").join("MASK.png"),
    ]
    .iter()
    .find(|path| path.exists())
    .and_then(|path| image::open(path).ok())
    .map(|image| image.to_luma8())
}

fn generate_render_jpeg(
    depth_map: &DepthMap,
    mask: Option<&GrayImage>,
    query: &RenderQuery,
) -> Option<Vec<u8>> {
    let source_width = depth_map.width();
    let source_height = depth_map.height();
    if source_width <= 0 || source_height <= 0 {
        return None;
    }

    let scale = render_target_scale(source_width, source_height, query);
    let target_width = scaled_dimension(source_width, scale);
    let target_height = scaled_dimension(source_height, scale);
    let (min_value, max_value) = query.min_max();
    let mut image = RgbImage::new(target_width, target_height);

    for y in 0..target_height {
        for x in 0..target_width {
            let pixel = if scale < 0.99 {
                let masked_out = mask
                    .map(|mask| {
                        let value = if query.thumbnail() {
                            resized_mask_pixel_nearest(mask, x, y, target_width, target_height)
                        } else {
                            resized_mask_pixel(mask, x, y, target_width, target_height)
                        };
                        value == 0
                    })
                    .unwrap_or(false);
                if masked_out {
                    Rgb([0, 0, 0])
                } else {
                    let normalized = if query.thumbnail() {
                        resized_depth_u8_area(
                            depth_map,
                            x,
                            y,
                            target_width,
                            target_height,
                            min_value,
                            max_value,
                        )
                    } else {
                        resized_depth_u8(
                            depth_map,
                            x,
                            y,
                            target_width,
                            target_height,
                            min_value,
                            max_value,
                        )
                    };
                    if query.grayscale() {
                        Rgb([normalized, normalized, normalized])
                    } else {
                        Rgb(jet_rgb(normalized))
                    }
                }
            } else {
                let source_x = source_coord(x, scale, source_width);
                let source_y = source_coord(y, scale, source_height);
                let masked_out = mask
                    .and_then(|mask| mask_pixel(mask, source_x, source_y))
                    .map(|value| value == 0)
                    .unwrap_or(false);
                if masked_out {
                    Rgb([0, 0, 0])
                } else {
                    let value = depth_map.value_f64(source_x, source_y).unwrap_or(0.0);
                    let normalized = normalize_depth_to_u8(value, min_value, max_value);
                    if query.grayscale() {
                        Rgb([normalized, normalized, normalized])
                    } else {
                        Rgb(jet_rgb(normalized))
                    }
                }
            };
            image.put_pixel(x, y, pixel);
        }
    }

    let mut bytes = Vec::new();
    let mut encoder = JpegEncoder::new_with_quality(&mut bytes, 90);
    encoder.encode_image(&DynamicImage::ImageRgb8(image)).ok()?;
    Some(bytes)
}

fn scaled_dimension(source: i32, scale: f64) -> u32 {
    ((f64::from(source) * scale) as i32).max(1) as u32
}

fn render_effective_scale(scale: f64) -> f64 {
    if scale < 0.99 { scale } else { 1.0 }
}

fn render_target_scale(source_width: i32, source_height: i32, query: &RenderQuery) -> f64 {
    if query.thumbnail() {
        let max_dimension = f64::from(source_width.max(source_height).max(1));
        let thumbnail_scale = 1024.0 / max_dimension;
        return thumbnail_scale.min(1.0);
    }
    render_effective_scale(query.scale())
}

fn resized_depth_u8(
    depth_map: &DepthMap,
    target_x: u32,
    target_y: u32,
    target_width: u32,
    target_height: u32,
    min_value: i32,
    max_value: i32,
) -> u8 {
    let source_width = depth_map.width().max(1);
    let source_height = depth_map.height().max(1);
    let (x0, x1, wx) = cv2_resize_axis(target_x, target_width, source_width);
    let (y0, y1, wy) = cv2_resize_axis(target_y, target_height, source_height);
    let sample = |x: i32, y: i32| {
        f64::from(normalize_depth_to_u8(
            depth_map.value_f64(x, y).unwrap_or(0.0),
            min_value,
            max_value,
        ))
    };
    bilinear_u8(
        sample(x0, y0),
        sample(x1, y0),
        sample(x0, y1),
        sample(x1, y1),
        wx,
        wy,
    )
}

fn resized_depth_u8_area(
    depth_map: &DepthMap,
    target_x: u32,
    target_y: u32,
    target_width: u32,
    target_height: u32,
    min_value: i32,
    max_value: i32,
) -> u8 {
    let source_width = depth_map.width().max(1);
    let source_height = depth_map.height().max(1);
    let x_start = f64::from(target_x) * f64::from(source_width) / f64::from(target_width.max(1));
    let x_end = f64::from(target_x + 1) * f64::from(source_width) / f64::from(target_width.max(1));
    let y_start = f64::from(target_y) * f64::from(source_height) / f64::from(target_height.max(1));
    let y_end =
        f64::from(target_y + 1) * f64::from(source_height) / f64::from(target_height.max(1));
    let mut weighted_sum = 0.0;
    let mut weight_total = 0.0;

    for source_y in (y_start.floor() as i32)..(y_end.ceil() as i32) {
        if source_y < 0 || source_y >= source_height {
            continue;
        }
        let y_weight = area_overlap(y_start, y_end, source_y);
        if y_weight <= 0.0 {
            continue;
        }
        for source_x in (x_start.floor() as i32)..(x_end.ceil() as i32) {
            if source_x < 0 || source_x >= source_width {
                continue;
            }
            let x_weight = area_overlap(x_start, x_end, source_x);
            if x_weight <= 0.0 {
                continue;
            }
            let weight = x_weight * y_weight;
            let normalized = f64::from(normalize_depth_to_u8(
                depth_map.value_f64(source_x, source_y).unwrap_or(0.0),
                min_value,
                max_value,
            ));
            weighted_sum += normalized * weight;
            weight_total += weight;
        }
    }

    if weight_total <= 0.0 {
        return 0;
    }
    (weighted_sum / weight_total).round().clamp(0.0, 255.0) as u8
}

fn area_overlap(start: f64, end: f64, source_index: i32) -> f64 {
    let pixel_start = f64::from(source_index);
    let pixel_end = pixel_start + 1.0;
    end.min(pixel_end) - start.max(pixel_start)
}

fn resized_mask_pixel(
    mask: &GrayImage,
    target_x: u32,
    target_y: u32,
    target_width: u32,
    target_height: u32,
) -> u8 {
    let source_width = i32::try_from(mask.width()).unwrap_or(i32::MAX).max(1);
    let source_height = i32::try_from(mask.height()).unwrap_or(i32::MAX).max(1);
    let (x0, x1, wx) = cv2_resize_axis(target_x, target_width, source_width);
    let (y0, y1, wy) = cv2_resize_axis(target_y, target_height, source_height);
    let sample = |x: i32, y: i32| f64::from(mask_pixel(mask, x, y).unwrap_or(0));
    bilinear_u8(
        sample(x0, y0),
        sample(x1, y0),
        sample(x0, y1),
        sample(x1, y1),
        wx,
        wy,
    )
}

fn resized_mask_pixel_nearest(
    mask: &GrayImage,
    target_x: u32,
    target_y: u32,
    target_width: u32,
    target_height: u32,
) -> u8 {
    let source_width = i32::try_from(mask.width()).unwrap_or(i32::MAX).max(1);
    let source_height = i32::try_from(mask.height()).unwrap_or(i32::MAX).max(1);
    let source_x = cv2_nearest_resize_coord(target_x, target_width, source_width);
    let source_y = cv2_nearest_resize_coord(target_y, target_height, source_height);
    mask_pixel(mask, source_x, source_y).unwrap_or(0)
}

fn cv2_nearest_resize_coord(target: u32, target_len: u32, source_len: i32) -> i32 {
    ((f64::from(target) * f64::from(source_len) / f64::from(target_len.max(1))).floor() as i32)
        .clamp(0, source_len.saturating_sub(1))
}

fn cv2_resize_axis(target: u32, target_len: u32, source_len: i32) -> (i32, i32, f64) {
    let source =
        ((f64::from(target) + 0.5) * f64::from(source_len) / f64::from(target_len.max(1))) - 0.5;
    let lower = source.floor();
    let weight = source - lower;
    let lower = (lower as i32).clamp(0, source_len.saturating_sub(1));
    let upper = (lower + 1).clamp(0, source_len.saturating_sub(1));
    (lower, upper, weight.clamp(0.0, 1.0))
}

fn bilinear_u8(
    top_left: f64,
    top_right: f64,
    bottom_left: f64,
    bottom_right: f64,
    wx: f64,
    wy: f64,
) -> u8 {
    let top = top_left * (1.0 - wx) + top_right * wx;
    let bottom = bottom_left * (1.0 - wx) + bottom_right * wx;
    (top * (1.0 - wy) + bottom * wy).round().clamp(0.0, 255.0) as u8
}

fn source_coord(target_coord: u32, scale: f64, source_limit: i32) -> i32 {
    ((f64::from(target_coord) / scale).floor() as i32).clamp(0, source_limit.saturating_sub(1))
}

fn mask_pixel(mask: &GrayImage, x: i32, y: i32) -> Option<u8> {
    if x < 0 || y < 0 || x >= mask.width() as i32 || y >= mask.height() as i32 {
        return None;
    }
    Some(mask.get_pixel(x as u32, y as u32).0[0])
}

fn normalize_depth_to_u8(value: f64, min_value: i32, max_value: i32) -> u8 {
    let clipped = value.clamp(f64::from(min_value), f64::from(max_value));
    (((clipped - f64::from(min_value)) / f64::from(max_value - min_value)) * 255.0)
        .clamp(0.0, 255.0) as u8
}

fn jet_rgb(value: u8) -> [u8; 3] {
    [
        opencv_jet_channel(4 * i32::from(value) - 382, -4 * i32::from(value) + 1148),
        opencv_jet_channel(4 * i32::from(value) - 128, -4 * i32::from(value) + 892),
        opencv_jet_channel(4 * i32::from(value) + 128, -4 * i32::from(value) + 638),
    ]
}

fn opencv_jet_channel(rising: i32, falling: i32) -> u8 {
    rising.clamp(0, 255).min(falling.clamp(0, 255)) as u8
}

fn clamp_point(x: i32, y: i32, width: i32, height: i32) -> (i32, i32) {
    (
        x.clamp(0, width.saturating_sub(1)),
        y.clamp(0, height.saturating_sub(1)),
    )
}

fn div_round(value: i32, divisor: i32) -> i32 {
    if divisor == 0 {
        return 0;
    }
    (f64::from(value) / f64::from(divisor)).round() as i32
}

#[cfg(test)]
mod render_color_tests {
    use super::*;

    #[test]
    fn disk_status_lines_are_sorted_by_mount_label_like_python() {
        let mut rows = vec![
            (
                "K:\\".to_string(),
                "分区: K:\\, 总大小: 10.00 GB".to_string(),
            ),
            (
                "C:\\".to_string(),
                "分区: C:\\, 总大小: 10.00 GB".to_string(),
            ),
            (
                "D:\\".to_string(),
                "分区: D:\\, 总大小: 10.00 GB".to_string(),
            ),
        ];

        sort_disk_status_lines_by_mount_label(&mut rows);

        let labels = rows
            .iter()
            .map(|(label, _)| label.as_str())
            .collect::<Vec<_>>();
        assert_eq!(labels, vec!["C:\\", "D:\\", "K:\\"]);
    }

    #[test]
    fn jet_rgb_matches_opencv_colormap_jet_key_points() {
        let cases = [
            (0, [0, 0, 128]),
            (1, [0, 0, 132]),
            (64, [0, 128, 255]),
            (127, [126, 255, 130]),
            (128, [130, 255, 126]),
            (191, [255, 128, 0]),
            (254, [132, 0, 0]),
            (255, [128, 0, 0]),
        ];

        for (value, expected) in cases {
            assert_eq!(jet_rgb(value), expected, "JET RGB mismatch at {value}");
        }
    }
}

fn synthetic_height_value(x: i32, y: i32) -> i32 {
    1000 + x + y
}

fn real_height_segments(
    depth_map: &DepthMap,
    mask: Option<&GrayImage>,
    x1: i32,
    y1: i32,
    x2: i32,
    y2: i32,
) -> Value {
    let height = depth_map.height();
    let width = depth_map.width();
    if height <= 0 || width <= 0 {
        return Value::Array(Vec::new());
    }

    let (start, end) = match mask {
        Some(mask) => {
            let mask_width = i32::try_from(mask.width()).unwrap_or(i32::MAX);
            let mask_height = i32::try_from(mask.height()).unwrap_or(i32::MAX);
            match edge_points_for_line(x1, y1, x2, y2, mask_width, mask_height) {
                Some(points) => points,
                None => return Value::Array(Vec::new()),
            }
        }
        None => (
            clamp_point(x1, y1, width, height),
            clamp_point(x2, y2, width, height),
        ),
    };
    let mut segments = Vec::new();
    let mut current = Vec::new();

    for (x, y) in line_points(start, end) {
        let z = if mask
            .and_then(|mask| mask_pixel(mask, x, y))
            .map(|value| value > 100)
            .unwrap_or(true)
        {
            depth_map.value_i32(x, y).unwrap_or(0)
        } else {
            0
        };
        if z > 100 {
            current.push(json!([x, y, z]));
        } else if !current.is_empty() {
            push_real_segment(&mut segments, &mut current);
        }
    }
    push_real_segment(&mut segments, &mut current);

    Value::Array(segments)
}

fn edge_points_for_line(
    x1: i32,
    y1: i32,
    x2: i32,
    y2: i32,
    width: i32,
    height: i32,
) -> Option<((i32, i32), (i32, i32))> {
    if width <= 0 || height <= 0 {
        return None;
    }

    let mut points = Vec::new();
    let mut add_point = |x: f64, y: f64| {
        if x >= 0.0 && y >= 0.0 && x <= f64::from(width) && y <= f64::from(height) {
            let x = (x as i32).clamp(0, width.saturating_sub(1));
            let y = (y as i32).clamp(0, height.saturating_sub(1));
            if !points.contains(&(x, y)) {
                points.push((x, y));
            }
        }
    };

    if x1 != x2 && y1 != y2 {
        let slope = f64::from(y2 - y1) / f64::from(x2 - x1);
        let intercept = f64::from(y1) - slope * f64::from(x1);
        add_point((0.0 - intercept) / slope, 0.0);
        add_point((f64::from(height) - intercept) / slope, f64::from(height));
        add_point(0.0, intercept);
        add_point(f64::from(width), slope * f64::from(width) + intercept);
    } else if x1 == x2 {
        add_point(f64::from(x1), 0.0);
        add_point(f64::from(x1), f64::from(height));
    } else {
        add_point(0.0, f64::from(y1));
        add_point(f64::from(width), f64::from(y1));
    }

    match points.len() {
        0 | 1 => None,
        2 => Some((points[0], points[1])),
        _ => {
            let mut max_pair = (points[0], points[1]);
            let mut max_distance = -1_i64;
            for (index, left) in points.iter().enumerate() {
                for right in points.iter().skip(index + 1) {
                    let dx = i64::from(left.0 - right.0);
                    let dy = i64::from(left.1 - right.1);
                    let distance = dx * dx + dy * dy;
                    if distance > max_distance {
                        max_distance = distance;
                        max_pair = (*left, *right);
                    }
                }
            }
            Some(max_pair)
        }
    }
}

fn line_points(start: (i32, i32), end: (i32, i32)) -> Vec<(i32, i32)> {
    let (mut x0, mut y0) = start;
    let (x1, y1) = end;
    let dx = (x1 - x0).abs();
    let sx = if x0 < x1 { 1 } else { -1 };
    let dy = -(y1 - y0).abs();
    let sy = if y0 < y1 { 1 } else { -1 };
    let mut error = dx + dy;
    let mut points = Vec::new();

    loop {
        points.push((x0, y0));
        if x0 == x1 && y0 == y1 {
            break;
        }
        let doubled_error = 2 * error;
        if doubled_error >= dy {
            error += dy;
            x0 += sx;
        }
        if doubled_error <= dx {
            error += dx;
            y0 += sy;
        }
    }

    points
}

fn push_real_segment(segments: &mut Vec<Value>, current: &mut Vec<Value>) {
    if current.len() > 100 {
        let left = current.first().cloned().unwrap_or_else(|| json!([0, 0, 0]));
        let right = current.last().cloned().unwrap_or_else(|| json!([0, 0, 0]));
        segments.push(json!({
            "pointL": [left[0].clone(), left[1].clone()],
            "pointR": [right[0].clone(), right[1].clone()],
            "points": std::mem::take(current),
        }));
    } else {
        current.clear();
    }
}
