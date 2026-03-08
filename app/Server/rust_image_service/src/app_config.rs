use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;

#[derive(Debug, Clone)]
pub struct RuntimeConfig {
    pub surfaces: Vec<SurfaceConfig>,
}

#[derive(Debug, Clone)]
pub struct SurfaceConfig {
    pub key: String,
    pub save_folder: PathBuf,
}

#[derive(Debug, Deserialize)]
struct RawConfig {
    surface: Vec<RawSurfaceConfig>,
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
        Ok(Self { surfaces })
    }

    pub fn surface(&self, key: &str) -> Option<&SurfaceConfig> {
        self.surfaces.iter().find(|surface| surface.key == key)
    }
}
