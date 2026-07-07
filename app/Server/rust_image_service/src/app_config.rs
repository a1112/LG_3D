use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, Clone)]
pub struct RuntimeConfig {
    pub surfaces: Vec<SurfaceConfig>,
    pub test_data: Option<TestDataConfig>,
}

#[derive(Debug, Clone)]
pub struct SurfaceConfig {
    pub key: String,
    pub save_folder: PathBuf,
}

#[derive(Debug, Clone)]
pub struct TestDataConfig {
    pub enabled: bool,
    #[allow(dead_code)]
    pub coil_id: i64,
    pub data_dir: PathBuf,
}

#[derive(Debug, Deserialize)]
struct RawConfig {
    surface: Vec<RawSurfaceConfig>,
    #[serde(default, rename = "testMode", alias = "test_mode")]
    test_mode: Option<bool>,
    #[serde(default, rename = "testDataDir", alias = "test_data_dir")]
    test_data_dir: Option<String>,
    #[serde(default, rename = "testDataCoilId", alias = "test_data_coil_id")]
    test_data_coil_id: Option<i64>,
}

#[derive(Debug, Deserialize)]
struct RawSurfaceConfig {
    key: String,
    #[serde(rename = "saveFolder")]
    save_folder: String,
}

impl RuntimeConfig {
    pub fn load(path: &Path) -> Result<Self> {
        let content =
            fs::read_to_string(path).with_context(|| format!("read config file {:?}", path))?;
        let raw: RawConfig =
            serde_json::from_str(&content).with_context(|| format!("parse config {:?}", path))?;
        let surfaces = raw
            .surface
            .into_iter()
            .map(|surface| SurfaceConfig {
                key: surface.key,
                save_folder: PathBuf::from(surface.save_folder),
            })
            .collect();
        let project_root = default_project_root();
        let coil_id = raw
            .test_data_coil_id
            .or_else(|| env_i64("RUST_IMAGE_TESTDATA_COIL_ID"))
            .or_else(|| env_i64("API_TESTDATA_COIL_ID"))
            .unwrap_or(193113);
        let data_dir = raw
            .test_data_dir
            .map(PathBuf::from)
            .or_else(|| env_path("RUST_IMAGE_TESTDATA_DIR"))
            .or_else(|| env_path("API_TESTDATA_DIR"))
            .unwrap_or_else(|| default_testdata_dir(&project_root, coil_id));
        let enabled = raw.test_mode.unwrap_or_else(|| {
            env_flag("RUST_IMAGE_TEST_MODE")
                || env_flag("API_DEVELOPER_MODE")
                || config_file_test_mode_enabled(&project_root)
        });
        let test_data = Some(TestDataConfig {
            enabled,
            coil_id,
            data_dir,
        });
        Ok(Self {
            surfaces,
            test_data,
        })
    }

    pub fn surface(&self, key: &str) -> Option<&SurfaceConfig> {
        self.surfaces.iter().find(|surface| surface.key == key)
    }
}

impl TestDataConfig {
    pub fn data_available(&self) -> bool {
        self.data_dir.exists()
            && (has_any_file(&self.data_dir, &["3D.npz", "3D.npy"])
                || ["S", "L"].iter().any(|surface| {
                    has_any_file(&self.data_dir.join(surface), &["3D.npz", "3D.npy"])
                }))
    }

    pub fn surface_asset_dir(&self, surface: &str) -> PathBuf {
        let surface_dir = self.data_dir.join(surface.to_ascii_uppercase());
        if surface_dir.exists() {
            return surface_dir;
        }
        self.data_dir.clone()
    }
}

pub fn default_server_config_path() -> PathBuf {
    let config_dir = default_config_3d_dir();
    default_server_config_path_for_dir(&config_dir)
}

fn default_server_config_path_for_dir(config_dir: &Path) -> PathBuf {
    let configs_dir = config_dir.join("configs");
    let preferred_name = if developer_mode_enabled(config_dir) {
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
    env_flag("API_DEVELOPER_MODE")
        || env_flag("RUST_IMAGE_DEVELOPER_MODE")
        || config_dir.join("developer_mode=true").exists()
}

fn default_project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")))
        .to_path_buf()
}

fn default_testdata_dir(project_root: &Path, coil_id: i64) -> PathBuf {
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

fn env_i64(name: &str) -> Option<i64> {
    std::env::var(name).ok()?.parse::<i64>().ok()
}

fn env_path(name: &str) -> Option<PathBuf> {
    std::env::var(name).ok().map(PathBuf::from)
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

fn config_file_test_mode_enabled(project_root: &Path) -> bool {
    [
        PathBuf::from(r"D:\CONFIG_3D\test_mode_config.json"),
        project_root.join("CONFIG_3D").join("test_mode_config.json"),
    ]
    .iter()
    .any(|path| read_test_mode_config(path).unwrap_or(false))
}

fn read_test_mode_config(path: &Path) -> Option<bool> {
    let value: Value = serde_json::from_str(&fs::read_to_string(path).ok()?).ok()?;
    value.get("test_mode").and_then(Value::as_bool)
}

fn has_any_file(dir: &Path, names: &[&str]) -> bool {
    names.iter().any(|name| dir.join(name).exists())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    static TEMP_COUNTER: AtomicUsize = AtomicUsize::new(0);

    fn unique_temp_dir() -> PathBuf {
        let counter = TEMP_COUNTER.fetch_add(1, Ordering::SeqCst);
        std::env::temp_dir().join(format!(
            "lg3d_rust_image_config_test_{}_{}",
            std::process::id(),
            counter
        ))
    }

    #[test]
    fn default_server_config_path_prefers_local_config_in_developer_mode() {
        let temp_dir = unique_temp_dir();
        let config_dir = temp_dir.join("CONFIG_3D");
        let configs_dir = config_dir.join("configs");
        fs::create_dir_all(&configs_dir).expect("config dir");
        fs::write(config_dir.join("developer_mode=true"), "").expect("developer marker");
        fs::write(configs_dir.join("Server3D.json"), "{}").expect("standard config");
        fs::write(configs_dir.join("Server3DLoc2.json"), "{}").expect("local config");

        let selected = default_server_config_path_for_dir(&config_dir);

        assert_eq!(selected, configs_dir.join("Server3DLoc2.json"));

        let _ = fs::remove_dir_all(temp_dir);
    }
}
