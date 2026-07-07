use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use anyhow::{Context, Result};
use serde::Deserialize;
use serde_json::{Value, json};

use crate::depth_data::{DepthMap, load_depth_map_from_dir};

#[derive(Clone, Debug)]
pub struct DataRuntimeConfig {
    surfaces: Vec<SurfaceDataConfig>,
    info: Value,
    dump_tools: DumpToolConfig,
}

#[derive(Clone, Debug)]
struct SurfaceDataConfig {
    key: String,
    save_folder: PathBuf,
    capture_sources: Vec<PathBuf>,
}

#[derive(Clone, Debug, Default)]
struct DumpToolConfig {
    mysqldump_exe: Option<String>,
    pg_dump_exe: Option<String>,
}

#[derive(Deserialize)]
struct RawConfig {
    surface: Vec<RawSurfaceConfig>,
}

#[derive(Deserialize)]
struct RawSurfaceConfig {
    key: String,
    #[serde(rename = "saveFolder")]
    save_folder: String,
    #[serde(rename = "folderList", default)]
    folder_list: Vec<RawCaptureFolderConfig>,
}

#[derive(Deserialize)]
struct RawCaptureFolderConfig {
    source: String,
}

impl DataRuntimeConfig {
    pub fn load(path: &Path) -> Result<Self> {
        let content =
            fs::read_to_string(path).with_context(|| format!("read config file {:?}", path))?;
        let raw: RawConfig =
            serde_json::from_str(&content).with_context(|| format!("parse config {:?}", path))?;
        let raw_value: Value = serde_json::from_str(&content)
            .with_context(|| format!("parse config JSON {:?}", path))?;
        Ok(Self {
            surfaces: raw
                .surface
                .into_iter()
                .map(|surface| SurfaceDataConfig {
                    key: surface.key,
                    save_folder: PathBuf::from(surface.save_folder),
                    capture_sources: surface
                        .folder_list
                        .into_iter()
                        .filter_map(|folder| {
                            let source = folder.source.trim();
                            (!source.is_empty()).then(|| PathBuf::from(source))
                        })
                        .collect(),
                })
                .collect(),
            dump_tools: DumpToolConfig {
                mysqldump_exe: raw_value
                    .get("mysqldump")
                    .and_then(Value::as_str)
                    .map(str::to_string),
                pg_dump_exe: raw_value
                    .get("pg_dump")
                    .and_then(Value::as_str)
                    .map(str::to_string),
            },
            info: api_info_from_config(raw_value),
        })
    }

    pub fn load_default() -> Option<Self> {
        Self::load(&default_server_config_path()).ok()
    }

    pub fn data_has(&self, coil_id: i64) -> Value {
        let mut result = serde_json::Map::new();
        for surface in &self.surfaces {
            let coil_dir = surface.save_folder.join(coil_id.to_string());
            result.insert(
                surface.key.clone(),
                json!({
                    "3D": has_any_file(&coil_dir, &["3D.npz", "3D.npy"]),
                    "MESH": has_python_default_mesh(&coil_dir),
                    "JPG": has_named_image(&coil_dir, "GRAY"),
                    "2D": has_named_image(&coil_dir, "AREA"),
                }),
            );
        }
        Value::Object(result)
    }

    pub fn surface_asset_dir(&self, coil_id: i64, surface: &str) -> Option<PathBuf> {
        let surface = self.surface_config(surface)?;
        let coil_dir = surface.save_folder.join(coil_id.to_string());
        coil_dir.exists().then_some(coil_dir)
    }

    pub fn depth_map(&self, coil_id: i64, surface: &str) -> Option<Arc<DepthMap>> {
        let coil_dir = self.surface_asset_dir(coil_id, surface)?;
        load_depth_map_from_dir(&coil_dir)
    }

    pub fn api_info(&self) -> Value {
        self.info.clone()
    }

    pub fn backup_image_sources(&self) -> Vec<PathBuf> {
        self.surfaces
            .iter()
            .flat_map(|surface| surface.capture_sources.iter().cloned())
            .collect()
    }

    pub fn surface_save_folders(&self) -> Vec<PathBuf> {
        self.surfaces
            .iter()
            .map(|surface| surface.save_folder.clone())
            .collect()
    }

    pub fn mysqldump_exe(&self) -> Option<&str> {
        self.dump_tools.mysqldump_exe.as_deref()
    }

    pub fn pg_dump_exe(&self) -> Option<&str> {
        self.dump_tools.pg_dump_exe.as_deref()
    }

    fn surface_config(&self, surface: &str) -> Option<&SurfaceDataConfig> {
        self.surfaces
            .iter()
            .find(|config| config.key.eq_ignore_ascii_case(surface))
    }
}

pub fn default_server_config_path() -> PathBuf {
    if let Ok(path) = std::env::var("API_SERVER_CONFIG") {
        return PathBuf::from(path);
    }

    let config_dir = default_config_3d_dir();
    let configs_dir = config_dir.join("configs");
    let preferred_name = if developer_mode_enabled(&config_dir) {
        "Server3DLoc2.json"
    } else {
        "Server3D.json"
    };
    let preferred_path = configs_dir.join(preferred_name);
    if preferred_path.exists() {
        return preferred_path;
    }
    let standard_path = configs_dir.join("Server3D.json");
    if standard_path.exists() {
        return standard_path;
    }
    preferred_path
}

fn default_config_3d_dir() -> PathBuf {
    if let Ok(path) = std::env::var("CONFIG_3D_DIR") {
        return PathBuf::from(path);
    }

    let production_path = PathBuf::from(r"D:\CONFIG_3D");
    if production_path.exists() {
        return production_path;
    }

    default_project_root().join("CONFIG_3D")
}

fn developer_mode_enabled(config_dir: &Path) -> bool {
    env_flag("API_DEVELOPER_MODE") || config_dir.join("developer_mode=true").exists()
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

fn default_project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")))
        .to_path_buf()
}

pub fn default_api_info() -> Value {
    api_info_from_config(json!({
        "surface": [
            {
                "key": "S",
                "saveFolder": "D:\\Save_S",
                "rotate": 90,
                "x_rotate": 17,
                "direction": "L",
                "save3D_data": false,
                "folderList": []
            },
            {
                "key": "L",
                "saveFolder": "E:\\Save_L",
                "rotate": -90,
                "x_rotate": 10,
                "direction": "R",
                "save3D_data": false,
                "folderList": []
            }
        ]
    }))
}

fn api_info_from_config(config: Value) -> Value {
    let mut info = serde_json::Map::new();
    info.insert(
        "ErrorMap".to_string(),
        json!({
            "DataFolderError": -3,
            "ImageError": -2,
        }),
    );
    info.insert(
        "RendererList".to_string(),
        config
            .get("RendererList")
            .cloned()
            .unwrap_or_else(|| json!(["JET"])),
    );
    info.insert(
        "ColorMaps".to_string(),
        json!({
            "AUTUMN": 0,
            "BONE": 1,
            "JET": 2,
            "WINTER": 3,
            "RAINBOW": 4,
            "OCEAN": 5,
            "SUMMER": 6,
            "SPRING": 7,
            "COOL": 8,
            "HSV": 9,
            "PINK": 10,
            "HOT": 11,
            "PARULA": 12,
            "MAGMA": 13,
            "INFERNO": 14,
            "PLASMA": 15,
            "VIRIDIS": 16,
            "CIVIDIS": 17,
            "TWILIGHT": 18,
            "TWILIGHT_SHIFTED": 19,
            "TURBO": 20,
            "DEEPGREEN": 21,
        }),
    );
    info.insert(
        "SaveImageType".to_string(),
        config
            .get("SaveImageType")
            .cloned()
            .unwrap_or_else(|| json!(".png")),
    );
    info.insert("PreviewSize".to_string(), json!([512, 512]));

    if let Some(surfaces) = config.get("surface").and_then(Value::as_array) {
        for surface in surfaces {
            let key = surface
                .get("key")
                .and_then(Value::as_str)
                .unwrap_or_default();
            if !key.is_empty() {
                info.insert(format!("surface{key}"), surface.clone());
            }
        }
    }

    Value::Object(info)
}

fn has_any_file(dir: &Path, names: &[&str]) -> bool {
    names.iter().any(|name| dir.join(name).exists())
}

fn has_named_image(coil_dir: &Path, name: &str) -> bool {
    ["jpg", "png"].iter().any(|folder| {
        [".jpg", ".jpeg", ".png"].iter().any(|extension| {
            coil_dir
                .join(folder)
                .join(format!("{name}{extension}"))
                .exists()
        })
    })
}

fn has_python_default_mesh(coil_dir: &Path) -> bool {
    coil_dir
        .join("meshes")
        .join("defaultobject_mesh.mesh")
        .exists()
}
