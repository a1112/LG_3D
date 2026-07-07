use std::collections::HashMap;
use std::fs::File;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, OnceLock};
use std::time::SystemTime;

use anyhow::{Context, Result, anyhow};
use ndarray::{Array2, ArrayD, Ix2};
use ndarray_npy::{NpzReader, read_npy};

const DEFAULT_DEPTH_CACHE_CAPACITY: usize = 4;

pub struct DepthMap {
    array: Array2<f64>,
}

impl DepthMap {
    pub fn height(&self) -> i32 {
        i32::try_from(self.array.nrows()).unwrap_or(i32::MAX)
    }

    pub fn width(&self) -> i32 {
        i32::try_from(self.array.ncols()).unwrap_or(i32::MAX)
    }

    pub fn value_f64(&self, x: i32, y: i32) -> Option<f64> {
        if x < 0 || y < 0 {
            return None;
        }
        self.array
            .get((usize::try_from(y).ok()?, usize::try_from(x).ok()?))
            .copied()
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct DepthFileMetadata {
    len: u64,
    modified: Option<SystemTime>,
}

struct CachedDepthMap {
    metadata: DepthFileMetadata,
    depth_map: Arc<DepthMap>,
    last_used: u64,
}

#[derive(Default)]
struct DepthCache {
    entries: HashMap<PathBuf, CachedDepthMap>,
    access_counter: u64,
}

impl DepthCache {
    fn get(&mut self, path: &Path, metadata: &DepthFileMetadata) -> Option<Arc<DepthMap>> {
        let is_current = self
            .entries
            .get(path)
            .map(|cached| cached.metadata == *metadata)
            .unwrap_or(false);
        if !is_current {
            return None;
        }

        let last_used = self.next_access();
        let cached = self.entries.get_mut(path).expect("current cache entry");
        cached.last_used = last_used;
        Some(Arc::clone(&cached.depth_map))
    }

    fn insert(
        &mut self,
        path: PathBuf,
        metadata: DepthFileMetadata,
        depth_map: Arc<DepthMap>,
        capacity: usize,
    ) {
        if capacity == 0 {
            return;
        }

        let last_used = self.next_access();
        self.entries.insert(
            path,
            CachedDepthMap {
                metadata,
                depth_map,
                last_used,
            },
        );
        self.evict_to_capacity(capacity);
    }

    fn evict_to_capacity(&mut self, capacity: usize) {
        while self.entries.len() > capacity {
            let Some(lru_path) = self
                .entries
                .iter()
                .min_by_key(|(_, cached)| cached.last_used)
                .map(|(path, _)| path.clone())
            else {
                return;
            };
            self.entries.remove(&lru_path);
        }
    }

    fn next_access(&mut self) -> u64 {
        self.access_counter = self.access_counter.saturating_add(1);
        self.access_counter
    }
}

static DEPTH_CACHE: OnceLock<Mutex<DepthCache>> = OnceLock::new();

pub fn load_depth_map_from_dir(surface_dir: &Path) -> Option<Arc<DepthMap>> {
    for name in ["3D.npz", "3D.npy"] {
        let path = surface_dir.join(name);
        if path.exists() {
            if let Ok(depth_map) = load_cached_depth_map(&path) {
                return Some(depth_map);
            }
        }
    }
    None
}

fn load_cached_depth_map(path: &Path) -> Result<Arc<DepthMap>> {
    let canonical_path = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    let metadata = depth_file_metadata(path)?;
    let cache = DEPTH_CACHE.get_or_init(|| Mutex::new(DepthCache::default()));
    {
        let mut cache_guard = cache.lock().expect("depth cache lock");
        if let Some(depth_map) = cache_guard.get(&canonical_path, &metadata) {
            return Ok(depth_map);
        }
    }

    let depth_map = Arc::new(load_depth_map(path)?);
    let mut cache_guard = cache.lock().expect("depth cache lock");
    cache_guard.insert(
        canonical_path,
        metadata,
        Arc::clone(&depth_map),
        depth_cache_capacity(),
    );
    Ok(depth_map)
}

fn depth_cache_capacity() -> usize {
    std::env::var("RUST_IMAGE_DEPTH_CACHE_CAPACITY")
        .ok()
        .or_else(|| std::env::var("RUST_API_DEPTH_CACHE_CAPACITY").ok())
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(DEFAULT_DEPTH_CACHE_CAPACITY)
}

fn depth_file_metadata(path: &Path) -> Result<DepthFileMetadata> {
    let metadata = std::fs::metadata(path)
        .with_context(|| format!("failed to read depth metadata: {}", path.display()))?;
    Ok(DepthFileMetadata {
        len: metadata.len(),
        modified: metadata.modified().ok(),
    })
}

fn load_depth_map(path: &Path) -> Result<DepthMap> {
    let extension = path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    let array = match extension.as_str() {
        "npy" => read_npy_array(path)?,
        "npz" => read_npz_array(path)?,
        _ => {
            return Err(anyhow!(
                "unsupported depth file extension: {}",
                path.display()
            ));
        }
    };
    let array = array
        .into_dimensionality::<Ix2>()
        .with_context(|| format!("depth array must be 2D: {}", path.display()))?;
    Ok(DepthMap { array })
}

fn read_npy_array(path: &Path) -> Result<ArrayD<f64>> {
    read_npy(path).with_context(|| format!("failed to read npy depth file: {}", path.display()))
}

fn read_npz_array(path: &Path) -> Result<ArrayD<f64>> {
    let file = File::open(path)
        .with_context(|| format!("failed to open npz depth file: {}", path.display()))?;
    let mut npz = NpzReader::new(file)
        .with_context(|| format!("failed to read npz depth file: {}", path.display()))?;
    let names = npz
        .names()
        .with_context(|| format!("failed to list npz arrays: {}", path.display()))?;
    let array_name = names
        .iter()
        .find(|name| name.as_str() == "array.npy")
        .or_else(|| names.first())
        .ok_or_else(|| anyhow!("npz depth file has no arrays: {}", path.display()))?;
    npz.by_name(array_name)
        .with_context(|| format!("failed to read npz array {array_name}: {}", path.display()))
}
