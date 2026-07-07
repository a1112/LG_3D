#![recursion_limit = "512"]

mod config;
mod data_config;
mod depth_data;
mod models;
mod repository;
mod routes;

pub use config::{DATABASE_URL_ENV, database_url_from_env, normalize_database_url};
pub use data_config::DataRuntimeConfig;
pub use models::{
    AlarmFlatRollDataRow, AlarmFlatRollRow, AlarmInfoSummaryRow, AlarmLooseCoilRow,
    AlarmTaperShapeRow, CapTrueLogItemRow, CapTrueLogRow, CoilAlarmStatusRow, CoilCheckRow,
    CoilDefectRow, CoilRow, CoilStateRow, CoilSummaryRow, DataEllipseRow, DeepPointRow,
    DefectCheckRow, DefectClassDictRow, DefectStatisticsRow, DetectionSpeedRow, ImageJoinLogRow,
    LatestCoilRow, LineDataRow, ManualDefectRow, ManualDefectWrite, NextCodeDictRow, PlcDataRow,
    PointDataRow, SecondaryCoilRow, ServerDetectionErrorRow, TaperShapePointRow,
};
pub use repository::{CoilRepository, InMemoryCoilRepository, MySqlCoilRepository};
pub use routes::{ApiState, TestModeConfig, build_app};
