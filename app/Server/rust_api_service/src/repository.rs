use anyhow::Result;
use async_trait::async_trait;
use chrono::NaiveDateTime;
use serde_json::Value;
use sqlx::mysql::{MySqlPool, MySqlPoolOptions};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use crate::models::{
    AlarmFlatRollDataRow, AlarmFlatRollRow, AlarmInfoSummaryRow, AlarmLooseCoilRow,
    AlarmTaperShapeRow, CapTrueLogItemRow, CapTrueLogRow, CoilAlarmStatusRow, CoilCheckRow,
    CoilDefectRow, CoilDefectSqlRow, CoilRow, CoilStateRow, CoilStateSqlRow, CoilSummaryRow,
    DataEllipseRow, DeepPointRow, DefectCheckRow, DefectClassDictRow, DefectStatisticsRow,
    DetectionSpeedRow, GraderRow, GraderSqlRow, ImageJoinLogRow, LatestCoilRow, LineDataRow,
    ManualDefectRow, ManualDefectSqlRow, ManualDefectWrite, NextCodeDictRow, PlcCurveAllRow,
    PlcCurveAllSqlRow, PlcDataRow, PlcDataSqlRow, PointDataRow, SecondaryCoilRow,
    ServerDetectionErrorRow, TaperShapePointRow,
};

#[async_trait]
pub trait CoilRepository: Send + Sync {
    async fn list_coils(&self, limit: u32) -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_recent(&self, limit: u32) -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_recent_for_export(
        &self,
        limit: u32,
    ) -> Result<Vec<CoilSummaryRow>>;
    async fn latest_coil(&self) -> Result<Option<LatestCoilRow>>;
    async fn list_coils_after(&self, coil_id: i64, limit: u32) -> Result<Vec<CoilSummaryRow>>;
    async fn grader_list(&self, limit: u32) -> Result<Vec<GraderRow>>;
    async fn coil_detail(&self, coil_id: i64) -> Result<Option<GraderRow>>;
    async fn search_coils_by_no(&self, coil_no: &str) -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_by_id(&self, coil_id: i64) -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_by_id_range(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_by_datetime(&self, start: &str, end: &str)
    -> Result<Vec<CoilSummaryRow>>;
    async fn search_coils_by_datetime_for_export(
        &self,
        start: &str,
        end: &str,
    ) -> Result<Vec<CoilSummaryRow>>;
    async fn backup_secondary_coils(&self) -> Result<Vec<SecondaryCoilRow>>;
    async fn secondary_coils(&self, coil_id: i64) -> Result<Vec<SecondaryCoilRow>>;
    async fn coil_rows(&self, coil_id: i64) -> Result<Vec<CoilRow>>;
    async fn backup_coil_rows(&self) -> Result<Vec<CoilRow>>;
    async fn defects(&self, coil_id: i64, surface: &str) -> Result<Vec<CoilDefectRow>>;
    async fn defects_between(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilDefectRow>>;
    async fn backup_defects(&self) -> Result<Vec<CoilDefectRow>>;
    async fn manual_defects(&self, coil_id: i64, surface: &str) -> Result<Vec<ManualDefectRow>>;
    async fn backup_manual_defects(&self) -> Result<Vec<ManualDefectRow>>;
    async fn add_manual_defect(&self, defect: ManualDefectWrite) -> Result<ManualDefectRow>;
    async fn update_manual_defect(
        &self,
        defect_id: i64,
        defect: ManualDefectWrite,
    ) -> Result<Option<ManualDefectRow>>;
    async fn delete_manual_defect(&self, defect_id: i64) -> Result<bool>;
    async fn coil_checks(&self, coil_id: i64) -> Result<Vec<CoilCheckRow>>;
    async fn backup_coil_checks(&self) -> Result<Vec<CoilCheckRow>>;
    async fn coil_check(&self, coil_id: i64) -> Result<Option<CoilCheckRow>>;
    async fn set_coil_check(&self, coil_id: i64, status: i32, msg: &str) -> Result<()>;
    async fn coil_state(&self, coil_id: i64, surface: &str) -> Result<Option<CoilStateRow>>;
    async fn coil_states(&self, coil_id: i64) -> Result<Vec<CoilStateRow>>;
    async fn backup_coil_states(&self) -> Result<Vec<CoilStateRow>>;
    async fn plc_data(&self, coil_id: i64) -> Result<Option<PlcDataRow>>;
    async fn backup_plc_data(&self) -> Result<Vec<PlcDataRow>>;
    async fn plc_curve_rows(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcDataRow>>;
    async fn plc_curve_all(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcCurveAllRow>>;
    async fn point_data(&self, coil_id: i64, surface: &str) -> Result<Vec<PointDataRow>>;
    async fn backup_point_data(&self) -> Result<Vec<PointDataRow>>;
    async fn line_data(&self, coil_id: i64, surface: &str) -> Result<Vec<LineDataRow>>;
    async fn backup_line_data(&self) -> Result<Vec<LineDataRow>>;
    async fn defect_class_dict(&self) -> Result<Vec<DefectClassDictRow>>;
    async fn next_code_dict(&self) -> Result<Vec<NextCodeDictRow>>;
    async fn sync_missing_summaries(&self, limit: u32) -> Result<usize>;
    async fn sync_existing_summaries(&self, coil_ids: &[i64]) -> Result<usize>;
    async fn alarm_flat_rolls(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollRow>>;
    async fn backup_alarm_flat_rolls(&self) -> Result<Vec<AlarmFlatRollRow>>;
    async fn alarm_taper_shapes(&self, coil_id: i64) -> Result<Vec<AlarmTaperShapeRow>>;
    async fn backup_alarm_taper_shapes(&self) -> Result<Vec<AlarmTaperShapeRow>>;
    async fn alarm_loose_coils(&self, coil_id: i64) -> Result<Vec<AlarmLooseCoilRow>>;
    async fn backup_alarm_loose_coils(&self) -> Result<Vec<AlarmLooseCoilRow>>;
    async fn taper_shape_points(&self, coil_id: i64) -> Result<Vec<TaperShapePointRow>>;
    async fn backup_taper_shape_points(&self) -> Result<Vec<TaperShapePointRow>>;
    async fn alarm_infos(&self, coil_id: i64) -> Result<Vec<AlarmInfoSummaryRow>>;
    async fn backup_alarm_infos(&self) -> Result<Vec<AlarmInfoSummaryRow>>;
    async fn server_detection_errors(&self, coil_id: i64) -> Result<Vec<ServerDetectionErrorRow>>;
    async fn backup_server_detection_errors(&self) -> Result<Vec<ServerDetectionErrorRow>>;
    async fn defect_checks(&self, coil_id: i64) -> Result<Vec<DefectCheckRow>>;
    async fn backup_defect_checks(&self) -> Result<Vec<DefectCheckRow>>;
    async fn data_ellipses(&self, coil_id: i64) -> Result<Vec<DataEllipseRow>>;
    async fn backup_data_ellipses(&self) -> Result<Vec<DataEllipseRow>>;
    async fn deep_points(&self, coil_id: i64) -> Result<Vec<DeepPointRow>>;
    async fn backup_deep_points(&self) -> Result<Vec<DeepPointRow>>;
    async fn detection_speeds(&self, coil_id: i64) -> Result<Vec<DetectionSpeedRow>>;
    async fn backup_detection_speeds(&self) -> Result<Vec<DetectionSpeedRow>>;
    async fn coil_alarm_statuses(&self, coil_id: i64) -> Result<Vec<CoilAlarmStatusRow>>;
    async fn backup_coil_alarm_statuses(&self) -> Result<Vec<CoilAlarmStatusRow>>;
    async fn image_join_logs(&self, coil_id: i64) -> Result<Vec<ImageJoinLogRow>>;
    async fn backup_image_join_logs(&self) -> Result<Vec<ImageJoinLogRow>>;
    async fn defect_statistics(&self, coil_id: i64) -> Result<Vec<DefectStatisticsRow>>;
    async fn backup_defect_statistics(&self) -> Result<Vec<DefectStatisticsRow>>;
    async fn alarm_flat_roll_data(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollDataRow>>;
    async fn backup_alarm_flat_roll_data(&self) -> Result<Vec<AlarmFlatRollDataRow>>;
    async fn cap_true_logs(&self, coil_id: i64) -> Result<Vec<CapTrueLogRow>>;
    async fn backup_cap_true_logs(&self) -> Result<Vec<CapTrueLogRow>>;
    async fn cap_true_log_items(&self, coil_id: i64) -> Result<Vec<CapTrueLogItemRow>>;
    async fn backup_cap_true_log_items(&self) -> Result<Vec<CapTrueLogItemRow>>;
}

#[derive(Clone)]
pub struct InMemoryCoilRepository {
    coils: Arc<Mutex<Vec<CoilSummaryRow>>>,
    detected_coils: Vec<CoilSummaryRow>,
    secondary_coils: Vec<SecondaryCoilRow>,
    coil_rows: Vec<CoilRow>,
    defects: Vec<CoilDefectRow>,
    manual_defects: Arc<Mutex<Vec<ManualDefectRow>>>,
    coil_states: Vec<CoilStateRow>,
    plc_data: Vec<PlcDataRow>,
    coil_checks: Arc<Mutex<Vec<CoilCheckRow>>>,
    point_data: Vec<PointDataRow>,
    line_data: Vec<LineDataRow>,
    defect_classes: Vec<DefectClassDictRow>,
    next_code_dict: Vec<NextCodeDictRow>,
    alarm_infos: Vec<AlarmInfoSummaryRow>,
    alarm_flat_rolls: Vec<AlarmFlatRollRow>,
    alarm_taper_shapes: Vec<AlarmTaperShapeRow>,
    alarm_loose_coils: Vec<AlarmLooseCoilRow>,
    taper_shape_points: Vec<TaperShapePointRow>,
    server_detection_errors: Vec<ServerDetectionErrorRow>,
    defect_checks: Vec<DefectCheckRow>,
    data_ellipses: Vec<DataEllipseRow>,
    deep_points: Vec<DeepPointRow>,
    detection_speeds: Vec<DetectionSpeedRow>,
    coil_alarm_statuses: Vec<CoilAlarmStatusRow>,
    image_join_logs: Vec<ImageJoinLogRow>,
    defect_statistics: Vec<DefectStatisticsRow>,
    alarm_flat_roll_data: Vec<AlarmFlatRollDataRow>,
    cap_true_logs: Vec<CapTrueLogRow>,
    cap_true_log_items: Vec<CapTrueLogItemRow>,
    coil_state_delay: Option<Duration>,
}

impl Default for InMemoryCoilRepository {
    fn default() -> Self {
        Self {
            coils: Arc::new(Mutex::new(Vec::new())),
            detected_coils: Vec::new(),
            secondary_coils: Vec::new(),
            coil_rows: Vec::new(),
            defects: Vec::new(),
            manual_defects: Arc::new(Mutex::new(Vec::new())),
            coil_states: Vec::new(),
            plc_data: Vec::new(),
            coil_checks: Arc::new(Mutex::new(Vec::new())),
            point_data: Vec::new(),
            line_data: Vec::new(),
            defect_classes: Vec::new(),
            next_code_dict: Vec::new(),
            alarm_infos: Vec::new(),
            alarm_flat_rolls: Vec::new(),
            alarm_taper_shapes: Vec::new(),
            alarm_loose_coils: Vec::new(),
            taper_shape_points: Vec::new(),
            server_detection_errors: Vec::new(),
            defect_checks: Vec::new(),
            data_ellipses: Vec::new(),
            deep_points: Vec::new(),
            detection_speeds: Vec::new(),
            coil_alarm_statuses: Vec::new(),
            image_join_logs: Vec::new(),
            defect_statistics: Vec::new(),
            alarm_flat_roll_data: Vec::new(),
            cap_true_logs: Vec::new(),
            cap_true_log_items: Vec::new(),
            coil_state_delay: None,
        }
    }
}

impl InMemoryCoilRepository {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_coils(self, coils: Vec<CoilSummaryRow>) -> Self {
        *self.coils.lock().expect("coil lock") = coils;
        self
    }

    pub fn with_detected_coils(mut self, detected_coils: Vec<CoilSummaryRow>) -> Self {
        self.detected_coils = detected_coils;
        self
    }

    pub fn with_secondary_coils(mut self, secondary_coils: Vec<SecondaryCoilRow>) -> Self {
        self.secondary_coils = secondary_coils;
        self
    }

    pub fn with_coil_rows(mut self, coil_rows: Vec<CoilRow>) -> Self {
        self.coil_rows = coil_rows;
        self
    }

    pub fn with_defects(mut self, defects: Vec<CoilDefectRow>) -> Self {
        self.defects = defects;
        self
    }

    pub fn with_manual_defects(self, manual_defects: Vec<ManualDefectRow>) -> Self {
        *self.manual_defects.lock().expect("manual defect lock") = manual_defects;
        self
    }

    pub fn with_coil_checks(self, coil_checks: Vec<CoilCheckRow>) -> Self {
        *self.coil_checks.lock().expect("coil check lock") = coil_checks;
        self
    }

    pub fn with_coil_states(mut self, coil_states: Vec<CoilStateRow>) -> Self {
        self.coil_states = coil_states;
        self
    }

    pub fn with_coil_state_delay(mut self, delay: Duration) -> Self {
        self.coil_state_delay = Some(delay);
        self
    }

    pub fn with_plc_data(mut self, plc_data: Vec<PlcDataRow>) -> Self {
        self.plc_data = plc_data;
        self
    }

    pub fn with_point_data(mut self, point_data: Vec<PointDataRow>) -> Self {
        self.point_data = point_data;
        self
    }

    pub fn with_line_data(mut self, line_data: Vec<LineDataRow>) -> Self {
        self.line_data = line_data;
        self
    }

    pub fn with_defect_classes(mut self, defect_classes: Vec<DefectClassDictRow>) -> Self {
        self.defect_classes = defect_classes;
        self
    }

    pub fn with_next_code_dict(mut self, next_code_dict: Vec<NextCodeDictRow>) -> Self {
        self.next_code_dict = next_code_dict;
        self
    }

    pub fn with_alarm_infos(mut self, alarm_infos: Vec<AlarmInfoSummaryRow>) -> Self {
        self.alarm_infos = alarm_infos;
        self
    }

    pub fn with_alarm_flat_rolls(mut self, alarm_flat_rolls: Vec<AlarmFlatRollRow>) -> Self {
        self.alarm_flat_rolls = alarm_flat_rolls;
        self
    }

    pub fn with_alarm_taper_shapes(mut self, alarm_taper_shapes: Vec<AlarmTaperShapeRow>) -> Self {
        self.alarm_taper_shapes = alarm_taper_shapes;
        self
    }

    pub fn with_alarm_loose_coils(mut self, alarm_loose_coils: Vec<AlarmLooseCoilRow>) -> Self {
        self.alarm_loose_coils = alarm_loose_coils;
        self
    }

    pub fn with_taper_shape_points(mut self, taper_shape_points: Vec<TaperShapePointRow>) -> Self {
        self.taper_shape_points = taper_shape_points;
        self
    }

    pub fn with_server_detection_errors(
        mut self,
        server_detection_errors: Vec<ServerDetectionErrorRow>,
    ) -> Self {
        self.server_detection_errors = server_detection_errors;
        self
    }

    pub fn with_defect_checks(mut self, defect_checks: Vec<DefectCheckRow>) -> Self {
        self.defect_checks = defect_checks;
        self
    }

    pub fn with_data_ellipses(mut self, data_ellipses: Vec<DataEllipseRow>) -> Self {
        self.data_ellipses = data_ellipses;
        self
    }

    pub fn with_deep_points(mut self, deep_points: Vec<DeepPointRow>) -> Self {
        self.deep_points = deep_points;
        self
    }

    pub fn with_detection_speeds(mut self, detection_speeds: Vec<DetectionSpeedRow>) -> Self {
        self.detection_speeds = detection_speeds;
        self
    }

    pub fn with_coil_alarm_statuses(
        mut self,
        coil_alarm_statuses: Vec<CoilAlarmStatusRow>,
    ) -> Self {
        self.coil_alarm_statuses = coil_alarm_statuses;
        self
    }

    pub fn with_image_join_logs(mut self, image_join_logs: Vec<ImageJoinLogRow>) -> Self {
        self.image_join_logs = image_join_logs;
        self
    }

    pub fn with_defect_statistics(mut self, defect_statistics: Vec<DefectStatisticsRow>) -> Self {
        self.defect_statistics = defect_statistics;
        self
    }

    pub fn with_alarm_flat_roll_data(
        mut self,
        alarm_flat_roll_data: Vec<AlarmFlatRollDataRow>,
    ) -> Self {
        self.alarm_flat_roll_data = alarm_flat_roll_data;
        self
    }

    pub fn with_cap_true_logs(mut self, cap_true_logs: Vec<CapTrueLogRow>) -> Self {
        self.cap_true_logs = cap_true_logs;
        self
    }

    pub fn with_cap_true_log_items(mut self, cap_true_log_items: Vec<CapTrueLogItemRow>) -> Self {
        self.cap_true_log_items = cap_true_log_items;
        self
    }

    fn coil_snapshot(&self) -> Vec<CoilSummaryRow> {
        self.coils.lock().expect("coil lock").clone()
    }
}

#[derive(Debug)]
struct SummarySyncValues {
    defect_count_s: i32,
    defect_count_l: i32,
    max_defect_name: String,
    max_defect_level: i32,
    max_defect_surface: String,
    max_defect_is_shown: bool,
}

#[derive(Clone, Debug)]
struct SurfaceAlarmSummary {
    has_alarm: bool,
    defect_grad: i32,
    taper_shape_grad: i32,
    loose_coil_grad: i32,
    flat_roll_grad: i32,
    grad: i32,
    next_code: Option<String>,
    next_name: Option<String>,
}

#[derive(Clone, Debug)]
struct AlarmSyncValues {
    has_alarm_info: bool,
    s: SurfaceAlarmSummary,
    l: SurfaceAlarmSummary,
    next_code: Option<String>,
    next_info: Option<String>,
}

fn default_surface_alarm_summary() -> SurfaceAlarmSummary {
    SurfaceAlarmSummary {
        has_alarm: false,
        defect_grad: 1,
        taper_shape_grad: 1,
        loose_coil_grad: 1,
        flat_roll_grad: 1,
        grad: 1,
        next_code: None,
        next_name: None,
    }
}

fn defect_class_lookup(defect_classes: &[DefectClassDictRow]) -> HashMap<String, (i32, bool)> {
    defect_classes
        .iter()
        .map(|row| {
            (
                row.defect_name.clone(),
                (row.defect_level.unwrap_or(1), row.visible.unwrap_or(1) != 0),
            )
        })
        .collect()
}

fn summary_sync_values(
    coil_id: i64,
    defects: &[CoilDefectRow],
    defect_classes: &[DefectClassDictRow],
) -> SummarySyncValues {
    let lookup = defect_class_lookup(defect_classes);
    let mut max_defect: Option<&CoilDefectRow> = None;
    let mut max_level = -1;
    let mut defect_count_s = 0;
    let mut defect_count_l = 0;

    for defect in defects
        .iter()
        .filter(|defect| defect.secondary_coil_id == coil_id)
    {
        if defect.surface.eq_ignore_ascii_case("S") {
            defect_count_s += 1;
        } else if defect.surface.eq_ignore_ascii_case("L") {
            defect_count_l += 1;
        }

        let (level, is_shown) = lookup
            .get(&defect.defect_name)
            .copied()
            .unwrap_or((1, true));
        if is_shown && level > max_level {
            max_level = level;
            max_defect = Some(defect);
        }
    }

    if let Some(defect) = max_defect {
        return SummarySyncValues {
            defect_count_s,
            defect_count_l,
            max_defect_name: defect.defect_name.clone(),
            max_defect_level: max_level.max(0),
            max_defect_surface: if defect.surface.trim().is_empty() {
                "S".to_string()
            } else {
                defect.surface.clone()
            },
            max_defect_is_shown: true,
        };
    }

    SummarySyncValues {
        defect_count_s,
        defect_count_l,
        max_defect_name: String::new(),
        max_defect_level: 0,
        max_defect_surface: String::new(),
        max_defect_is_shown: defects
            .iter()
            .all(|defect| defect.secondary_coil_id != coil_id),
    }
}

fn decode_next_code(weight: Option<f64>) -> Option<String> {
    let value = weight?;
    if !value.is_finite() || value == 0.0 {
        return None;
    }
    char::from_u32(value as u32).map(|code| code.to_string())
}

fn non_empty_string(value: Option<&str>) -> Option<String> {
    value
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
}

fn surface_alarm_sync_value(
    coil_id: i64,
    surface: &str,
    alarm_infos: &[AlarmInfoSummaryRow],
) -> SurfaceAlarmSummary {
    let Some(alarm) = alarm_infos
        .iter()
        .find(|row| row.secondary_coil_id == coil_id && row.surface.eq_ignore_ascii_case(surface))
    else {
        return default_surface_alarm_summary();
    };

    let defect_grad = if alarm.defect_grad == 0 {
        1
    } else {
        alarm.defect_grad
    };
    let taper_shape_grad = if alarm.taper_shape_grad == 0 {
        1
    } else {
        alarm.taper_shape_grad
    };
    let loose_coil_grad = if alarm.loose_coil_grad == 0 {
        1
    } else {
        alarm.loose_coil_grad
    };
    let flat_roll_grad = if alarm.flat_roll_grad == 0 {
        1
    } else {
        alarm.flat_roll_grad
    };
    let fallback_grad = defect_grad
        .max(taper_shape_grad)
        .max(loose_coil_grad)
        .max(flat_roll_grad);
    let grad = if alarm.grad == 0 {
        fallback_grad
    } else {
        alarm.grad
    };

    SurfaceAlarmSummary {
        has_alarm: true,
        defect_grad,
        taper_shape_grad,
        loose_coil_grad,
        flat_roll_grad,
        grad,
        next_code: non_empty_string(alarm.next_code.as_deref()),
        next_name: non_empty_string(alarm.next_name.as_deref()),
    }
}

fn alarm_sync_values(
    coil_id: i64,
    source_next_code: Option<&str>,
    source_next_info: Option<&str>,
    alarm_infos: &[AlarmInfoSummaryRow],
) -> AlarmSyncValues {
    let s = surface_alarm_sync_value(coil_id, "S", alarm_infos);
    let l = surface_alarm_sync_value(coil_id, "L", alarm_infos);
    let mut next_code = non_empty_string(source_next_code);
    let mut next_info = non_empty_string(source_next_info);

    if let Some(code) = s.next_code.as_ref() {
        next_code = Some(code.clone());
        next_info = s.next_name.clone().or_else(|| Some(String::new()));
    }

    if next_info.as_deref().unwrap_or("").is_empty() {
        if let Some(code) = l.next_code.as_ref() {
            next_code = Some(code.clone());
            next_info = l.next_name.clone().or_else(|| Some(String::new()));
        }
    }

    AlarmSyncValues {
        has_alarm_info: s.has_alarm || l.has_alarm,
        s,
        l,
        next_code,
        next_info,
    }
}

fn apply_alarm_sync_values(row: &mut CoilSummaryRow, values: &AlarmSyncValues) {
    row.has_alarm_info = values.has_alarm_info;
    row.s_defect_grad = values.s.defect_grad;
    row.s_taper_shape_grad = values.s.taper_shape_grad;
    row.s_loose_coil_grad = values.s.loose_coil_grad;
    row.s_flat_roll_grad = values.s.flat_roll_grad;
    row.s_grad = values.s.grad;
    row.s_has_alarm = values.s.has_alarm;
    row.s_next_code = values.s.next_code.clone();
    row.s_next_name = values.s.next_name.clone();
    row.l_defect_grad = values.l.defect_grad;
    row.l_taper_shape_grad = values.l.taper_shape_grad;
    row.l_loose_coil_grad = values.l.loose_coil_grad;
    row.l_flat_roll_grad = values.l.flat_roll_grad;
    row.l_grad = values.l.grad;
    row.l_has_alarm = values.l.has_alarm;
    row.l_next_code = values.l.next_code.clone();
    row.l_next_name = values.l.next_name.clone();
    row.next_code = values.next_code.clone();
    row.next_info = values.next_info.clone();
}

fn parse_python_datetime_minute(value: &str) -> Option<NaiveDateTime> {
    NaiveDateTime::parse_from_str(value, "%Y%m%d%H%M").ok()
}

fn parse_sql_datetime_second(value: &str) -> Option<NaiveDateTime> {
    NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S")
        .or_else(|_| NaiveDateTime::parse_from_str(value, "%Y-%m-%dT%H:%M:%S"))
        .ok()
}

#[async_trait]
impl CoilRepository for InMemoryCoilRepository {
    async fn list_coils(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        Ok(self
            .coil_snapshot()
            .into_iter()
            .take(limit as usize)
            .collect())
    }

    async fn search_coils_recent(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| coil.has_coil)
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        rows.truncate(limit.clamp(1, 1000) as usize);
        Ok(rows)
    }

    async fn search_coils_recent_for_export(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let mut rows = self.coil_snapshot().into_iter().collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        rows.truncate(limit.clamp(1, 1000) as usize);
        Ok(rows)
    }

    async fn latest_coil(&self) -> Result<Option<LatestCoilRow>> {
        Ok(self.coil_snapshot().first().map(|row| LatestCoilRow {
            id: row.id,
            secondary_coil_id: row.id,
            detection_time: row.detection_time.clone(),
            defect_count_s: Some(row.defect_count_s),
            defect_count_l: Some(row.defect_count_l),
            check_status: Some(row.check_status),
            status_l: Some(row.status_l),
            status_s: Some(row.status_s),
            grade: Some(row.grade),
            msg: Some(String::new()),
        }))
    }

    async fn list_coils_after(&self, coil_id: i64, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| coil.id > coil_id && coil.has_coil)
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        rows.truncate(limit as usize);
        Ok(rows)
    }

    async fn grader_list(&self, limit: u32) -> Result<Vec<GraderRow>> {
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .map(GraderRow::from)
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        rows.truncate(limit as usize);
        Ok(rows)
    }

    async fn coil_detail(&self, coil_id: i64) -> Result<Option<GraderRow>> {
        Ok(self
            .coil_snapshot()
            .into_iter()
            .find(|coil| coil.id == coil_id)
            .map(GraderRow::from))
    }

    async fn alarm_infos(&self, coil_id: i64) -> Result<Vec<AlarmInfoSummaryRow>> {
        let mut rows = self
            .alarm_infos
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_alarm_infos(&self) -> Result<Vec<AlarmInfoSummaryRow>> {
        let mut rows = self.alarm_infos.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn search_coils_by_no(&self, coil_no: &str) -> Result<Vec<CoilSummaryRow>> {
        Ok(self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| coil.has_coil && coil.coil_no.contains(coil_no))
            .collect())
    }

    async fn search_coils_by_id(&self, coil_id: i64) -> Result<Vec<CoilSummaryRow>> {
        Ok(self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| coil.has_coil && coil.id == coil_id)
            .collect())
    }

    async fn search_coils_by_id_range(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilSummaryRow>> {
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| coil.id >= start_coil_id && coil.id <= end_coil_id)
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        Ok(rows)
    }

    async fn search_coils_by_datetime(
        &self,
        start: &str,
        end: &str,
    ) -> Result<Vec<CoilSummaryRow>> {
        let Some(start_time) = parse_python_datetime_minute(start) else {
            return Ok(Vec::new());
        };
        let Some(end_time) = parse_python_datetime_minute(end) else {
            return Ok(Vec::new());
        };
        let min_time = start_time.min(end_time);
        let max_time = start_time.max(end_time);
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| {
                coil.has_coil
                    && coil
                        .create_time
                        .as_deref()
                        .and_then(parse_sql_datetime_second)
                        .is_some_and(|create_time| {
                            create_time >= min_time && create_time <= max_time
                        })
            })
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        Ok(rows)
    }

    async fn search_coils_by_datetime_for_export(
        &self,
        start: &str,
        end: &str,
    ) -> Result<Vec<CoilSummaryRow>> {
        let Some(start_time) = parse_python_datetime_minute(start) else {
            return Ok(Vec::new());
        };
        let Some(end_time) = parse_python_datetime_minute(end) else {
            return Ok(Vec::new());
        };
        let min_time = start_time.min(end_time);
        let max_time = start_time.max(end_time);
        let mut rows = self
            .coil_snapshot()
            .into_iter()
            .filter(|coil| {
                coil
                    .create_time
                    .as_deref()
                    .and_then(parse_sql_datetime_second)
                    .is_some_and(|create_time| {
                        create_time >= min_time && create_time <= max_time
                    })
            })
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        Ok(rows)
    }

    async fn backup_secondary_coils(&self) -> Result<Vec<SecondaryCoilRow>> {
        let mut rows = if self.secondary_coils.is_empty() {
            self.coil_snapshot()
                .into_iter()
                .map(|row| SecondaryCoilRow {
                    id: row.id,
                    coil_no: row.coil_no,
                    coil_type: row.coil_type,
                    coil_inside: row.coil_inside,
                    coil_dia: row.coil_dia,
                    thickness: row.thickness,
                    width: row.width,
                    weight: row.weight,
                    act_width: row.act_width,
                    create_time: row.create_time,
                })
                .collect::<Vec<_>>()
        } else {
            self.secondary_coils.clone()
        };
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn secondary_coils(&self, coil_id: i64) -> Result<Vec<SecondaryCoilRow>> {
        let mut rows = self
            .secondary_coils
            .iter()
            .filter(|row| row.id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn coil_rows(&self, coil_id: i64) -> Result<Vec<CoilRow>> {
        let mut rows = self
            .coil_rows
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_coil_rows(&self) -> Result<Vec<CoilRow>> {
        let mut rows = self.coil_rows.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn defects(&self, coil_id: i64, surface: &str) -> Result<Vec<CoilDefectRow>> {
        let mut rows = self
            .defects
            .iter()
            .filter(|defect| {
                defect.secondary_coil_id == coil_id && defect.surface.eq_ignore_ascii_case(surface)
            })
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn defects_between(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilDefectRow>> {
        let mut rows = self
            .defects
            .iter()
            .filter(|defect| {
                defect.secondary_coil_id >= start_coil_id && defect.secondary_coil_id <= end_coil_id
            })
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| {
            left.secondary_coil_id
                .cmp(&right.secondary_coil_id)
                .then_with(|| left.id.cmp(&right.id))
        });
        Ok(rows)
    }

    async fn backup_defects(&self) -> Result<Vec<CoilDefectRow>> {
        let mut rows = self.defects.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn manual_defects(&self, coil_id: i64, surface: &str) -> Result<Vec<ManualDefectRow>> {
        let mut rows = self
            .manual_defects
            .lock()
            .expect("manual defect lock")
            .iter()
            .filter(|defect| {
                defect.secondary_coil_id == coil_id && defect.surface.eq_ignore_ascii_case(surface)
            })
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_manual_defects(&self) -> Result<Vec<ManualDefectRow>> {
        let mut rows = self
            .manual_defects
            .lock()
            .expect("manual defect lock")
            .clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn add_manual_defect(&self, defect: ManualDefectWrite) -> Result<ManualDefectRow> {
        let mut rows = self.manual_defects.lock().expect("manual defect lock");
        let next_id = rows.iter().map(|row| row.id).max().unwrap_or(0) + 1;
        let row = ManualDefectRow {
            id: next_id,
            secondary_coil_id: defect.secondary_coil_id.unwrap_or_default(),
            surface: defect.surface.unwrap_or_else(|| "S".to_string()),
            defect_class: 0,
            defect_name: defect.defect_name.unwrap_or_else(|| "未知缺陷".to_string()),
            defect_status: defect.defect_status.unwrap_or(1),
            defect_time: None,
            defect_x: defect.defect_x.unwrap_or_default(),
            defect_y: defect.defect_y.unwrap_or_default(),
            defect_w: defect.defect_w.unwrap_or_default(),
            defect_h: defect.defect_h.unwrap_or_default(),
            defect_source: 0.0,
            defect_data: defect.defect_data,
            remark: Some(defect.remark.unwrap_or_default()),
            annotator: Some(defect.annotator.unwrap_or_else(|| "系统用户".to_string())),
        };
        rows.push(row.clone());
        Ok(row)
    }

    async fn update_manual_defect(
        &self,
        defect_id: i64,
        defect: ManualDefectWrite,
    ) -> Result<Option<ManualDefectRow>> {
        let mut rows = self.manual_defects.lock().expect("manual defect lock");
        let Some(row) = rows.iter_mut().find(|row| row.id == defect_id) else {
            return Ok(None);
        };
        if let Some(defect_name) = defect.defect_name {
            row.defect_name = defect_name;
            row.defect_class = 0;
        }
        if let Some(defect_status) = defect.defect_status {
            row.defect_status = defect_status;
        }
        if let Some(defect_x) = defect.defect_x {
            row.defect_x = defect_x;
        }
        if let Some(defect_y) = defect.defect_y {
            row.defect_y = defect_y;
        }
        if let Some(defect_w) = defect.defect_w {
            row.defect_w = defect_w;
        }
        if let Some(defect_h) = defect.defect_h {
            row.defect_h = defect_h;
        }
        if let Some(defect_data) = defect.defect_data {
            row.defect_data = Some(defect_data);
        }
        if let Some(remark) = defect.remark {
            row.remark = Some(remark);
        }
        if let Some(annotator) = defect.annotator {
            row.annotator = Some(annotator);
        }
        Ok(Some(row.clone()))
    }

    async fn delete_manual_defect(&self, defect_id: i64) -> Result<bool> {
        let mut rows = self.manual_defects.lock().expect("manual defect lock");
        let previous_len = rows.len();
        rows.retain(|row| row.id != defect_id);
        Ok(rows.len() != previous_len)
    }

    async fn coil_check(&self, coil_id: i64) -> Result<Option<CoilCheckRow>> {
        Ok(self
            .coil_checks
            .lock()
            .expect("coil check lock")
            .iter()
            .find(|item| item.secondary_coil_id == coil_id)
            .cloned())
    }

    async fn coil_checks(&self, coil_id: i64) -> Result<Vec<CoilCheckRow>> {
        let mut rows = self
            .coil_checks
            .lock()
            .expect("coil check lock")
            .iter()
            .filter(|item| item.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_coil_checks(&self) -> Result<Vec<CoilCheckRow>> {
        let mut rows = self.coil_checks.lock().expect("coil check lock").clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn set_coil_check(&self, coil_id: i64, status: i32, msg: &str) -> Result<()> {
        let mut rows = self.coil_checks.lock().expect("coil check lock");
        if let Some(row) = rows
            .iter_mut()
            .find(|item| item.secondary_coil_id == coil_id)
        {
            row.status = status;
            row.msg = msg.to_string();
            return Ok(());
        }
        let next_id = rows.iter().map(|row| row.id).max().unwrap_or(0) + 1;
        rows.push(CoilCheckRow {
            id: next_id,
            secondary_coil_id: coil_id,
            status,
            msg: msg.to_string(),
        });
        Ok(())
    }

    async fn coil_states(&self, coil_id: i64) -> Result<Vec<CoilStateRow>> {
        let mut rows = self
            .coil_states
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| right.id.cmp(&left.id));
        rows.truncate(2);
        Ok(rows)
    }

    async fn backup_coil_states(&self) -> Result<Vec<CoilStateRow>> {
        let mut rows = self.coil_states.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn coil_state(&self, coil_id: i64, surface: &str) -> Result<Option<CoilStateRow>> {
        if let Some(delay) = self.coil_state_delay {
            std::thread::sleep(delay);
        }
        Ok(self
            .coil_states
            .iter()
            .filter(|row| {
                row.secondary_coil_id == coil_id && row.surface.eq_ignore_ascii_case(surface)
            })
            .max_by_key(|row| row.id)
            .cloned())
    }

    async fn plc_data(&self, coil_id: i64) -> Result<Option<PlcDataRow>> {
        Ok(self
            .plc_data
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .max_by_key(|row| row.id)
            .cloned())
    }

    async fn backup_plc_data(&self) -> Result<Vec<PlcDataRow>> {
        let mut rows = self.plc_data.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn plc_curve_rows(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcDataRow>> {
        Ok(in_memory_latest_plc_rows(
            &self.plc_data,
            start_id,
            end_id,
            limit,
        ))
    }

    async fn plc_curve_all(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcCurveAllRow>> {
        let plc_rows = in_memory_latest_plc_rows(&self.plc_data, start_id, end_id, limit);
        let coils = self.coil_snapshot();
        Ok(plc_rows
            .into_iter()
            .map(|row| {
                let median_3d_mm_s =
                    latest_state_median(&self.coil_states, row.secondary_coil_id, "S");
                let median_3d_mm_l =
                    latest_state_median(&self.coil_states, row.secondary_coil_id, "L");
                let median_3d_mm_avg = match (median_3d_mm_s, median_3d_mm_l) {
                    (Some(s), Some(l)) => Some((s + l) / 2.0),
                    _ => None,
                };
                let width = coils
                    .iter()
                    .find(|coil| coil.id == row.secondary_coil_id)
                    .and_then(|coil| coil.act_width);
                PlcCurveAllRow {
                    coil_id: row.secondary_coil_id,
                    time: row.start_time,
                    location_s: row.location_s,
                    location_l: row.location_l,
                    location_laser: row.location_laser,
                    median_3d_mm_s,
                    median_3d_mm_l,
                    median_3d_mm_avg,
                    width,
                }
            })
            .collect())
    }

    async fn point_data(&self, coil_id: i64, surface: &str) -> Result<Vec<PointDataRow>> {
        let mut rows = self
            .point_data
            .iter()
            .filter(|row| {
                row.secondary_coil_id == coil_id && row.surface.eq_ignore_ascii_case(surface)
            })
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_point_data(&self) -> Result<Vec<PointDataRow>> {
        let mut rows = self.point_data.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn line_data(&self, coil_id: i64, surface: &str) -> Result<Vec<LineDataRow>> {
        let mut rows = self
            .line_data
            .iter()
            .filter(|row| {
                row.secondary_coil_id == coil_id && row.surface.eq_ignore_ascii_case(surface)
            })
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_line_data(&self) -> Result<Vec<LineDataRow>> {
        let mut rows = self.line_data.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn defect_class_dict(&self) -> Result<Vec<DefectClassDictRow>> {
        let mut rows = self.defect_classes.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn next_code_dict(&self) -> Result<Vec<NextCodeDictRow>> {
        let mut rows = self.next_code_dict.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn server_detection_errors(&self, coil_id: i64) -> Result<Vec<ServerDetectionErrorRow>> {
        let mut rows = self
            .server_detection_errors
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_server_detection_errors(&self) -> Result<Vec<ServerDetectionErrorRow>> {
        let mut rows = self.server_detection_errors.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn defect_checks(&self, coil_id: i64) -> Result<Vec<DefectCheckRow>> {
        let mut rows = self
            .defect_checks
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_defect_checks(&self) -> Result<Vec<DefectCheckRow>> {
        let mut rows = self.defect_checks.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn data_ellipses(&self, coil_id: i64) -> Result<Vec<DataEllipseRow>> {
        let mut rows = self
            .data_ellipses
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_data_ellipses(&self) -> Result<Vec<DataEllipseRow>> {
        let mut rows = self.data_ellipses.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn deep_points(&self, coil_id: i64) -> Result<Vec<DeepPointRow>> {
        let mut rows = self
            .deep_points
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_deep_points(&self) -> Result<Vec<DeepPointRow>> {
        let mut rows = self.deep_points.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn detection_speeds(&self, coil_id: i64) -> Result<Vec<DetectionSpeedRow>> {
        let mut rows = self
            .detection_speeds
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_detection_speeds(&self) -> Result<Vec<DetectionSpeedRow>> {
        let mut rows = self.detection_speeds.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn coil_alarm_statuses(&self, coil_id: i64) -> Result<Vec<CoilAlarmStatusRow>> {
        let mut rows = self
            .coil_alarm_statuses
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_coil_alarm_statuses(&self) -> Result<Vec<CoilAlarmStatusRow>> {
        let mut rows = self.coil_alarm_statuses.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn image_join_logs(&self, coil_id: i64) -> Result<Vec<ImageJoinLogRow>> {
        let mut rows = self
            .image_join_logs
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_image_join_logs(&self) -> Result<Vec<ImageJoinLogRow>> {
        let mut rows = self.image_join_logs.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn defect_statistics(&self, coil_id: i64) -> Result<Vec<DefectStatisticsRow>> {
        let mut rows = self
            .defect_statistics
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_defect_statistics(&self) -> Result<Vec<DefectStatisticsRow>> {
        let mut rows = self.defect_statistics.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn alarm_flat_roll_data(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollDataRow>> {
        let mut rows = self
            .alarm_flat_roll_data
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_alarm_flat_roll_data(&self) -> Result<Vec<AlarmFlatRollDataRow>> {
        let mut rows = self.alarm_flat_roll_data.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn cap_true_logs(&self, coil_id: i64) -> Result<Vec<CapTrueLogRow>> {
        let mut rows = self
            .cap_true_logs
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_cap_true_logs(&self) -> Result<Vec<CapTrueLogRow>> {
        let mut rows = self.cap_true_logs.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn cap_true_log_items(&self, coil_id: i64) -> Result<Vec<CapTrueLogItemRow>> {
        let mut rows = self
            .cap_true_log_items
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_cap_true_log_items(&self) -> Result<Vec<CapTrueLogItemRow>> {
        let mut rows = self.cap_true_log_items.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn sync_missing_summaries(&self, limit: u32) -> Result<usize> {
        let mut inserted = 0;
        let mut coils = self.coils.lock().expect("coil lock");

        for detected_coil in self.detected_coils.iter().take(limit as usize) {
            if coils.iter().any(|row| row.id == detected_coil.id) {
                continue;
            }

            let values = summary_sync_values(detected_coil.id, &self.defects, &self.defect_classes);
            let mut row = detected_coil.clone();
            row.defect_count_s = values.defect_count_s;
            row.defect_count_l = values.defect_count_l;
            row.max_defect_name = Some(values.max_defect_name);
            row.max_defect_level = values.max_defect_level;
            row.max_defect_surface = Some(values.max_defect_surface);
            let alarm_values = alarm_sync_values(
                detected_coil.id,
                detected_coil.next_code.as_deref(),
                detected_coil.next_info.as_deref(),
                &self.alarm_infos,
            );
            apply_alarm_sync_values(&mut row, &alarm_values);
            row.has_coil = true;
            coils.push(row);
            inserted += 1;
        }

        Ok(inserted)
    }

    async fn sync_existing_summaries(&self, coil_ids: &[i64]) -> Result<usize> {
        let mut updated = 0;
        let mut coils = self.coils.lock().expect("coil lock");
        for coil_id in coil_ids {
            let Some(row) = coils.iter_mut().find(|row| row.id == *coil_id) else {
                continue;
            };
            let values = summary_sync_values(*coil_id, &self.defects, &self.defect_classes);
            row.defect_count_s = values.defect_count_s;
            row.defect_count_l = values.defect_count_l;
            row.max_defect_name = Some(values.max_defect_name);
            row.max_defect_level = values.max_defect_level;
            row.max_defect_surface = Some(values.max_defect_surface);
            let alarm_values = alarm_sync_values(
                *coil_id,
                row.next_code.as_deref(),
                row.next_info.as_deref(),
                &self.alarm_infos,
            );
            apply_alarm_sync_values(row, &alarm_values);
            updated += 1;
        }
        Ok(updated)
    }

    async fn alarm_flat_rolls(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollRow>> {
        let mut rows = self
            .alarm_flat_rolls
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        rows.truncate(2);
        Ok(rows)
    }

    async fn backup_alarm_flat_rolls(&self) -> Result<Vec<AlarmFlatRollRow>> {
        let mut rows = self.alarm_flat_rolls.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn alarm_taper_shapes(&self, coil_id: i64) -> Result<Vec<AlarmTaperShapeRow>> {
        let mut rows = self
            .alarm_taper_shapes
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_alarm_taper_shapes(&self) -> Result<Vec<AlarmTaperShapeRow>> {
        let mut rows = self.alarm_taper_shapes.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn alarm_loose_coils(&self, coil_id: i64) -> Result<Vec<AlarmLooseCoilRow>> {
        let mut rows = self
            .alarm_loose_coils
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_alarm_loose_coils(&self) -> Result<Vec<AlarmLooseCoilRow>> {
        let mut rows = self.alarm_loose_coils.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn taper_shape_points(&self, coil_id: i64) -> Result<Vec<TaperShapePointRow>> {
        let mut rows = self
            .taper_shape_points
            .iter()
            .filter(|row| row.secondary_coil_id == coil_id)
            .cloned()
            .collect::<Vec<_>>();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }

    async fn backup_taper_shape_points(&self) -> Result<Vec<TaperShapePointRow>> {
        let mut rows = self.taper_shape_points.clone();
        rows.sort_by(|left, right| left.id.cmp(&right.id));
        Ok(rows)
    }
}

fn in_memory_latest_plc_rows(
    rows: &[PlcDataRow],
    start_id: i64,
    end_id: i64,
    limit: u32,
) -> Vec<PlcDataRow> {
    let (start_id, end_id, limit, order_desc) = normalize_plc_curve_args(start_id, end_id, limit);
    let mut latest_by_coil: HashMap<i64, PlcDataRow> = HashMap::new();
    for row in rows {
        if start_id != 0 && row.secondary_coil_id < start_id {
            continue;
        }
        if end_id != 0 && row.secondary_coil_id > end_id {
            continue;
        }
        let replace = latest_by_coil
            .get(&row.secondary_coil_id)
            .is_none_or(|existing| row.id > existing.id);
        if replace {
            latest_by_coil.insert(row.secondary_coil_id, row.clone());
        }
    }

    let mut latest_rows = latest_by_coil.into_values().collect::<Vec<_>>();
    if order_desc {
        latest_rows.sort_by(|left, right| right.secondary_coil_id.cmp(&left.secondary_coil_id));
        latest_rows.truncate(limit as usize);
        latest_rows.reverse();
    } else {
        latest_rows.sort_by(|left, right| left.secondary_coil_id.cmp(&right.secondary_coil_id));
        latest_rows.truncate(limit as usize);
    }
    latest_rows
}

fn latest_state_median(rows: &[CoilStateRow], coil_id: i64, surface: &str) -> Option<f64> {
    rows.iter()
        .filter(|row| row.secondary_coil_id == coil_id && row.surface.eq_ignore_ascii_case(surface))
        .max_by_key(|row| row.id)
        .and_then(|row| row.median_3d_mm)
}

fn defect_data_for_storage(value: Option<Value>) -> String {
    match value {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(value)) => value,
        Some(value) => value.to_string(),
    }
}

fn normalize_plc_curve_args(start_id: i64, end_id: i64, limit: u32) -> (i64, i64, u32, bool) {
    let mut start_id = start_id;
    let mut end_id = end_id;
    let limit = limit.clamp(1, 2000);
    if start_id != 0 && end_id != 0 && start_id > end_id {
        std::mem::swap(&mut start_id, &mut end_id);
    }
    let order_desc = start_id == 0 && end_id == 0;
    (start_id, end_id, limit, order_desc)
}

pub struct MySqlCoilRepository {
    pool: MySqlPool,
}

impl MySqlCoilRepository {
    pub async fn connect(database_url: &str) -> Result<Self> {
        let pool = MySqlPoolOptions::new()
            .max_connections(10)
            .connect(database_url)
            .await?;
        Ok(Self { pool })
    }

    async fn defects_for_summary(&self, coil_id: i64) -> Result<Vec<CoilDefectRow>> {
        let rows = sqlx::query_as::<_, CoilDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(defectTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data
            FROM CoilDefect
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn missing_summary_source(&self, coil_id: i64) -> Result<Option<CoilSummaryRow>> {
        let mut row = sqlx::query_as::<_, CoilSummaryRow>(
            r#"
            SELECT
                secondary_coil.Id AS id,
                COALESCE(secondary_coil.CoilNo, '') AS coil_no,
                DATE_FORMAT(secondary_coil.CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
                secondary_coil.CoilType AS coil_type,
                secondary_coil.CoilInside AS coil_inside,
                secondary_coil.CoilDia AS coil_dia,
                secondary_coil.Thickness AS thickness,
                secondary_coil.Width AS width,
                secondary_coil.Weight AS weight,
                secondary_coil.ActWidth AS act_width,
                NULL AS next_code,
                NULL AS next_info,
                1 AS s_defect_grad,
                1 AS s_taper_shape_grad,
                1 AS s_loose_coil_grad,
                1 AS s_flat_roll_grad,
                1 AS s_grad,
                FALSE AS s_has_alarm,
                NULL AS s_next_code,
                NULL AS s_next_name,
                1 AS l_defect_grad,
                1 AS l_taper_shape_grad,
                1 AS l_loose_coil_grad,
                1 AS l_flat_roll_grad,
                1 AS l_grad,
                FALSE AS l_has_alarm,
                NULL AS l_next_code,
                NULL AS l_next_name,
                0 AS defect_count_s,
                0 AS defect_count_l,
                DATE_FORMAT(child_coil.DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                COALESCE(child_coil.CheckStatus, 0) AS check_status,
                COALESCE(child_coil.Status_L, 0) AS status_l,
                COALESCE(child_coil.Status_S, 0) AS status_s,
                COALESCE(child_coil.Grade, 0) AS grade,
                NULL AS max_defect_name,
                0 AS max_defect_level,
                NULL AS max_defect_surface,
                child_coil.Id IS NOT NULL AS has_coil,
                FALSE AS has_alarm_info
            FROM SecondaryCoil secondary_coil
            LEFT JOIN Coil child_coil ON child_coil.Id = (
                SELECT latest_child.Id
                FROM Coil latest_child
                WHERE latest_child.SecondaryCoilId = secondary_coil.Id
                ORDER BY latest_child.DetectionTime DESC, latest_child.Id DESC
                LIMIT 1
            )
            WHERE secondary_coil.Id = ?
            LIMIT 1
            "#,
        )
        .bind(coil_id)
        .fetch_optional(&self.pool)
        .await?;

        if let Some(row) = row.as_mut() {
            row.next_code = decode_next_code(row.weight);
        }

        Ok(row)
    }

    async fn insert_summary(
        &self,
        row: &CoilSummaryRow,
        values: &SummarySyncValues,
    ) -> Result<bool> {
        let result = sqlx::query(
            r#"
            INSERT IGNORE INTO coil_summary (
                Id, CoilNo, CreateTime, CoilType, CoilInside, CoilDia, Thickness, Width, Weight,
                ActWidth, NextCode, NextInfo, S_DefectGrad, S_TaperShapeGrad, S_LooseCoilGrad,
                S_FlatRollGrad, S_Grad, S_HasAlarm, S_NextCode, S_NextName, L_DefectGrad,
                L_TaperShapeGrad, L_LooseCoilGrad, L_FlatRollGrad, L_Grad, L_HasAlarm,
                L_NextCode, L_NextName, DefectCountS, DefectCountL, DetectionTime, CheckStatus,
                Status_L, Status_S, Grade, HasCoil, MaxDefectName, MaxDefectLevel,
                MaxDefectSurface, MaxDefectIsShown, UpdateTime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
            "#,
        )
        .bind(row.id)
        .bind(row.coil_no.as_str())
        .bind(row.create_time.as_deref())
        .bind(row.coil_type.as_deref())
        .bind(row.coil_inside)
        .bind(row.coil_dia)
        .bind(row.thickness)
        .bind(row.width)
        .bind(row.weight)
        .bind(row.act_width)
        .bind(row.next_code.as_deref())
        .bind(row.next_info.as_deref())
        .bind(row.s_defect_grad)
        .bind(row.s_taper_shape_grad)
        .bind(row.s_loose_coil_grad)
        .bind(row.s_flat_roll_grad)
        .bind(row.s_grad)
        .bind(row.s_has_alarm)
        .bind(row.s_next_code.as_deref())
        .bind(row.s_next_name.as_deref())
        .bind(row.l_defect_grad)
        .bind(row.l_taper_shape_grad)
        .bind(row.l_loose_coil_grad)
        .bind(row.l_flat_roll_grad)
        .bind(row.l_grad)
        .bind(row.l_has_alarm)
        .bind(row.l_next_code.as_deref())
        .bind(row.l_next_name.as_deref())
        .bind(values.defect_count_s)
        .bind(values.defect_count_l)
        .bind(row.detection_time.as_deref())
        .bind(row.check_status)
        .bind(row.status_l)
        .bind(row.status_s)
        .bind(row.grade)
        .bind(row.has_coil)
        .bind(values.max_defect_name.as_str())
        .bind(values.max_defect_level)
        .bind(values.max_defect_surface.as_str())
        .bind(values.max_defect_is_shown)
        .execute(&self.pool)
        .await?;

        Ok(result.rows_affected() > 0)
    }

    async fn alarm_infos_for_summary(&self, coil_id: i64) -> Result<Vec<AlarmInfoSummaryRow>> {
        let rows = sqlx::query_as::<_, AlarmInfoSummaryRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                nextCode AS next_code,
                nextName AS next_name,
                taperShapeMsg AS taper_shape_msg,
                looseCoilMsg AS loose_coil_msg,
                flatRollMsg AS flat_roll_msg,
                defectMsg AS defect_msg,
                COALESCE(defectGrad, 0) AS defect_grad,
                COALESCE(taperShapeGrad, 0) AS taper_shape_grad,
                COALESCE(looseCoilGrad, 0) AS loose_coil_grad,
                COALESCE(flatRollGrad, 0) AS flat_roll_grad,
                COALESCE(grad, 0) AS grad,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
                data
            FROM AlarmInfo
            WHERE secondaryCoilId = ?
              AND surface IN ('S', 'L')
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn query_coils(&self, sql: &str, bind: QueryBind<'_>) -> Result<Vec<CoilSummaryRow>> {
        let mut query = sqlx::query_as::<_, CoilSummaryRow>(sql);
        match bind {
            QueryBind::None => {}
            QueryBind::I64(value) => {
                query = query.bind(value);
            }
            QueryBind::IdRange(start, end) => {
                query = query.bind(start).bind(end);
            }
            QueryBind::String(value) => {
                query = query.bind(value);
            }
            QueryBind::DateRange(start, end) => {
                query = query.bind(start).bind(end);
            }
        }
        Ok(query.fetch_all(&self.pool).await?)
    }

    async fn defect_class_for_name(&self, defect_name: &str) -> Result<i32> {
        Ok(sqlx::query_scalar::<_, i32>(
            r#"
            SELECT COALESCE(defectClass, 0)
            FROM DefectClassDict
            WHERE defectName = ?
            LIMIT 1
            "#,
        )
        .bind(defect_name)
        .fetch_optional(&self.pool)
        .await?
        .unwrap_or(0))
    }

    async fn manual_defect_by_id(&self, defect_id: i64) -> Result<Option<ManualDefectRow>> {
        let row = sqlx::query_as::<_, ManualDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(createTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data,
                remark,
                annotator
            FROM ManualDefect
            WHERE Id = ?
            LIMIT 1
            "#,
        )
        .bind(defect_id)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(Into::into))
    }
}

enum QueryBind<'a> {
    None,
    I64(i64),
    IdRange(i64, i64),
    String(String),
    DateRange(&'a str, &'a str),
}

const COIL_SUMMARY_SELECT: &str = r#"
SELECT
    Id AS id,
    COALESCE(CoilNo, '') AS coil_no,
    DATE_FORMAT(CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
    CoilType AS coil_type,
    CoilInside AS coil_inside,
    CoilDia AS coil_dia,
    Thickness AS thickness,
    Width AS width,
    Weight AS weight,
    ActWidth AS act_width,
    NextCode AS next_code,
    NextInfo AS next_info,
    COALESCE(S_DefectGrad, 1) AS s_defect_grad,
    COALESCE(S_TaperShapeGrad, 1) AS s_taper_shape_grad,
    COALESCE(S_LooseCoilGrad, 1) AS s_loose_coil_grad,
    COALESCE(S_FlatRollGrad, 1) AS s_flat_roll_grad,
    COALESCE(S_Grad, 1) AS s_grad,
    COALESCE(S_HasAlarm, 0) AS s_has_alarm,
    S_NextCode AS s_next_code,
    S_NextName AS s_next_name,
    COALESCE(L_DefectGrad, 1) AS l_defect_grad,
    COALESCE(L_TaperShapeGrad, 1) AS l_taper_shape_grad,
    COALESCE(L_LooseCoilGrad, 1) AS l_loose_coil_grad,
    COALESCE(L_FlatRollGrad, 1) AS l_flat_roll_grad,
    COALESCE(L_Grad, 1) AS l_grad,
    COALESCE(L_HasAlarm, 0) AS l_has_alarm,
    L_NextCode AS l_next_code,
    L_NextName AS l_next_name,
    COALESCE(DefectCountS, 0) AS defect_count_s,
    COALESCE(DefectCountL, 0) AS defect_count_l,
    DATE_FORMAT(DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
    COALESCE(CheckStatus, 0) AS check_status,
    COALESCE(Status_L, 0) AS status_l,
    COALESCE(Status_S, 0) AS status_s,
    COALESCE(Grade, 0) AS grade,
    MaxDefectName AS max_defect_name,
    COALESCE(MaxDefectLevel, 0) AS max_defect_level,
    MaxDefectSurface AS max_defect_surface,
    COALESCE(HasCoil, 0) AS has_coil,
    IF(COALESCE(S_HasAlarm, 0) OR COALESCE(L_HasAlarm, 0), TRUE, FALSE) AS has_alarm_info
FROM coil_summary
"#;

#[async_trait]
impl CoilRepository for MySqlCoilRepository {
    async fn list_coils(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let limit = limit.clamp(1, 1000);
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 ORDER BY Id DESC LIMIT {limit}"
        );
        self.query_coils(&sql, QueryBind::None).await
    }

    async fn search_coils_recent(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let limit = limit.clamp(1, 1000);
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 ORDER BY Id DESC LIMIT {limit}"
        );
        self.query_coils(&sql, QueryBind::None).await
    }

    async fn search_coils_recent_for_export(&self, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let limit = limit.clamp(1, 1000);
        let sql = format!("{COIL_SUMMARY_SELECT} ORDER BY Id DESC LIMIT {limit}");
        self.query_coils(&sql, QueryBind::None).await
    }

    async fn latest_coil(&self) -> Result<Option<LatestCoilRow>> {
        let row = sqlx::query_as::<_, LatestCoilRow>(
            r#"
            SELECT
                Id AS id,
                SecondaryCoilId AS secondary_coil_id,
                DATE_FORMAT(DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                DefectCountS AS defect_count_s,
                DefectCountL AS defect_count_l,
                CheckStatus AS check_status,
                Status_L AS status_l,
                Status_S AS status_s,
                Grade AS grade,
                Msg AS msg
            FROM Coil
            ORDER BY Id DESC
            LIMIT 1
            "#,
        )
        .fetch_optional(&self.pool)
        .await?;
        Ok(row)
    }

    async fn list_coils_after(&self, coil_id: i64, limit: u32) -> Result<Vec<CoilSummaryRow>> {
        let limit = limit.clamp(1, 1000);
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 AND Id > ? ORDER BY Id DESC LIMIT {limit}"
        );
        self.query_coils(&sql, QueryBind::I64(coil_id)).await
    }

    async fn grader_list(&self, limit: u32) -> Result<Vec<GraderRow>> {
        let limit = limit.clamp(1, 1000);
        let rows = sqlx::query_as::<_, GraderSqlRow>(
            r#"
            SELECT
                secondary_coil.Id AS id,
                COALESCE(secondary_coil.CoilNo, '') AS coil_no,
                DATE_FORMAT(secondary_coil.CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
                secondary_coil.CoilType AS coil_type,
                secondary_coil.CoilInside AS coil_inside,
                secondary_coil.CoilDia AS coil_dia,
                secondary_coil.Thickness AS thickness,
                secondary_coil.Width AS width,
                secondary_coil.Weight AS weight,
                secondary_coil.ActWidth AS act_width,
                child_coil.Id AS child_id,
                child_coil.SecondaryCoilId AS child_secondary_coil_id,
                DATE_FORMAT(child_coil.DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                child_coil.DefectCountS AS defect_count_s,
                child_coil.DefectCountL AS defect_count_l,
                child_coil.CheckStatus AS check_status,
                child_coil.Status_L AS status_l,
                child_coil.Status_S AS status_s,
                child_coil.Grade AS grade,
                child_coil.Msg AS msg
            FROM SecondaryCoil secondary_coil
            LEFT JOIN (
                SELECT SecondaryCoilId, MIN(Id) AS child_id
                FROM Coil
                GROUP BY SecondaryCoilId
            ) first_child ON first_child.SecondaryCoilId = secondary_coil.Id
            LEFT JOIN Coil child_coil ON child_coil.Id = first_child.child_id
            ORDER BY secondary_coil.Id DESC
            LIMIT ?
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn coil_detail(&self, coil_id: i64) -> Result<Option<GraderRow>> {
        let row = sqlx::query_as::<_, GraderSqlRow>(
            r#"
            SELECT
                secondary_coil.Id AS id,
                COALESCE(secondary_coil.CoilNo, '') AS coil_no,
                DATE_FORMAT(secondary_coil.CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
                secondary_coil.CoilType AS coil_type,
                secondary_coil.CoilInside AS coil_inside,
                secondary_coil.CoilDia AS coil_dia,
                secondary_coil.Thickness AS thickness,
                secondary_coil.Width AS width,
                secondary_coil.Weight AS weight,
                secondary_coil.ActWidth AS act_width,
                child_coil.Id AS child_id,
                child_coil.SecondaryCoilId AS child_secondary_coil_id,
                DATE_FORMAT(child_coil.DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                child_coil.DefectCountS AS defect_count_s,
                child_coil.DefectCountL AS defect_count_l,
                child_coil.CheckStatus AS check_status,
                child_coil.Status_L AS status_l,
                child_coil.Status_S AS status_s,
                child_coil.Grade AS grade,
                child_coil.Msg AS msg
            FROM SecondaryCoil secondary_coil
            LEFT JOIN (
                SELECT SecondaryCoilId, MAX(Id) AS child_id
                FROM Coil
                GROUP BY SecondaryCoilId
            ) latest_child ON latest_child.SecondaryCoilId = secondary_coil.Id
            LEFT JOIN Coil child_coil ON child_coil.Id = latest_child.child_id
            WHERE secondary_coil.Id = ?
            LIMIT 1
            "#,
        )
        .bind(coil_id)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(Into::into))
    }

    async fn alarm_infos(&self, coil_id: i64) -> Result<Vec<AlarmInfoSummaryRow>> {
        self.alarm_infos_for_summary(coil_id).await
    }

    async fn backup_alarm_infos(&self) -> Result<Vec<AlarmInfoSummaryRow>> {
        let rows = sqlx::query_as::<_, AlarmInfoSummaryRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                nextCode AS next_code,
                nextName AS next_name,
                taperShapeMsg AS taper_shape_msg,
                looseCoilMsg AS loose_coil_msg,
                flatRollMsg AS flat_roll_msg,
                defectMsg AS defect_msg,
                COALESCE(defectGrad, 0) AS defect_grad,
                COALESCE(taperShapeGrad, 0) AS taper_shape_grad,
                COALESCE(looseCoilGrad, 0) AS loose_coil_grad,
                COALESCE(flatRollGrad, 0) AS flat_roll_grad,
                COALESCE(grad, 0) AS grad,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS create_time,
                data
            FROM AlarmInfo
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn search_coils_by_no(&self, coil_no: &str) -> Result<Vec<CoilSummaryRow>> {
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 AND CoilNo LIKE ? ORDER BY Id DESC LIMIT 200"
        );
        self.query_coils(&sql, QueryBind::String(format!("%{coil_no}%")))
            .await
    }

    async fn search_coils_by_id(&self, coil_id: i64) -> Result<Vec<CoilSummaryRow>> {
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 AND Id = ? ORDER BY Id DESC LIMIT 200"
        );
        self.query_coils(&sql, QueryBind::I64(coil_id)).await
    }

    async fn search_coils_by_id_range(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilSummaryRow>> {
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE Id >= ? AND Id <= ? ORDER BY Id DESC"
        );
        self.query_coils(&sql, QueryBind::IdRange(start_coil_id, end_coil_id))
            .await
    }

    async fn search_coils_by_datetime(
        &self,
        start: &str,
        end: &str,
    ) -> Result<Vec<CoilSummaryRow>> {
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE COALESCE(HasCoil, 0) = 1 AND CreateTime >= STR_TO_DATE(?, '%Y%m%d%H%i') AND CreateTime <= STR_TO_DATE(?, '%Y%m%d%H%i') ORDER BY Id DESC LIMIT 500"
        );
        self.query_coils(&sql, QueryBind::DateRange(start, end))
            .await
    }

    async fn search_coils_by_datetime_for_export(
        &self,
        start: &str,
        end: &str,
    ) -> Result<Vec<CoilSummaryRow>> {
        let sql = format!(
            "{COIL_SUMMARY_SELECT} WHERE CreateTime >= STR_TO_DATE(?, '%Y%m%d%H%i') AND CreateTime <= STR_TO_DATE(?, '%Y%m%d%H%i') ORDER BY Id DESC"
        );
        self.query_coils(&sql, QueryBind::DateRange(start, end))
            .await
    }

    async fn backup_secondary_coils(&self) -> Result<Vec<SecondaryCoilRow>> {
        let rows = sqlx::query_as::<_, SecondaryCoilRow>(
            r#"
            SELECT
                Id AS id,
                COALESCE(CoilNo, '') AS coil_no,
                CoilType AS coil_type,
                CoilInside AS coil_inside,
                CoilDia AS coil_dia,
                Thickness AS thickness,
                Width AS width,
                Weight AS weight,
                ActWidth AS act_width,
                DATE_FORMAT(CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time
            FROM SecondaryCoil
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn secondary_coils(&self, coil_id: i64) -> Result<Vec<SecondaryCoilRow>> {
        let rows = sqlx::query_as::<_, SecondaryCoilRow>(
            r#"
            SELECT
                Id AS id,
                COALESCE(CoilNo, '') AS coil_no,
                CoilType AS coil_type,
                CoilInside AS coil_inside,
                CoilDia AS coil_dia,
                Thickness AS thickness,
                Width AS width,
                Weight AS weight,
                ActWidth AS act_width,
                DATE_FORMAT(CreateTime, '%Y-%m-%d %H:%i:%s') AS create_time
            FROM SecondaryCoil
            WHERE Id = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn coil_rows(&self, coil_id: i64) -> Result<Vec<CoilRow>> {
        let rows = sqlx::query_as::<_, CoilRow>(
            r#"
            SELECT
                Id AS id,
                SecondaryCoilId AS secondary_coil_id,
                DATE_FORMAT(DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                DefectCountS AS defect_count_s,
                DefectCountL AS defect_count_l,
                CheckStatus AS check_status,
                Status_L AS status_l,
                Status_S AS status_s,
                Grade AS grade,
                Msg AS msg
            FROM Coil
            WHERE SecondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_coil_rows(&self) -> Result<Vec<CoilRow>> {
        let rows = sqlx::query_as::<_, CoilRow>(
            r#"
            SELECT
                Id AS id,
                SecondaryCoilId AS secondary_coil_id,
                DATE_FORMAT(DetectionTime, '%Y-%m-%d %H:%i:%s') AS detection_time,
                DefectCountS AS defect_count_s,
                DefectCountL AS defect_count_l,
                CheckStatus AS check_status,
                Status_L AS status_l,
                Status_S AS status_s,
                Grade AS grade,
                Msg AS msg
            FROM Coil
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn defects(&self, coil_id: i64, surface: &str) -> Result<Vec<CoilDefectRow>> {
        let rows = sqlx::query_as::<_, CoilDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(defectTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data
            FROM CoilDefect
            WHERE secondaryCoilId = ? AND surface = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .bind(surface)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn defects_between(
        &self,
        start_coil_id: i64,
        end_coil_id: i64,
    ) -> Result<Vec<CoilDefectRow>> {
        let rows = sqlx::query_as::<_, CoilDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(defectTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data
            FROM CoilDefect
            WHERE secondaryCoilId >= ? AND secondaryCoilId <= ?
            ORDER BY secondaryCoilId ASC, Id ASC
            "#,
        )
        .bind(start_coil_id)
        .bind(end_coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn backup_defects(&self) -> Result<Vec<CoilDefectRow>> {
        let rows = sqlx::query_as::<_, CoilDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(defectTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data
            FROM CoilDefect
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn manual_defects(&self, coil_id: i64, surface: &str) -> Result<Vec<ManualDefectRow>> {
        let rows = sqlx::query_as::<_, ManualDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(createTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data,
                remark,
                annotator
            FROM ManualDefect
            WHERE secondaryCoilId = ? AND surface = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .bind(surface)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn backup_manual_defects(&self) -> Result<Vec<ManualDefectRow>> {
        let rows = sqlx::query_as::<_, ManualDefectSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                COALESCE(defectStatus, 0) AS defect_status,
                DATE_FORMAT(createTime, '%Y-%m-%d %H:%i:%s') AS defect_time,
                COALESCE(defectX, 0) AS defect_x,
                COALESCE(defectY, 0) AS defect_y,
                COALESCE(defectW, 0) AS defect_w,
                COALESCE(defectH, 0) AS defect_h,
                COALESCE(defectSource, 0) AS defect_source,
                defectData AS defect_data,
                remark,
                annotator
            FROM ManualDefect
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn add_manual_defect(&self, defect: ManualDefectWrite) -> Result<ManualDefectRow> {
        let defect_name = defect
            .defect_name
            .clone()
            .unwrap_or_else(|| "未知缺陷".to_string());
        let defect_class = self.defect_class_for_name(&defect_name).await?;
        let result = sqlx::query(
            r#"
            INSERT INTO ManualDefect (
                secondaryCoilId,
                surface,
                defectClass,
                defectName,
                defectStatus,
                defectX,
                defectY,
                defectW,
                defectH,
                defectSource,
                defectData,
                remark,
                annotator
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(defect.secondary_coil_id.unwrap_or_default())
        .bind(defect.surface.as_deref().unwrap_or("S"))
        .bind(defect_class)
        .bind(defect_name)
        .bind(defect.defect_status.unwrap_or(1))
        .bind(defect.defect_x.unwrap_or_default())
        .bind(defect.defect_y.unwrap_or_default())
        .bind(defect.defect_w.unwrap_or_default())
        .bind(defect.defect_h.unwrap_or_default())
        .bind(0)
        .bind(defect_data_for_storage(defect.defect_data))
        .bind(defect.remark.unwrap_or_default())
        .bind(defect.annotator.unwrap_or_else(|| "系统用户".to_string()))
        .execute(&self.pool)
        .await?;

        let defect_id = result.last_insert_id() as i64;
        self.manual_defect_by_id(defect_id)
            .await?
            .ok_or_else(|| anyhow::anyhow!("manual defect insert failed"))
    }

    async fn update_manual_defect(
        &self,
        defect_id: i64,
        defect: ManualDefectWrite,
    ) -> Result<Option<ManualDefectRow>> {
        let Some(mut current) = self.manual_defect_by_id(defect_id).await? else {
            return Ok(None);
        };

        if let Some(defect_name) = defect.defect_name {
            current.defect_class = self.defect_class_for_name(&defect_name).await?;
            current.defect_name = defect_name;
        }
        if let Some(defect_status) = defect.defect_status {
            current.defect_status = defect_status;
        }
        if let Some(defect_x) = defect.defect_x {
            current.defect_x = defect_x;
        }
        if let Some(defect_y) = defect.defect_y {
            current.defect_y = defect_y;
        }
        if let Some(defect_w) = defect.defect_w {
            current.defect_w = defect_w;
        }
        if let Some(defect_h) = defect.defect_h {
            current.defect_h = defect_h;
        }
        if let Some(defect_data) = defect.defect_data {
            current.defect_data = Some(defect_data);
        }
        if let Some(remark) = defect.remark {
            current.remark = Some(remark);
        }
        if let Some(annotator) = defect.annotator {
            current.annotator = Some(annotator);
        }

        sqlx::query(
            r#"
            UPDATE ManualDefect
            SET
                defectClass = ?,
                defectName = ?,
                defectStatus = ?,
                defectX = ?,
                defectY = ?,
                defectW = ?,
                defectH = ?,
                defectData = ?,
                remark = ?,
                annotator = ?
            WHERE Id = ?
            LIMIT 1
            "#,
        )
        .bind(current.defect_class)
        .bind(&current.defect_name)
        .bind(current.defect_status)
        .bind(current.defect_x)
        .bind(current.defect_y)
        .bind(current.defect_w)
        .bind(current.defect_h)
        .bind(defect_data_for_storage(current.defect_data.clone()))
        .bind(current.remark.clone().unwrap_or_default())
        .bind(current.annotator.clone().unwrap_or_default())
        .bind(defect_id)
        .execute(&self.pool)
        .await?;

        self.manual_defect_by_id(defect_id).await
    }

    async fn delete_manual_defect(&self, defect_id: i64) -> Result<bool> {
        let result = sqlx::query(
            r#"
            DELETE FROM ManualDefect
            WHERE Id = ?
            LIMIT 1
            "#,
        )
        .bind(defect_id)
        .execute(&self.pool)
        .await?;
        Ok(result.rows_affected() > 0)
    }

    async fn coil_check(&self, coil_id: i64) -> Result<Option<CoilCheckRow>> {
        let row = sqlx::query_as::<_, CoilCheckRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(status, 0) AS status,
                COALESCE(msg, '') AS msg
            FROM CoilCheck
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            LIMIT 1
            "#,
        )
        .bind(coil_id)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row)
    }

    async fn coil_checks(&self, coil_id: i64) -> Result<Vec<CoilCheckRow>> {
        let rows = sqlx::query_as::<_, CoilCheckRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(status, 0) AS status,
                COALESCE(msg, '') AS msg
            FROM CoilCheck
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_coil_checks(&self) -> Result<Vec<CoilCheckRow>> {
        let rows = sqlx::query_as::<_, CoilCheckRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(status, 0) AS status,
                COALESCE(msg, '') AS msg
            FROM CoilCheck
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn set_coil_check(&self, coil_id: i64, status: i32, msg: &str) -> Result<()> {
        let result = sqlx::query(
            r#"
            UPDATE CoilCheck
            SET status = ?, msg = ?
            WHERE secondaryCoilId = ?
            LIMIT 1
            "#,
        )
        .bind(status)
        .bind(msg)
        .bind(coil_id)
        .execute(&self.pool)
        .await?;

        if result.rows_affected() == 0 {
            sqlx::query(
                r#"
                INSERT INTO CoilCheck (secondaryCoilId, status, msg)
                VALUES (?, ?, ?)
                "#,
            )
            .bind(coil_id)
            .bind(status)
            .bind(msg)
            .execute(&self.pool)
            .await?;
        }
        Ok(())
    }

    async fn coil_states(&self, coil_id: i64) -> Result<Vec<CoilStateRow>> {
        let rows = sqlx::query_as::<_, CoilStateSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                scan3dCoordinateScaleX AS scan3d_coordinate_scale_x,
                scan3dCoordinateScaleY AS scan3d_coordinate_scale_y,
                scan3dCoordinateScaleZ AS scan3d_coordinate_scale_z,
                rotate,
                x_rotate,
                median_3d,
                median_3d_mm,
                colorFromValue_mm AS color_from_value_mm,
                colorToValue_mm AS color_to_value_mm,
                start,
                step,
                upperLimit AS upper_limit,
                lowerLimit AS lower_limit,
                lowerArea AS lower_area,
                upperArea AS upper_area,
                lowerArea_percent AS lower_area_percent,
                upperArea_percent AS upper_area_percent,
                mask_area,
                width,
                height,
                jsonData AS json_data
            FROM CoilState
            WHERE secondaryCoilId = ?
            ORDER BY Id DESC
            LIMIT 2
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn backup_coil_states(&self) -> Result<Vec<CoilStateRow>> {
        let rows = sqlx::query_as::<_, CoilStateSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                scan3dCoordinateScaleX AS scan3d_coordinate_scale_x,
                scan3dCoordinateScaleY AS scan3d_coordinate_scale_y,
                scan3dCoordinateScaleZ AS scan3d_coordinate_scale_z,
                rotate,
                x_rotate,
                median_3d,
                median_3d_mm,
                colorFromValue_mm AS color_from_value_mm,
                colorToValue_mm AS color_to_value_mm,
                start,
                step,
                upperLimit AS upper_limit,
                lowerLimit AS lower_limit,
                lowerArea AS lower_area,
                upperArea AS upper_area,
                lowerArea_percent AS lower_area_percent,
                upperArea_percent AS upper_area_percent,
                mask_area,
                width,
                height,
                jsonData AS json_data
            FROM CoilState
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn coil_state(&self, coil_id: i64, surface: &str) -> Result<Option<CoilStateRow>> {
        let row = sqlx::query_as::<_, CoilStateSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                scan3dCoordinateScaleX AS scan3d_coordinate_scale_x,
                scan3dCoordinateScaleY AS scan3d_coordinate_scale_y,
                scan3dCoordinateScaleZ AS scan3d_coordinate_scale_z,
                rotate,
                x_rotate,
                median_3d,
                median_3d_mm,
                colorFromValue_mm AS color_from_value_mm,
                colorToValue_mm AS color_to_value_mm,
                start,
                step,
                upperLimit AS upper_limit,
                lowerLimit AS lower_limit,
                lowerArea AS lower_area,
                upperArea AS upper_area,
                lowerArea_percent AS lower_area_percent,
                upperArea_percent AS upper_area_percent,
                mask_area,
                width,
                height,
                jsonData AS json_data
            FROM CoilState
            WHERE secondaryCoilId = ? AND surface = ?
            ORDER BY Id DESC
            LIMIT 1
            "#,
        )
        .bind(coil_id)
        .bind(surface)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(Into::into))
    }

    async fn plc_data(&self, coil_id: i64) -> Result<Option<PlcDataRow>> {
        let row = sqlx::query_as::<_, PlcDataSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                location_S AS location_s,
                location_L AS location_l,
                location_laser,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                pclData AS pcl_data
            FROM PlcData
            WHERE secondaryCoilId = ?
            ORDER BY Id DESC
            LIMIT 1
            "#,
        )
        .bind(coil_id)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(Into::into))
    }

    async fn backup_plc_data(&self) -> Result<Vec<PlcDataRow>> {
        let rows = sqlx::query_as::<_, PlcDataSqlRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                location_S AS location_s,
                location_L AS location_l,
                location_laser,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                pclData AS pcl_data
            FROM PlcData
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows.into_iter().map(Into::into).collect())
    }

    async fn plc_curve_rows(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcDataRow>> {
        let (start_id, end_id, limit, order_desc) =
            normalize_plc_curve_args(start_id, end_id, limit);
        let order = if order_desc { "DESC" } else { "ASC" };
        let sql = format!(
            r#"
            SELECT
                pd.Id AS id,
                pd.secondaryCoilId AS secondary_coil_id,
                pd.location_S AS location_s,
                pd.location_L AS location_l,
                pd.location_laser,
                DATE_FORMAT(pd.startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                pd.pclData AS pcl_data
            FROM PlcData pd
            INNER JOIN (
                SELECT secondaryCoilId, MAX(Id) AS max_id
                FROM PlcData
                WHERE (? = 0 OR secondaryCoilId >= ?)
                  AND (? = 0 OR secondaryCoilId <= ?)
                GROUP BY secondaryCoilId
            ) latest ON pd.Id = latest.max_id
            ORDER BY pd.secondaryCoilId {order}
            LIMIT ?
            "#
        );
        let mut rows = sqlx::query_as::<_, PlcDataSqlRow>(&sql)
            .bind(start_id)
            .bind(start_id)
            .bind(end_id)
            .bind(end_id)
            .bind(limit)
            .fetch_all(&self.pool)
            .await?
            .into_iter()
            .map(Into::into)
            .collect::<Vec<_>>();
        if order_desc {
            rows.reverse();
        }
        Ok(rows)
    }

    async fn plc_curve_all(
        &self,
        start_id: i64,
        end_id: i64,
        limit: u32,
    ) -> Result<Vec<PlcCurveAllRow>> {
        let (start_id, end_id, limit, order_desc) =
            normalize_plc_curve_args(start_id, end_id, limit);
        let order = if order_desc { "DESC" } else { "ASC" };
        let sql = format!(
            r#"
            SELECT
                pd.secondaryCoilId AS coil_id,
                DATE_FORMAT(pd.startTime, '%Y-%m-%d %H:%i:%s') AS time,
                pd.location_S AS location_s,
                pd.location_L AS location_l,
                pd.location_laser,
                state_s.median_3d_mm AS median_3d_mm_s,
                state_l.median_3d_mm AS median_3d_mm_l,
                IF(
                    state_s.median_3d_mm IS NOT NULL AND state_l.median_3d_mm IS NOT NULL,
                    (state_s.median_3d_mm + state_l.median_3d_mm) / 2,
                    NULL
                ) AS median_3d_mm_avg,
                secondary_coil.ActWidth AS width
            FROM PlcData pd
            INNER JOIN (
                SELECT secondaryCoilId, MAX(Id) AS max_id
                FROM PlcData
                WHERE (? = 0 OR secondaryCoilId >= ?)
                  AND (? = 0 OR secondaryCoilId <= ?)
                GROUP BY secondaryCoilId
            ) latest_plc ON pd.Id = latest_plc.max_id
            LEFT JOIN (
                SELECT secondaryCoilId, MAX(Id) AS max_id
                FROM CoilState
                WHERE surface = 'S'
                GROUP BY secondaryCoilId
            ) latest_state_s ON latest_state_s.secondaryCoilId = pd.secondaryCoilId
            LEFT JOIN CoilState state_s ON state_s.Id = latest_state_s.max_id
            LEFT JOIN (
                SELECT secondaryCoilId, MAX(Id) AS max_id
                FROM CoilState
                WHERE surface = 'L'
                GROUP BY secondaryCoilId
            ) latest_state_l ON latest_state_l.secondaryCoilId = pd.secondaryCoilId
            LEFT JOIN CoilState state_l ON state_l.Id = latest_state_l.max_id
            LEFT JOIN SecondaryCoil secondary_coil ON secondary_coil.Id = pd.secondaryCoilId
            ORDER BY pd.secondaryCoilId {order}
            LIMIT ?
            "#
        );
        let mut rows = sqlx::query_as::<_, PlcCurveAllSqlRow>(&sql)
            .bind(start_id)
            .bind(start_id)
            .bind(end_id)
            .bind(end_id)
            .bind(limit)
            .fetch_all(&self.pool)
            .await?
            .into_iter()
            .map(Into::into)
            .collect::<Vec<_>>();
        if order_desc {
            rows.reverse();
        }
        Ok(rows)
    }

    async fn point_data(&self, coil_id: i64, surface: &str) -> Result<Vec<PointDataRow>> {
        let rows = sqlx::query_as::<_, PointDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                type AS point_type,
                x,
                y,
                z,
                z_mm,
                data,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time
            FROM PointData
            WHERE secondaryCoilId = ? AND surface = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .bind(surface)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_point_data(&self) -> Result<Vec<PointDataRow>> {
        let rows = sqlx::query_as::<_, PointDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                type AS point_type,
                x,
                y,
                z,
                z_mm,
                data,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time
            FROM PointData
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn line_data(&self, coil_id: i64, surface: &str) -> Result<Vec<LineDataRow>> {
        let rows = sqlx::query_as::<_, LineDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                type AS line_type,
                center_x,
                center_y,
                width,
                height,
                rotation_angle,
                x1,
                y1,
                x2,
                y2,
                data,
                inner_min_value,
                inner_min_value_mm,
                inner_max_value,
                inner_max_value_mm,
                outer_min_value,
                outer_min_value_mm,
                outer_max_value,
                outer_max_value_mm,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time
            FROM LineData
            WHERE secondaryCoilId = ? AND surface = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .bind(surface)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_line_data(&self) -> Result<Vec<LineDataRow>> {
        let rows = sqlx::query_as::<_, LineDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                type AS line_type,
                center_x,
                center_y,
                width,
                height,
                rotation_angle,
                x1,
                y1,
                x2,
                y2,
                data,
                inner_min_value,
                inner_min_value_mm,
                inner_max_value,
                inner_max_value_mm,
                outer_min_value,
                outer_min_value_mm,
                outer_max_value,
                outer_max_value_mm,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time
            FROM LineData
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn defect_class_dict(&self) -> Result<Vec<DefectClassDictRow>> {
        let rows = sqlx::query_as::<_, DefectClassDictRow>(
            r#"
            SELECT
                Id AS id,
                COALESCE(defectClass, 0) AS defect_class,
                COALESCE(defectName, '') AS defect_name,
                defectType AS defect_type,
                defectColor AS defect_color,
                defectLevel AS defect_level,
                visible,
                defectDesc AS defect_desc
            FROM DefectClassDict
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn next_code_dict(&self) -> Result<Vec<NextCodeDictRow>> {
        let rows = sqlx::query_as::<_, NextCodeDictRow>(
            r#"
            SELECT
                Id AS id,
                code,
                info
            FROM NextCodeDict
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn server_detection_errors(&self, coil_id: i64) -> Result<Vec<ServerDetectionErrorRow>> {
        let rows = sqlx::query_as::<_, ServerDetectionErrorRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                errorType AS error_type,
                DATE_FORMAT(time, '%Y-%m-%d %H:%i:%s') AS time,
                msg
            FROM ServerDetectionError
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_server_detection_errors(&self) -> Result<Vec<ServerDetectionErrorRow>> {
        let rows = sqlx::query_as::<_, ServerDetectionErrorRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                errorType AS error_type,
                DATE_FORMAT(time, '%Y-%m-%d %H:%i:%s') AS time,
                msg
            FROM ServerDetectionError
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn defect_checks(&self, coil_id: i64) -> Result<Vec<DefectCheckRow>> {
        let rows = sqlx::query_as::<_, DefectCheckRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                defectId AS defect_id,
                `key`,
                status,
                oldDefectId AS old_defect_id,
                oldDefectName AS old_defect_name,
                newDefectId AS new_defect_id,
                newDefectName AS new_defect_name,
                DATE_FORMAT(addTime, '%Y-%m-%d %H:%i:%s') AS add_time,
                msg
            FROM DefectCheck
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_defect_checks(&self) -> Result<Vec<DefectCheckRow>> {
        let rows = sqlx::query_as::<_, DefectCheckRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                defectId AS defect_id,
                `key`,
                status,
                oldDefectId AS old_defect_id,
                oldDefectName AS old_defect_name,
                newDefectId AS new_defect_id,
                newDefectName AS new_defect_name,
                DATE_FORMAT(addTime, '%Y-%m-%d %H:%i:%s') AS add_time,
                msg
            FROM DefectCheck
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn data_ellipses(&self, coil_id: i64) -> Result<Vec<DataEllipseRow>> {
        let rows = sqlx::query_as::<_, DataEllipseRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                type AS ellipse_type,
                center_x,
                center_y,
                width,
                height,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM DataEllipse
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_data_ellipses(&self) -> Result<Vec<DataEllipseRow>> {
        let rows = sqlx::query_as::<_, DataEllipseRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                type AS ellipse_type,
                center_x,
                center_y,
                width,
                height,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM DataEllipse
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn deep_points(&self, coil_id: i64) -> Result<Vec<DeepPointRow>> {
        let rows = sqlx::query_as::<_, DeepPointRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                x,
                y,
                x_mm,
                y_mm,
                value,
                value_int,
                by_user,
                draw,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM DeepPoint
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_deep_points(&self) -> Result<Vec<DeepPointRow>> {
        let rows = sqlx::query_as::<_, DeepPointRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                x,
                y,
                x_mm,
                y_mm,
                value,
                value_int,
                by_user,
                draw,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM DeepPoint
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn detection_speeds(&self, coil_id: i64) -> Result<Vec<DetectionSpeedRow>> {
        let rows = sqlx::query_as::<_, DetectionSpeedRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                DATE_FORMAT(endTime, '%Y-%m-%d %H:%i:%s') AS end_time,
                allTime AS all_time
            FROM DetectionSpeed
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_detection_speeds(&self) -> Result<Vec<DetectionSpeedRow>> {
        let rows = sqlx::query_as::<_, DetectionSpeedRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                DATE_FORMAT(startTime, '%Y-%m-%d %H:%i:%s') AS start_time,
                DATE_FORMAT(endTime, '%Y-%m-%d %H:%i:%s') AS end_time,
                allTime AS all_time
            FROM DetectionSpeed
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn coil_alarm_statuses(&self, coil_id: i64) -> Result<Vec<CoilAlarmStatusRow>> {
        let rows = sqlx::query_as::<_, CoilAlarmStatusRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                level,
                alarmStatus AS alarm_status,
                alarmFlatRoll AS alarm_flat_roll,
                alarmTaper AS alarm_taper,
                alarmFolding AS alarm_folding,
                alarmDefect AS alarm_defect,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM CoilAlarmStatus
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_coil_alarm_statuses(&self) -> Result<Vec<CoilAlarmStatusRow>> {
        let rows = sqlx::query_as::<_, CoilAlarmStatusRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                level,
                alarmStatus AS alarm_status,
                alarmFlatRoll AS alarm_flat_roll,
                alarmTaper AS alarm_taper,
                alarmFolding AS alarm_folding,
                alarmDefect AS alarm_defect,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM CoilAlarmStatus
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn image_join_logs(&self, coil_id: i64) -> Result<Vec<ImageJoinLogRow>> {
        let rows = sqlx::query_as::<_, ImageJoinLogRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                imageCount AS image_count,
                rotate,
                flipH AS flip_h,
                flipV AS flip_v,
                clip1L AS clip1_l,
                clip1R AS clip1_r,
                clip2L AS clip2_l,
                clip2R AS clip2_r,
                clip3L AS clip3_l,
                clip3R AS clip3_r,
                data,
                DATE_FORMAT(createTime, '%Y-%m-%d %H:%i:%s') AS create_time
            FROM ImageJoinLog
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_image_join_logs(&self) -> Result<Vec<ImageJoinLogRow>> {
        let rows = sqlx::query_as::<_, ImageJoinLogRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                imageCount AS image_count,
                rotate,
                flipH AS flip_h,
                flipV AS flip_v,
                clip1L AS clip1_l,
                clip1R AS clip1_r,
                clip2L AS clip2_l,
                clip2R AS clip2_r,
                clip3L AS clip3_l,
                clip3R AS clip3_r,
                data,
                DATE_FORMAT(createTime, '%Y-%m-%d %H:%i:%s') AS create_time
            FROM ImageJoinLog
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn defect_statistics(&self, coil_id: i64) -> Result<Vec<DefectStatisticsRow>> {
        let result = sqlx::query_as::<_, DefectStatisticsRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface
            FROM DefectStatistics
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await;

        match result {
            Ok(rows) => Ok(rows),
            Err(sqlx::Error::Database(error))
                if matches!(error.code().as_deref(), Some("1146" | "42S02")) =>
            {
                Ok(Vec::new())
            }
            Err(error) => Err(error.into()),
        }
    }

    async fn backup_defect_statistics(&self) -> Result<Vec<DefectStatisticsRow>> {
        let result = sqlx::query_as::<_, DefectStatisticsRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface
            FROM DefectStatistics
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await;

        match result {
            Ok(rows) => Ok(rows),
            Err(sqlx::Error::Database(error))
                if matches!(error.code().as_deref(), Some("1146" | "42S02")) =>
            {
                Ok(Vec::new())
            }
            Err(error) => Err(error.into()),
        }
    }

    async fn alarm_flat_roll_data(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollDataRow>> {
        let rows = sqlx::query_as::<_, AlarmFlatRollDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmFlatRollData
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_alarm_flat_roll_data(&self) -> Result<Vec<AlarmFlatRollDataRow>> {
        let rows = sqlx::query_as::<_, AlarmFlatRollDataRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                surface,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmFlatRollData
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn cap_true_logs(&self, coil_id: i64) -> Result<Vec<CapTrueLogRow>> {
        let rows = sqlx::query_as::<_, CapTrueLogRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                cameraId AS camera_id,
                cameraName AS camera_name,
                DATE_FORMAT(capTrueStartTime, '%Y-%m-%d %H:%i:%s') AS cap_true_start_time,
                DATE_FORMAT(capTrueEndTime, '%Y-%m-%d %H:%i:%s') AS cap_true_end_time
            FROM CapTrueLog
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_cap_true_logs(&self) -> Result<Vec<CapTrueLogRow>> {
        let rows = sqlx::query_as::<_, CapTrueLogRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                cameraId AS camera_id,
                cameraName AS camera_name,
                DATE_FORMAT(capTrueStartTime, '%Y-%m-%d %H:%i:%s') AS cap_true_start_time,
                DATE_FORMAT(capTrueEndTime, '%Y-%m-%d %H:%i:%s') AS cap_true_end_time
            FROM CapTrueLog
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn cap_true_log_items(&self, coil_id: i64) -> Result<Vec<CapTrueLogItemRow>> {
        let rows = sqlx::query_as::<_, CapTrueLogItemRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                cameraId AS camera_id,
                cameraName AS camera_name,
                DATE_FORMAT(capTrueTime, '%Y-%m-%d %H:%i:%s') AS cap_true_time,
                imageIndex AS image_index
            FROM CapTrueLogItem
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_cap_true_log_items(&self) -> Result<Vec<CapTrueLogItemRow>> {
        let rows = sqlx::query_as::<_, CapTrueLogItemRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                cameraId AS camera_id,
                cameraName AS camera_name,
                DATE_FORMAT(capTrueTime, '%Y-%m-%d %H:%i:%s') AS cap_true_time,
                imageIndex AS image_index
            FROM CapTrueLogItem
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn sync_missing_summaries(&self, limit: u32) -> Result<usize> {
        let limit = limit.clamp(1, 1000);
        let coil_ids = sqlx::query_scalar::<_, i64>(
            r#"
            SELECT DISTINCT child_coil.SecondaryCoilId
            FROM Coil child_coil
            LEFT JOIN coil_summary summary ON summary.Id = child_coil.SecondaryCoilId
            WHERE child_coil.SecondaryCoilId IS NOT NULL
              AND summary.Id IS NULL
            ORDER BY child_coil.SecondaryCoilId DESC
            LIMIT ?
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;

        let defect_classes = self.defect_class_dict().await?;
        let mut inserted = 0;

        for coil_id in coil_ids {
            let Some(mut source) = self.missing_summary_source(coil_id).await? else {
                continue;
            };
            let defects = self.defects_for_summary(coil_id).await?;
            let values = summary_sync_values(coil_id, &defects, &defect_classes);
            let alarm_infos = self.alarm_infos_for_summary(coil_id).await?;
            let alarm_values = alarm_sync_values(
                coil_id,
                source.next_code.as_deref(),
                source.next_info.as_deref(),
                &alarm_infos,
            );
            apply_alarm_sync_values(&mut source, &alarm_values);
            if self.insert_summary(&source, &values).await? {
                inserted += 1;
            }
        }

        Ok(inserted)
    }

    async fn sync_existing_summaries(&self, coil_ids: &[i64]) -> Result<usize> {
        let defect_classes = self.defect_class_dict().await?;
        let mut updated = 0;

        for coil_id in coil_ids {
            let exists =
                sqlx::query_scalar::<_, i64>("SELECT Id FROM coil_summary WHERE Id = ? LIMIT 1")
                    .bind(coil_id)
                    .fetch_optional(&self.pool)
                    .await?
                    .is_some();
            if !exists {
                continue;
            }

            let defects = self.defects_for_summary(*coil_id).await?;
            let values = summary_sync_values(*coil_id, &defects, &defect_classes);
            let sql = format!("{COIL_SUMMARY_SELECT} WHERE Id = ? LIMIT 1");
            let mut summary_rows = self.query_coils(&sql, QueryBind::I64(*coil_id)).await?;
            let Some(mut summary_row) = summary_rows.pop() else {
                continue;
            };
            let alarm_infos = self.alarm_infos_for_summary(*coil_id).await?;
            let alarm_values = alarm_sync_values(
                *coil_id,
                summary_row.next_code.as_deref(),
                summary_row.next_info.as_deref(),
                &alarm_infos,
            );
            apply_alarm_sync_values(&mut summary_row, &alarm_values);
            sqlx::query(
                r#"
                UPDATE coil_summary
                SET
                    NextCode = ?,
                    NextInfo = ?,
                    S_DefectGrad = ?,
                    S_TaperShapeGrad = ?,
                    S_LooseCoilGrad = ?,
                    S_FlatRollGrad = ?,
                    S_Grad = ?,
                    S_HasAlarm = ?,
                    S_NextCode = ?,
                    S_NextName = ?,
                    L_DefectGrad = ?,
                    L_TaperShapeGrad = ?,
                    L_LooseCoilGrad = ?,
                    L_FlatRollGrad = ?,
                    L_Grad = ?,
                    L_HasAlarm = ?,
                    L_NextCode = ?,
                    L_NextName = ?,
                    DefectCountS = ?,
                    DefectCountL = ?,
                    MaxDefectName = ?,
                    MaxDefectLevel = ?,
                    MaxDefectSurface = ?,
                    MaxDefectIsShown = ?
                WHERE Id = ?
                "#,
            )
            .bind(summary_row.next_code.as_deref())
            .bind(summary_row.next_info.as_deref())
            .bind(summary_row.s_defect_grad)
            .bind(summary_row.s_taper_shape_grad)
            .bind(summary_row.s_loose_coil_grad)
            .bind(summary_row.s_flat_roll_grad)
            .bind(summary_row.s_grad)
            .bind(summary_row.s_has_alarm)
            .bind(summary_row.s_next_code.as_deref())
            .bind(summary_row.s_next_name.as_deref())
            .bind(summary_row.l_defect_grad)
            .bind(summary_row.l_taper_shape_grad)
            .bind(summary_row.l_loose_coil_grad)
            .bind(summary_row.l_flat_roll_grad)
            .bind(summary_row.l_grad)
            .bind(summary_row.l_has_alarm)
            .bind(summary_row.l_next_code.as_deref())
            .bind(summary_row.l_next_name.as_deref())
            .bind(values.defect_count_s)
            .bind(values.defect_count_l)
            .bind(values.max_defect_name)
            .bind(values.max_defect_level)
            .bind(values.max_defect_surface)
            .bind(values.max_defect_is_shown)
            .bind(coil_id)
            .execute(&self.pool)
            .await?;
            updated += 1;
        }

        Ok(updated)
    }

    async fn alarm_flat_rolls(&self, coil_id: i64) -> Result<Vec<AlarmFlatRollRow>> {
        let rows = sqlx::query_as::<_, AlarmFlatRollRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                out_circle_width,
                out_circle_height,
                out_circle_center_x,
                out_circle_center_y,
                out_circle_radius,
                inner_circle_width,
                inner_circle_height,
                inner_circle_center_x,
                inner_circle_center_y,
                inner_circle_radius,
                accuracy_x,
                accuracy_y,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmFlatRoll
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            LIMIT 2
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_alarm_flat_rolls(&self) -> Result<Vec<AlarmFlatRollRow>> {
        let rows = sqlx::query_as::<_, AlarmFlatRollRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                out_circle_width,
                out_circle_height,
                out_circle_center_x,
                out_circle_center_y,
                out_circle_radius,
                inner_circle_width,
                inner_circle_height,
                inner_circle_center_x,
                inner_circle_center_y,
                inner_circle_radius,
                accuracy_x,
                accuracy_y,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmFlatRoll
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn alarm_taper_shapes(&self, coil_id: i64) -> Result<Vec<AlarmTaperShapeRow>> {
        let rows = sqlx::query_as::<_, AlarmTaperShapeRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                out_taper_max_x,
                out_taper_max_y,
                out_taper_max_value,
                out_taper_min_x,
                out_taper_min_y,
                out_taper_min_value,
                in_taper_max_x,
                in_taper_max_y,
                in_taper_max_value,
                in_taper_min_x,
                in_taper_min_y,
                in_taper_min_value,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmTaperShape
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_alarm_taper_shapes(&self) -> Result<Vec<AlarmTaperShapeRow>> {
        let rows = sqlx::query_as::<_, AlarmTaperShapeRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                out_taper_max_x,
                out_taper_max_y,
                out_taper_max_value,
                out_taper_min_x,
                out_taper_min_y,
                out_taper_min_value,
                in_taper_max_x,
                in_taper_max_y,
                in_taper_max_value,
                in_taper_min_x,
                in_taper_min_y,
                in_taper_min_value,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmTaperShape
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn alarm_loose_coils(&self, coil_id: i64) -> Result<Vec<AlarmLooseCoilRow>> {
        let rows = sqlx::query_as::<_, AlarmLooseCoilRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                max_width,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmLooseCoil
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_alarm_loose_coils(&self) -> Result<Vec<AlarmLooseCoilRow>> {
        let rows = sqlx::query_as::<_, AlarmLooseCoilRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                max_width,
                rotation_angle,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM AlarmLooseCoil
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn taper_shape_points(&self, coil_id: i64) -> Result<Vec<TaperShapePointRow>> {
        let rows = sqlx::query_as::<_, TaperShapePointRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                x,
                y,
                value,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM TaperShapePoint
            WHERE secondaryCoilId = ?
            ORDER BY Id ASC
            "#,
        )
        .bind(coil_id)
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }

    async fn backup_taper_shape_points(&self) -> Result<Vec<TaperShapePointRow>> {
        let rows = sqlx::query_as::<_, TaperShapePointRow>(
            r#"
            SELECT
                Id AS id,
                secondaryCoilId AS secondary_coil_id,
                COALESCE(surface, '') AS surface,
                x,
                y,
                value,
                level,
                err_msg,
                DATE_FORMAT(crateTime, '%Y-%m-%d %H:%i:%s') AS crate_time,
                data
            FROM TaperShapePoint
            ORDER BY Id ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await?;
        Ok(rows)
    }
}
