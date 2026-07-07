use serde_json::{Value, json};

use chrono::{Datelike, NaiveDateTime, Timelike};

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CoilSummaryRow {
    pub id: i64,
    pub coil_no: String,
    pub create_time: Option<String>,
    pub coil_type: Option<String>,
    pub coil_inside: Option<f64>,
    pub coil_dia: Option<f64>,
    pub thickness: Option<f64>,
    pub width: Option<f64>,
    pub weight: Option<f64>,
    pub act_width: Option<f64>,
    pub next_code: Option<String>,
    pub next_info: Option<String>,
    pub s_defect_grad: i32,
    pub s_taper_shape_grad: i32,
    pub s_loose_coil_grad: i32,
    pub s_flat_roll_grad: i32,
    pub s_grad: i32,
    pub s_has_alarm: bool,
    pub s_next_code: Option<String>,
    pub s_next_name: Option<String>,
    pub l_defect_grad: i32,
    pub l_taper_shape_grad: i32,
    pub l_loose_coil_grad: i32,
    pub l_flat_roll_grad: i32,
    pub l_grad: i32,
    pub l_has_alarm: bool,
    pub l_next_code: Option<String>,
    pub l_next_name: Option<String>,
    pub defect_count_s: i32,
    pub defect_count_l: i32,
    pub detection_time: Option<String>,
    pub check_status: i32,
    pub status_l: i32,
    pub status_s: i32,
    pub grade: i32,
    pub max_defect_name: Option<String>,
    pub max_defect_level: i32,
    pub max_defect_surface: Option<String>,
    pub has_coil: bool,
    pub has_alarm_info: bool,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct SecondaryCoilRow {
    pub id: i64,
    pub coil_no: String,
    pub coil_type: Option<String>,
    pub coil_inside: Option<f64>,
    pub coil_dia: Option<f64>,
    pub thickness: Option<f64>,
    pub width: Option<f64>,
    pub weight: Option<f64>,
    pub act_width: Option<f64>,
    pub create_time: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct NextCodeDictRow {
    pub id: i64,
    pub code: Option<String>,
    pub info: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct AlarmInfoSummaryRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub next_code: Option<String>,
    pub next_name: Option<String>,
    pub taper_shape_msg: Option<String>,
    pub loose_coil_msg: Option<String>,
    pub flat_roll_msg: Option<String>,
    pub defect_msg: Option<String>,
    pub defect_grad: i32,
    pub taper_shape_grad: i32,
    pub loose_coil_grad: i32,
    pub flat_roll_grad: i32,
    pub grad: i32,
    pub create_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct LatestCoilRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub detection_time: Option<String>,
    pub defect_count_s: Option<i32>,
    pub defect_count_l: Option<i32>,
    pub check_status: Option<i32>,
    pub status_l: Option<i32>,
    pub status_s: Option<i32>,
    pub grade: Option<i32>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CoilRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub detection_time: Option<String>,
    pub defect_count_s: Option<i32>,
    pub defect_count_l: Option<i32>,
    pub check_status: Option<i32>,
    pub status_l: Option<i32>,
    pub status_s: Option<i32>,
    pub grade: Option<i32>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug)]
pub struct GraderRow {
    pub id: i64,
    pub coil_no: String,
    pub create_time: Option<String>,
    pub coil_type: Option<String>,
    pub coil_inside: Option<f64>,
    pub coil_dia: Option<f64>,
    pub thickness: Option<f64>,
    pub width: Option<f64>,
    pub weight: Option<f64>,
    pub act_width: Option<f64>,
    pub child_id: Option<i64>,
    pub child_secondary_coil_id: Option<i64>,
    pub detection_time: Option<String>,
    pub defect_count_s: Option<i32>,
    pub defect_count_l: Option<i32>,
    pub check_status: Option<i32>,
    pub status_l: Option<i32>,
    pub status_s: Option<i32>,
    pub grade: Option<i32>,
    pub msg: Option<String>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct GraderSqlRow {
    pub id: i64,
    pub coil_no: String,
    pub create_time: Option<String>,
    pub coil_type: Option<String>,
    pub coil_inside: Option<f64>,
    pub coil_dia: Option<f64>,
    pub thickness: Option<f64>,
    pub width: Option<f64>,
    pub weight: Option<f64>,
    pub act_width: Option<f64>,
    pub child_id: Option<i64>,
    pub child_secondary_coil_id: Option<i64>,
    pub detection_time: Option<String>,
    pub defect_count_s: Option<i32>,
    pub defect_count_l: Option<i32>,
    pub check_status: Option<i32>,
    pub status_l: Option<i32>,
    pub status_s: Option<i32>,
    pub grade: Option<i32>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug)]
pub struct CoilDefectRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub defect_class: i32,
    pub defect_name: String,
    pub defect_status: i32,
    pub defect_time: Option<String>,
    pub defect_x: i32,
    pub defect_y: i32,
    pub defect_w: i32,
    pub defect_h: i32,
    pub defect_source: f64,
    pub defect_data: Option<Value>,
}

#[derive(Clone, Debug)]
pub struct ManualDefectRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub defect_class: i32,
    pub defect_name: String,
    pub defect_status: i32,
    pub defect_time: Option<String>,
    pub defect_x: i32,
    pub defect_y: i32,
    pub defect_w: i32,
    pub defect_h: i32,
    pub defect_source: f64,
    pub defect_data: Option<Value>,
    pub remark: Option<String>,
    pub annotator: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DefectClassDictRow {
    pub id: i64,
    pub defect_class: i32,
    pub defect_name: String,
    pub defect_type: Option<String>,
    pub defect_color: Option<String>,
    pub defect_level: Option<i32>,
    pub visible: Option<i32>,
    pub defect_desc: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct AlarmFlatRollRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub out_circle_width: Option<f64>,
    pub out_circle_height: Option<f64>,
    pub out_circle_center_x: Option<f64>,
    pub out_circle_center_y: Option<f64>,
    pub out_circle_radius: Option<f64>,
    pub inner_circle_width: Option<f64>,
    pub inner_circle_height: Option<f64>,
    pub inner_circle_center_x: Option<f64>,
    pub inner_circle_center_y: Option<f64>,
    pub inner_circle_radius: Option<f64>,
    pub accuracy_x: Option<f64>,
    pub accuracy_y: Option<f64>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct AlarmTaperShapeRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub out_taper_max_x: Option<i32>,
    pub out_taper_max_y: Option<i32>,
    pub out_taper_max_value: Option<f64>,
    pub out_taper_min_x: Option<i32>,
    pub out_taper_min_y: Option<i32>,
    pub out_taper_min_value: Option<f64>,
    pub in_taper_max_x: Option<i32>,
    pub in_taper_max_y: Option<i32>,
    pub in_taper_max_value: Option<f64>,
    pub in_taper_min_x: Option<i32>,
    pub in_taper_min_y: Option<i32>,
    pub in_taper_min_value: Option<f64>,
    pub rotation_angle: Option<f64>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct AlarmLooseCoilRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub max_width: Option<f64>,
    pub rotation_angle: Option<f64>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct TaperShapePointRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub value: Option<f64>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct ServerDetectionErrorRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub error_type: Option<String>,
    pub time: Option<String>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DefectCheckRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub defect_id: Option<i64>,
    pub key: Option<String>,
    pub status: Option<i32>,
    pub old_defect_id: Option<i64>,
    pub old_defect_name: Option<String>,
    pub new_defect_id: Option<i64>,
    pub new_defect_name: Option<String>,
    pub add_time: Option<String>,
    pub msg: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DataEllipseRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub ellipse_type: Option<String>,
    pub center_x: Option<f64>,
    pub center_y: Option<f64>,
    pub width: Option<f64>,
    pub height: Option<f64>,
    pub rotation_angle: Option<f64>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DeepPointRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub x_mm: Option<f64>,
    pub y_mm: Option<f64>,
    pub value: Option<f64>,
    pub value_int: Option<i32>,
    pub by_user: Option<i32>,
    pub draw: Option<i32>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DetectionSpeedRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub start_time: Option<String>,
    pub end_time: Option<String>,
    pub all_time: Option<f64>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CoilAlarmStatusRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub level: Option<i32>,
    pub alarm_status: Option<i32>,
    pub alarm_flat_roll: Option<i32>,
    pub alarm_taper: Option<i32>,
    pub alarm_folding: Option<i32>,
    pub alarm_defect: Option<i32>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct ImageJoinLogRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub image_count: Option<i32>,
    pub rotate: Option<f64>,
    pub flip_h: Option<i32>,
    pub flip_v: Option<i32>,
    pub clip1_l: Option<i32>,
    pub clip1_r: Option<i32>,
    pub clip2_l: Option<i32>,
    pub clip2_r: Option<i32>,
    pub clip3_l: Option<i32>,
    pub clip3_r: Option<i32>,
    pub data: Option<String>,
    pub create_time: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct DefectStatisticsRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct AlarmFlatRollDataRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub level: Option<i32>,
    pub err_msg: Option<String>,
    pub crate_time: Option<String>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CapTrueLogRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub camera_id: Option<i32>,
    pub camera_name: Option<String>,
    pub cap_true_start_time: Option<String>,
    pub cap_true_end_time: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CapTrueLogItemRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub camera_id: Option<i32>,
    pub camera_name: Option<String>,
    pub cap_true_time: Option<String>,
    pub image_index: Option<i32>,
}

#[derive(Clone, Debug, Default)]
pub struct ManualDefectWrite {
    pub secondary_coil_id: Option<i64>,
    pub surface: Option<String>,
    pub defect_name: Option<String>,
    pub defect_status: Option<i32>,
    pub defect_x: Option<i32>,
    pub defect_y: Option<i32>,
    pub defect_w: Option<i32>,
    pub defect_h: Option<i32>,
    pub defect_data: Option<Value>,
    pub remark: Option<String>,
    pub annotator: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct CoilCheckRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub status: i32,
    pub msg: String,
}

#[derive(Clone, Debug)]
pub struct CoilStateRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub start_time: Option<String>,
    pub scan3d_coordinate_scale_x: Option<f64>,
    pub scan3d_coordinate_scale_y: Option<f64>,
    pub scan3d_coordinate_scale_z: Option<f64>,
    pub rotate: Option<i32>,
    pub x_rotate: Option<i32>,
    pub median_3d: Option<f64>,
    pub median_3d_mm: Option<f64>,
    pub color_from_value_mm: Option<f64>,
    pub color_to_value_mm: Option<f64>,
    pub start: Option<f64>,
    pub step: Option<f64>,
    pub upper_limit: Option<f64>,
    pub lower_limit: Option<f64>,
    pub lower_area: Option<i64>,
    pub upper_area: Option<i64>,
    pub lower_area_percent: Option<f64>,
    pub upper_area_percent: Option<f64>,
    pub mask_area: Option<i64>,
    pub width: Option<i32>,
    pub height: Option<i32>,
    pub json_data: Option<String>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct CoilStateSqlRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: Option<String>,
    pub start_time: Option<String>,
    pub scan3d_coordinate_scale_x: Option<f64>,
    pub scan3d_coordinate_scale_y: Option<f64>,
    pub scan3d_coordinate_scale_z: Option<f64>,
    pub rotate: Option<i32>,
    pub x_rotate: Option<i32>,
    pub median_3d: Option<f64>,
    pub median_3d_mm: Option<f64>,
    pub color_from_value_mm: Option<f64>,
    pub color_to_value_mm: Option<f64>,
    pub start: Option<f64>,
    pub step: Option<f64>,
    pub upper_limit: Option<f64>,
    pub lower_limit: Option<f64>,
    pub lower_area: Option<i64>,
    pub upper_area: Option<i64>,
    pub lower_area_percent: Option<f64>,
    pub upper_area_percent: Option<f64>,
    pub mask_area: Option<i64>,
    pub width: Option<i32>,
    pub height: Option<i32>,
    pub json_data: Option<String>,
}

#[derive(Clone, Debug)]
pub struct PlcDataRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub location_s: Option<f64>,
    pub location_l: Option<f64>,
    pub location_laser: Option<f64>,
    pub start_time: Option<String>,
    pub pcl_data: Option<String>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct PlcDataSqlRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub location_s: Option<f64>,
    pub location_l: Option<f64>,
    pub location_laser: Option<f64>,
    pub start_time: Option<String>,
    pub pcl_data: Option<String>,
}

#[derive(Clone, Debug)]
pub struct PlcCurveAllRow {
    pub coil_id: i64,
    pub time: Option<String>,
    pub location_s: Option<f64>,
    pub location_l: Option<f64>,
    pub location_laser: Option<f64>,
    pub median_3d_mm_s: Option<f64>,
    pub median_3d_mm_l: Option<f64>,
    pub median_3d_mm_avg: Option<f64>,
    pub width: Option<f64>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct PlcCurveAllSqlRow {
    pub coil_id: i64,
    pub time: Option<String>,
    pub location_s: Option<f64>,
    pub location_l: Option<f64>,
    pub location_laser: Option<f64>,
    pub median_3d_mm_s: Option<f64>,
    pub median_3d_mm_l: Option<f64>,
    pub median_3d_mm_avg: Option<f64>,
    pub width: Option<f64>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct PointDataRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub point_type: Option<String>,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub z: Option<f64>,
    pub z_mm: Option<f64>,
    pub data: Option<String>,
    pub crate_time: Option<String>,
}

#[derive(Clone, Debug, sqlx::FromRow)]
pub struct LineDataRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub line_type: Option<String>,
    pub center_x: Option<f64>,
    pub center_y: Option<f64>,
    pub width: Option<f64>,
    pub height: Option<f64>,
    pub rotation_angle: Option<f64>,
    pub x1: Option<f64>,
    pub y1: Option<f64>,
    pub x2: Option<f64>,
    pub y2: Option<f64>,
    pub data: Option<String>,
    pub inner_min_value: Option<f64>,
    pub inner_min_value_mm: Option<f64>,
    pub inner_max_value: Option<f64>,
    pub inner_max_value_mm: Option<f64>,
    pub outer_min_value: Option<f64>,
    pub outer_min_value_mm: Option<f64>,
    pub outer_max_value: Option<f64>,
    pub outer_max_value_mm: Option<f64>,
    pub crate_time: Option<String>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct CoilDefectSqlRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub defect_class: i32,
    pub defect_name: String,
    pub defect_status: i32,
    pub defect_time: Option<String>,
    pub defect_x: i32,
    pub defect_y: i32,
    pub defect_w: i32,
    pub defect_h: i32,
    pub defect_source: f64,
    pub defect_data: Option<String>,
}

#[derive(Debug, sqlx::FromRow)]
pub struct ManualDefectSqlRow {
    pub id: i64,
    pub secondary_coil_id: i64,
    pub surface: String,
    pub defect_class: i32,
    pub defect_name: String,
    pub defect_status: i32,
    pub defect_time: Option<String>,
    pub defect_x: i32,
    pub defect_y: i32,
    pub defect_w: i32,
    pub defect_h: i32,
    pub defect_source: f64,
    pub defect_data: Option<String>,
    pub remark: Option<String>,
    pub annotator: Option<String>,
}

impl From<CoilStateSqlRow> for CoilStateRow {
    fn from(row: CoilStateSqlRow) -> Self {
        Self {
            id: row.id,
            secondary_coil_id: row.secondary_coil_id,
            surface: row.surface.unwrap_or_default(),
            start_time: row.start_time,
            scan3d_coordinate_scale_x: row.scan3d_coordinate_scale_x,
            scan3d_coordinate_scale_y: row.scan3d_coordinate_scale_y,
            scan3d_coordinate_scale_z: row.scan3d_coordinate_scale_z,
            rotate: row.rotate,
            x_rotate: row.x_rotate,
            median_3d: row.median_3d,
            median_3d_mm: row.median_3d_mm,
            color_from_value_mm: row.color_from_value_mm,
            color_to_value_mm: row.color_to_value_mm,
            start: row.start,
            step: row.step,
            upper_limit: row.upper_limit,
            lower_limit: row.lower_limit,
            lower_area: row.lower_area,
            upper_area: row.upper_area,
            lower_area_percent: row.lower_area_percent,
            upper_area_percent: row.upper_area_percent,
            mask_area: row.mask_area,
            width: row.width,
            height: row.height,
            json_data: row.json_data,
        }
    }
}

impl From<GraderSqlRow> for GraderRow {
    fn from(row: GraderSqlRow) -> Self {
        Self {
            id: row.id,
            coil_no: row.coil_no,
            create_time: row.create_time,
            coil_type: row.coil_type,
            coil_inside: row.coil_inside,
            coil_dia: row.coil_dia,
            thickness: row.thickness,
            width: row.width,
            weight: row.weight,
            act_width: row.act_width,
            child_id: row.child_id,
            child_secondary_coil_id: row.child_secondary_coil_id,
            detection_time: row.detection_time,
            defect_count_s: row.defect_count_s,
            defect_count_l: row.defect_count_l,
            check_status: row.check_status,
            status_l: row.status_l,
            status_s: row.status_s,
            grade: row.grade,
            msg: row.msg,
        }
    }
}

impl From<PlcDataSqlRow> for PlcDataRow {
    fn from(row: PlcDataSqlRow) -> Self {
        Self {
            id: row.id,
            secondary_coil_id: row.secondary_coil_id,
            location_s: row.location_s,
            location_l: row.location_l,
            location_laser: row.location_laser,
            start_time: row.start_time,
            pcl_data: row.pcl_data,
        }
    }
}

impl From<PlcCurveAllSqlRow> for PlcCurveAllRow {
    fn from(row: PlcCurveAllSqlRow) -> Self {
        Self {
            coil_id: row.coil_id,
            time: row.time,
            location_s: row.location_s,
            location_l: row.location_l,
            location_laser: row.location_laser,
            median_3d_mm_s: row.median_3d_mm_s,
            median_3d_mm_l: row.median_3d_mm_l,
            median_3d_mm_avg: row.median_3d_mm_avg,
            width: row.width,
        }
    }
}

impl From<CoilSummaryRow> for GraderRow {
    fn from(row: CoilSummaryRow) -> Self {
        Self {
            id: row.id,
            coil_no: row.coil_no,
            create_time: row.create_time,
            coil_type: row.coil_type,
            coil_inside: row.coil_inside,
            coil_dia: row.coil_dia,
            thickness: row.thickness,
            width: row.width,
            weight: row.weight,
            act_width: row.act_width,
            child_id: None,
            child_secondary_coil_id: None,
            detection_time: None,
            defect_count_s: None,
            defect_count_l: None,
            check_status: None,
            status_l: None,
            status_s: None,
            grade: None,
            msg: None,
        }
    }
}

impl From<CoilDefectSqlRow> for CoilDefectRow {
    fn from(row: CoilDefectSqlRow) -> Self {
        Self {
            id: row.id,
            secondary_coil_id: row.secondary_coil_id,
            surface: row.surface,
            defect_class: row.defect_class,
            defect_name: row.defect_name,
            defect_status: row.defect_status,
            defect_time: row.defect_time,
            defect_x: row.defect_x,
            defect_y: row.defect_y,
            defect_w: row.defect_w,
            defect_h: row.defect_h,
            defect_source: row.defect_source,
            defect_data: parse_defect_data(row.defect_data),
        }
    }
}

impl From<ManualDefectSqlRow> for ManualDefectRow {
    fn from(row: ManualDefectSqlRow) -> Self {
        Self {
            id: row.id,
            secondary_coil_id: row.secondary_coil_id,
            surface: row.surface,
            defect_class: row.defect_class,
            defect_name: row.defect_name,
            defect_status: row.defect_status,
            defect_time: row.defect_time,
            defect_x: row.defect_x,
            defect_y: row.defect_y,
            defect_w: row.defect_w,
            defect_h: row.defect_h,
            defect_source: row.defect_source,
            defect_data: parse_defect_data(row.defect_data),
            remark: row.remark,
            annotator: row.annotator,
        }
    }
}

pub fn coil_summary_to_python_json(row: &CoilSummaryRow) -> Value {
    let children_coil_defect = row
        .max_defect_name
        .as_deref()
        .filter(|name| !name.trim().is_empty())
        .map(|name| {
            vec![json!({
                "Id": 0,
                "secondaryCoilId": row.id,
                "surface": row.max_defect_surface.as_deref().unwrap_or("S"),
                "defectName": name,
                "defectLevel": row.max_defect_level,
                "defectClass": 0,
                "defectStatus": 0,
                "defectX": 0,
                "defectY": 0,
                "defectW": 0,
                "defectH": 0,
                "defectSource": 0,
                "is_area": false,
            })]
        })
        .unwrap_or_default();
    let children_coil = if row.has_coil {
        vec![json!({
            "SecondaryCoilId": row.id,
            "DetectionTime": python_iso_datetime_json(row.detection_time.as_deref()),
            "DefectCountL": row.defect_count_l,
            "Status_L": row.status_l,
            "Grade": row.grade,
            "DefectCountS": row.defect_count_s,
            "Id": row.id,
            "CheckStatus": row.check_status,
            "Status_S": row.status_s,
            "Msg": "",
        })]
    } else {
        Vec::new()
    };

    json!({
        "Id": row.id,
        "CoilNo": row.coil_no,
        "CreateTime": row.create_time,
        "CoilType": row.coil_type,
        "CoilInside": python_display_float(row.coil_inside),
        "CoilDia": python_display_float(row.coil_dia),
        "Thickness": python_display_float(row.thickness),
        "Width": python_display_float(row.width),
        "Weight": python_display_float(row.weight),
        "ActWidth": python_display_float(row.act_width),
        "NextCode": row.next_code.as_deref().unwrap_or(""),
        "NextInfo": row.next_info.as_deref().unwrap_or(""),
        "hasCoil": row.has_coil,
        "hasAlarmInfo": row.has_alarm_info,
        "AlarmInfo": {
            "S": alarm_summary(row, "S"),
            "L": alarm_summary(row, "L"),
        },
        "DefectCountS": row.defect_count_s,
        "DefectCountL": row.defect_count_l,
        "DetectionTime": row.detection_time,
        "CheckStatus": row.check_status,
        "Status_L": row.status_l,
        "Status_S": row.status_s,
        "Grade": row.grade,
        "Msg": "",
        "childrenCoil": children_coil,
        "childrenAlarmInfo": [],
        "childrenCoilDefect": children_coil_defect,
        "maxDefectName": row.max_defect_name.as_deref().unwrap_or(""),
        "maxDefectLevel": row.max_defect_level,
        "maxDefectSurface": row.max_defect_surface.as_deref().unwrap_or(""),
        "childrenCoilCheck": [],
    })
}

pub fn coil_detail_to_python_json(row: &GraderRow) -> Value {
    let mut body = serde_json::Map::new();
    body.insert("hasCoil".to_string(), json!(row.child_id.is_some()));
    body.insert("hasAlarmInfo".to_string(), json!(false));
    body.insert("AlarmInfo".to_string(), json!({}));
    body.insert("Id".to_string(), json!(row.id));
    body.insert(
        "SecondaryCoilId".to_string(),
        json!(row.child_secondary_coil_id.unwrap_or(row.id)),
    );
    body.insert("CoilNo".to_string(), json!(row.coil_no));
    body.insert(
        "CreateTime".to_string(),
        python_datetime_json(row.create_time.as_deref()),
    );
    body.insert("CoilType".to_string(), json!(row.coil_type));
    body.insert(
        "CoilInside".to_string(),
        json!(python_display_float(row.coil_inside)),
    );
    body.insert(
        "CoilDia".to_string(),
        json!(python_display_float(row.coil_dia)),
    );
    body.insert(
        "Thickness".to_string(),
        json!(python_display_float(row.thickness)),
    );
    body.insert("Width".to_string(), json!(python_display_float(row.width)));
    body.insert(
        "Weight".to_string(),
        json!(python_display_float(row.weight)),
    );
    body.insert(
        "ActWidth".to_string(),
        json!(python_display_float(row.act_width)),
    );
    body.insert("childrenAlarmInfo".to_string(), json!([]));
    body.insert("maxDefectName".to_string(), json!(""));
    body.insert("maxDefectLevel".to_string(), json!(0));
    body.insert("maxDefectSurface".to_string(), json!(""));

    if let Some(child_id) = row.child_id {
        let child_secondary_coil_id = row.child_secondary_coil_id.unwrap_or(row.id);
        body.insert(
            "DetectionTime".to_string(),
            python_datetime_json(row.detection_time.as_deref()),
        );
        body.insert(
            "DefectCountS".to_string(),
            json!(row.defect_count_s.unwrap_or(0)),
        );
        body.insert(
            "DefectCountL".to_string(),
            json!(row.defect_count_l.unwrap_or(0)),
        );
        body.insert(
            "CheckStatus".to_string(),
            json!(row.check_status.unwrap_or(0)),
        );
        body.insert("Status_L".to_string(), json!(row.status_l.unwrap_or(0)));
        body.insert("Status_S".to_string(), json!(row.status_s.unwrap_or(0)));
        body.insert("Grade".to_string(), json!(row.grade.unwrap_or(0)));
        body.insert("Msg".to_string(), json!(row.msg.as_deref().unwrap_or("")));
        body.insert(
            "childrenCoil".to_string(),
            json!([{
                "SecondaryCoilId": child_secondary_coil_id,
                "DetectionTime": python_iso_datetime_json(row.detection_time.as_deref()),
                "DefectCountL": row.defect_count_l.unwrap_or(0),
                "Status_L": row.status_l.unwrap_or(0),
                "Grade": row.grade.unwrap_or(0),
                "DefectCountS": row.defect_count_s.unwrap_or(0),
                "Id": child_id,
                "CheckStatus": row.check_status.unwrap_or(0),
                "Status_S": row.status_s.unwrap_or(0),
                "Msg": row.msg.as_deref().unwrap_or(""),
            }]),
        );
    } else {
        body.insert("childrenCoil".to_string(), json!([]));
    }

    Value::Object(body)
}

pub fn latest_coil_to_python_json(row: &LatestCoilRow) -> Value {
    let mut body = serde_json::Map::new();
    body.insert("SecondaryCoilId".to_string(), json!(row.secondary_coil_id));
    body.insert(
        "DetectionTime".to_string(),
        python_datetime_json(row.detection_time.as_deref()),
    );
    body.insert("DefectCountL".to_string(), json!(row.defect_count_l));
    body.insert("Status_L".to_string(), json!(row.status_l));
    body.insert("Grade".to_string(), json!(row.grade));
    body.insert("DefectCountS".to_string(), json!(row.defect_count_s));
    body.insert("Id".to_string(), json!(row.id));
    body.insert("CheckStatus".to_string(), json!(row.check_status));
    body.insert("Status_S".to_string(), json!(row.status_s));
    body.insert("Msg".to_string(), json!(row.msg));
    Value::Object(body)
}

pub fn grader_to_python_json(row: &GraderRow, next: String) -> Value {
    let mut body = serde_json::Map::new();
    body.insert(
        "ActWidth".to_string(),
        json!(python_display_float(row.act_width)),
    );
    body.insert("CoilNo".to_string(), json!(row.coil_no));
    body.insert(
        "CreateTime".to_string(),
        python_datetime_json(row.create_time.as_deref()),
    );
    body.insert("CoilType".to_string(), json!(row.coil_type));
    body.insert(
        "CoilInside".to_string(),
        json!(python_display_float(row.coil_inside)),
    );
    body.insert("Id".to_string(), json!(row.id));
    body.insert(
        "CoilDia".to_string(),
        json!(python_display_float(row.coil_dia)),
    );
    body.insert(
        "Thickness".to_string(),
        json!(python_display_float(row.thickness)),
    );
    body.insert("Width".to_string(), json!(python_display_float(row.width)));
    body.insert(
        "Weight".to_string(),
        json!(python_display_float(row.weight)),
    );

    if let Some(child_id) = row.child_id {
        body.insert("Id".to_string(), json!(child_id));
        body.insert(
            "SecondaryCoilId".to_string(),
            json!(row.child_secondary_coil_id.unwrap_or(row.id)),
        );
        body.insert(
            "DetectionTime".to_string(),
            python_datetime_json(row.detection_time.as_deref()),
        );
        body.insert("DefectCountS".to_string(), json!(row.defect_count_s));
        body.insert("DefectCountL".to_string(), json!(row.defect_count_l));
        body.insert("CheckStatus".to_string(), json!(row.check_status));
        body.insert("Status_L".to_string(), json!(row.status_l));
        body.insert("Status_S".to_string(), json!(row.status_s));
        body.insert("Grade".to_string(), json!(row.grade));
        body.insert("Msg".to_string(), json!(row.msg.as_deref().unwrap_or("")));
    } else {
        body.insert("childrenCoil".to_string(), json!([]));
    }

    body.insert("Next".to_string(), Value::String(next));
    Value::Object(body)
}

fn python_display_float(value: Option<f64>) -> Option<f64> {
    value.map(|number| {
        if !number.is_finite() {
            number
        } else {
            (number * 1_000_000.0).round() / 1_000_000.0
        }
    })
}

pub fn defect_to_python_json(row: &CoilDefectRow) -> Value {
    json!({
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "surface": row.surface,
        "defectClass": row.defect_class,
        "defectName": row.defect_name,
        "defectStatus": row.defect_status,
        "defectTime": python_iso_datetime_json(row.defect_time.as_deref()),
        "defectX": row.defect_x,
        "defectY": row.defect_y,
        "defectW": row.defect_w,
        "defectH": row.defect_h,
        "defectSource": round_mysql_float_for_python_json(row.defect_source),
        "defectData": detail_defect_data_json(row.defect_data.as_ref()),
    })
}

pub fn detail_defect_to_python_json(row: &CoilDefectRow) -> Value {
    json!({
        "surface": row.surface,
        "secondaryCoilId": row.secondary_coil_id,
        "Id": row.id,
        "defectClass": row.defect_class,
        "defectStatus": row.defect_status,
        "defectX": row.defect_x,
        "defectW": row.defect_w,
        "defectSource": round_mysql_float_for_python_json(row.defect_source),
        "defectName": row.defect_name,
        "defectTime": python_iso_datetime_json(row.defect_time.as_deref()),
        "defectY": row.defect_y,
        "defectH": row.defect_h,
        "defectData": detail_defect_data_json(row.defect_data.as_ref()),
    })
}

pub fn detail_defect_alias_to_python_json(row: &CoilDefectRow) -> Value {
    json!({
        "surface": row.surface,
        "secondaryCoilId": row.secondary_coil_id,
        "Id": row.id,
        "defectClass": row.defect_class,
        "defectStatus": row.defect_status,
        "defectX": row.defect_x,
        "defectW": row.defect_w,
        "defectSource": round_mysql_float_for_python_json(row.defect_source),
        "defectName": row.defect_name,
        "defectTime": python_datetime_json(row.defect_time.as_deref()),
        "defectY": row.defect_y,
        "defectH": row.defect_h,
        "defectData": detail_defect_data_json(row.defect_data.as_ref()),
    })
}

fn detail_defect_data_json(value: Option<&Value>) -> Value {
    match value {
        None | Some(Value::Null) => Value::String(String::new()),
        Some(value) => value.clone(),
    }
}

pub fn auto_defect_to_python_json(row: &CoilDefectRow) -> Value {
    let mut value = defect_to_python_json(row);
    if let Value::Object(body) = &mut value {
        body.insert("type".to_string(), json!("auto"));
    }
    value
}

pub fn manual_defect_to_python_json(row: &ManualDefectRow) -> Value {
    json!({
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "surface": row.surface,
        "defectClass": row.defect_class,
        "defectName": row.defect_name,
        "defectStatus": row.defect_status,
        "defectTime": python_iso_datetime_json(row.defect_time.as_deref()),
        "defectX": row.defect_x,
        "defectY": row.defect_y,
        "defectW": row.defect_w,
        "defectH": row.defect_h,
        "defectSource": row.defect_source,
        "defectData": row.defect_data,
        "remark": row.remark,
        "annotator": row.annotator,
        "type": "manual",
    })
}

pub fn defect_class_dict_to_python_json(row: &DefectClassDictRow) -> Value {
    json!({
        "Id": row.id,
        "defectClass": row.defect_class,
        "defectName": row.defect_name,
        "defectType": row.defect_type,
        "defectColor": row.defect_color,
        "defectLevel": row.defect_level,
        "visible": row.visible,
        "defectDesc": row.defect_desc,
    })
}

pub fn alarm_flat_roll_to_python_json(row: &AlarmFlatRollRow) -> Value {
    json!({
        "secondaryCoilId": row.secondary_coil_id,
        "out_circle_height": mysql_float_json(row.out_circle_height),
        "inner_circle_center_x": mysql_float_json(row.inner_circle_center_x),
        "data": row.data,
        "surface": row.surface,
        "inner_circle_center_y": mysql_float_json(row.inner_circle_center_y),
        "out_circle_center_x": mysql_float_json(row.out_circle_center_x),
        "inner_circle_radius": mysql_float_json(row.inner_circle_radius),
        "accuracy_x": mysql_float_json(row.accuracy_x),
        "out_circle_center_y": mysql_float_json(row.out_circle_center_y),
        "accuracy_y": mysql_float_json(row.accuracy_y),
        "out_circle_radius": mysql_float_json(row.out_circle_radius),
        "level": row.level,
        "Id": row.id,
        "inner_circle_width": mysql_float_json(row.inner_circle_width),
        "err_msg": row.err_msg,
        "out_circle_width": mysql_float_json(row.out_circle_width),
        "inner_circle_height": mysql_float_json(row.inner_circle_height),
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
    })
}

pub fn detail_alarm_flat_roll_to_python_json(row: &AlarmFlatRollRow) -> Value {
    let mut value = alarm_flat_roll_to_python_json(row);
    set_iso_crate_time(&mut value, row.crate_time.as_deref());
    value
}

pub fn alarm_taper_shape_to_python_json(row: &AlarmTaperShapeRow) -> Value {
    json!({
        "in_taper_max_x": row.in_taper_max_x,
        "err_msg": row.err_msg,
        "surface": row.surface,
        "in_taper_max_y": row.in_taper_max_y,
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
        "out_taper_max_x": row.out_taper_max_x,
        "in_taper_max_value": mysql_float_json(row.in_taper_max_value),
        "data": row.data,
        "out_taper_max_y": row.out_taper_max_y,
        "in_taper_min_x": row.in_taper_min_x,
        "Id": row.id,
        "out_taper_max_value": mysql_float_json(row.out_taper_max_value),
        "in_taper_min_y": row.in_taper_min_y,
        "out_taper_min_x": row.out_taper_min_x,
        "in_taper_min_value": mysql_float_json(row.in_taper_min_value),
        "out_taper_min_y": row.out_taper_min_y,
        "rotation_angle": mysql_float_json(row.rotation_angle),
        "secondaryCoilId": row.secondary_coil_id,
        "out_taper_min_value": mysql_float_json(row.out_taper_min_value),
        "level": row.level,
    })
}

pub fn detail_alarm_taper_shape_to_python_json(row: &AlarmTaperShapeRow) -> Value {
    let mut value = alarm_taper_shape_to_python_json(row);
    set_iso_crate_time(&mut value, row.crate_time.as_deref());
    value
}

pub fn alarm_loose_coil_to_python_json(row: &AlarmLooseCoilRow) -> Value {
    json!({
        "surface": row.surface,
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "rotation_angle": mysql_float_json(row.rotation_angle),
        "err_msg": row.err_msg,
        "data": row.data,
        "max_width": mysql_float_json(row.max_width),
        "level": row.level,
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
    })
}

pub fn detail_alarm_loose_coil_to_python_json(row: &AlarmLooseCoilRow) -> Value {
    let mut value = alarm_loose_coil_to_python_json(row);
    set_iso_crate_time(&mut value, row.crate_time.as_deref());
    value
}

pub fn taper_shape_point_to_python_json(row: &TaperShapePointRow) -> Value {
    json!({
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "surface": row.surface,
        "x": row.x,
        "y": row.y,
        "value": mysql_float_json(row.value),
        "level": row.level,
        "err_msg": row.err_msg,
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
        "data": row.data,
    })
}

fn mysql_float_json(value: Option<f64>) -> Option<f64> {
    value.map(round_mysql_float_for_python_json)
}

pub(crate) fn round_mysql_float_for_python_json(value: f64) -> f64 {
    if !value.is_finite() || value == 0.0 {
        return value;
    }

    let decimal_places = 5 - value.abs().log10().floor() as i32;
    if decimal_places >= 0 {
        let factor = 10_f64.powi(decimal_places);
        (value * factor).round() / factor
    } else {
        let factor = 10_f64.powi(-decimal_places);
        (value / factor).round() * factor
    }
}

pub fn coil_check_to_python_json(row: &CoilCheckRow) -> Value {
    json!({
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "status": row.status,
        "msg": row.msg,
    })
}

pub fn alarm_info_to_python_json(row: &AlarmInfoSummaryRow) -> Value {
    json!({
        "secondaryCoilId": row.secondary_coil_id,
        "surface": row.surface,
        "nextName": row.next_name,
        "taperShapeMsg": row.taper_shape_msg,
        "looseCoilMsg": row.loose_coil_msg,
        "flatRollMsg": row.flat_roll_msg,
        "defectMsg": row.defect_msg,
        "crateTime": python_datetime_json(row.create_time.as_deref()),
        "data": row.data,
        "Id": row.id,
        "nextCode": row.next_code,
        "taperShapeGrad": row.taper_shape_grad,
        "looseCoilGrad": row.loose_coil_grad,
        "flatRollGrad": row.flat_roll_grad,
        "defectGrad": row.defect_grad,
        "grad": row.grad,
    })
}

pub fn detail_alarm_info_to_python_json(row: &AlarmInfoSummaryRow) -> Value {
    let mut value = alarm_info_to_python_json(row);
    set_iso_crate_time(&mut value, row.create_time.as_deref());
    value
}

fn set_iso_crate_time(value: &mut Value, datetime: Option<&str>) {
    if let Value::Object(body) = value {
        body.insert("crateTime".to_string(), python_iso_datetime_json(datetime));
    }
}

pub fn coil_state_to_python_json(row: &CoilStateRow) -> Value {
    json!({
        "Id": row.id,
        "scan3dCoordinateScaleY": mysql_float_json(row.scan3d_coordinate_scale_y),
        "start": mysql_float_json(row.start),
        "mask_area": row.mask_area,
        "surface": row.surface,
        "scan3dCoordinateScaleZ": mysql_float_json(row.scan3d_coordinate_scale_z),
        "step": mysql_float_json(row.step),
        "width": row.width,
        "secondaryCoilId": row.secondary_coil_id,
        "rotate": row.rotate,
        "upperLimit": mysql_float_json(row.upper_limit),
        "height": row.height,
        "x_rotate": row.x_rotate,
        "lowerLimit": mysql_float_json(row.lower_limit),
        "jsonData": row.json_data.as_deref().unwrap_or(""),
        "median_3d": mysql_float_json(row.median_3d),
        "lowerArea": row.lower_area,
        "median_3d_mm": mysql_float_json(row.median_3d_mm),
        "upperArea": row.upper_area,
        "startTime": python_datetime_json(row.start_time.as_deref()),
        "colorFromValue_mm": mysql_float_json(row.color_from_value_mm),
        "lowerArea_percent": mysql_float_json(row.lower_area_percent),
        "scan3dCoordinateScaleX": mysql_float_json(row.scan3d_coordinate_scale_x),
        "colorToValue_mm": mysql_float_json(row.color_to_value_mm),
        "upperArea_percent": mysql_float_json(row.upper_area_percent),
    })
}

pub fn plc_data_to_python_json(row: &PlcDataRow) -> Value {
    json!({
        "Id": row.id,
        "secondaryCoilId": row.secondary_coil_id,
        "location_S": mysql_float_json(row.location_s),
        "location_L": mysql_float_json(row.location_l),
        "location_laser": mysql_float_json(row.location_laser),
        "startTime": python_datetime_json(row.start_time.as_deref()),
        "pclData": row.pcl_data.as_deref().unwrap_or(""),
    })
}

pub fn plc_curve_item_to_python_json(row: &PlcDataRow, field: &str) -> Value {
    let value = match field {
        "location_S" => row.location_s,
        "location_L" => row.location_l,
        "location_laser" => row.location_laser,
        _ => None,
    };
    json!({
        "coil_id": row.secondary_coil_id,
        "time": python_iso_datetime(row.start_time.as_deref()),
        "value": mysql_float_json(value),
    })
}

pub fn plc_curve_all_item_to_python_json(row: &PlcCurveAllRow) -> Value {
    json!({
        "coil_id": row.coil_id,
        "time": python_iso_datetime(row.time.as_deref()),
        "location_S": mysql_float_json(row.location_s),
        "location_L": mysql_float_json(row.location_l),
        "location_laser": mysql_float_json(row.location_laser),
        "median_3d_mm_S": mysql_float_json(row.median_3d_mm_s),
        "median_3d_mm_L": mysql_float_json(row.median_3d_mm_l),
        "median_3d_mm_avg": mysql_float_json(row.median_3d_mm_avg),
        "width_": mysql_float_json(row.width),
    })
}

pub fn point_data_to_python_json(row: &PointDataRow) -> Value {
    json!({
        "secondaryCoilId": row.secondary_coil_id,
        "surface": row.surface,
        "x": mysql_float_json(row.x),
        "z": mysql_float_json(row.z),
        "data": row.data,
        "type": row.point_type,
        "Id": row.id,
        "y": mysql_float_json(row.y),
        "z_mm": mysql_float_json(row.z_mm),
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
    })
}

pub fn line_data_to_python_json(row: &LineDataRow) -> Value {
    json!({
        "width": mysql_float_json(row.width),
        "inner_min_value": mysql_float_json(row.inner_min_value),
        "outer_max_value_mm": mysql_float_json(row.outer_max_value_mm),
        "height": mysql_float_json(row.height),
        "inner_min_value_mm": mysql_float_json(row.inner_min_value_mm),
        "crateTime": python_datetime_json(row.crate_time.as_deref()),
        "secondaryCoilId": row.secondary_coil_id,
        "rotation_angle": mysql_float_json(row.rotation_angle),
        "inner_max_value": mysql_float_json(row.inner_max_value),
        "surface": row.surface,
        "x1": mysql_float_json(row.x1),
        "inner_max_value_mm": mysql_float_json(row.inner_max_value_mm),
        "Id": row.id,
        "y1": mysql_float_json(row.y1),
        "outer_min_value": mysql_float_json(row.outer_min_value),
        "type": row.line_type,
        "x2": mysql_float_json(row.x2),
        "outer_min_value_mm": mysql_float_json(row.outer_min_value_mm),
        "center_x": mysql_float_json(row.center_x),
        "y2": mysql_float_json(row.y2),
        "outer_max_value": mysql_float_json(row.outer_max_value),
        "center_y": mysql_float_json(row.center_y),
        "data": row.data,
    })
}

pub fn default_coil_check_json(coil_id: i64) -> Value {
    json!({
        "status": 0,
        "msg": "",
        "secondaryCoilId": coil_id,
        "Id": -1,
    })
}

fn python_datetime_json(value: Option<&str>) -> Value {
    let Some(value) = value else {
        return Value::Null;
    };
    let Ok(datetime) = NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S") else {
        return Value::String(value.to_string());
    };
    json!({
        "year": datetime.year(),
        "month": datetime.month(),
        "weekday": datetime.weekday().num_days_from_monday(),
        "day": datetime.day(),
        "hour": datetime.hour(),
        "minute": datetime.minute(),
        "second": datetime.second(),
    })
}

fn python_iso_datetime(value: Option<&str>) -> String {
    let Some(value) = value else {
        return String::new();
    };
    if value.trim().is_empty() {
        return String::new();
    }
    NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S").map_or_else(
        |_| value.to_string(),
        |datetime| datetime.format("%Y-%m-%dT%H:%M:%S").to_string(),
    )
}

fn python_iso_datetime_json(value: Option<&str>) -> Value {
    let Some(value) = value else {
        return Value::Null;
    };
    if value.trim().is_empty() {
        return Value::Null;
    }
    Value::String(
        NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S").map_or_else(
            |_| value.to_string(),
            |datetime| datetime.format("%Y-%m-%dT%H:%M:%S").to_string(),
        ),
    )
}

fn alarm_summary(row: &CoilSummaryRow, surface: &str) -> Value {
    let (
        defect_grad,
        taper_shape_grad,
        loose_coil_grad,
        flat_roll_grad,
        grad,
        next_code,
        next_name,
    ) = if surface.eq_ignore_ascii_case("S") {
        (
            row.s_defect_grad,
            row.s_taper_shape_grad,
            row.s_loose_coil_grad,
            row.s_flat_roll_grad,
            row.s_grad,
            row.s_next_code.as_deref().unwrap_or(""),
            row.s_next_name.as_deref().unwrap_or(""),
        )
    } else {
        (
            row.l_defect_grad,
            row.l_taper_shape_grad,
            row.l_loose_coil_grad,
            row.l_flat_roll_grad,
            row.l_grad,
            row.l_next_code.as_deref().unwrap_or(""),
            row.l_next_name.as_deref().unwrap_or(""),
        )
    };

    json!({
        "secondaryCoilId": row.id,
        "surface": surface,
        "defectGrad": defect_grad,
        "taperShapeGrad": taper_shape_grad,
        "looseCoilGrad": loose_coil_grad,
        "flatRollGrad": flat_roll_grad,
        "grad": grad,
        "nextCode": next_code,
        "nextName": next_name,
        "createTime": row.detection_time.as_deref().or(row.create_time.as_deref()),
        "taperShapeMsg": "",
        "looseCoilMsg": "",
        "flatRollMsg": "",
        "defectMsg": "",
    })
}

fn parse_defect_data(value: Option<String>) -> Option<Value> {
    let value = value?;
    if value.trim().is_empty() {
        return None;
    }
    serde_json::from_str(&value)
        .ok()
        .or(Some(Value::String(value)))
}
