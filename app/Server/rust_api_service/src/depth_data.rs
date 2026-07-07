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
    median_nonzero: OnceLock<f64>,
}

impl DepthMap {
    pub fn height(&self) -> i32 {
        i32::try_from(self.array.nrows()).unwrap_or(i32::MAX)
    }

    pub fn width(&self) -> i32 {
        i32::try_from(self.array.ncols()).unwrap_or(i32::MAX)
    }

    pub fn value_i32(&self, x: i32, y: i32) -> Option<i32> {
        self.value_f64(x, y).map(|value| value.trunc() as i32)
    }

    pub fn value_f64(&self, x: i32, y: i32) -> Option<f64> {
        if x < 0 || y < 0 {
            return None;
        }
        self.array
            .get((usize::try_from(y).ok()?, usize::try_from(x).ok()?))
            .copied()
    }

    pub fn median_nonzero(&self) -> f64 {
        *self.median_nonzero.get_or_init(|| {
            #[cfg(test)]
            MEDIAN_NONZERO_COMPUTE_COUNT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

            self.compute_median_nonzero()
        })
    }

    fn compute_median_nonzero(&self) -> f64 {
        let mut values: Vec<f64> = self
            .array
            .iter()
            .copied()
            .filter(|value| *value != 0.0 && value.is_finite())
            .collect();
        if values.is_empty() {
            return 0.0;
        }
        let middle = values.len() / 2;
        let (_, upper_value, _) =
            values.select_nth_unstable_by(middle, |left, right| left.total_cmp(right));
        let upper_value = *upper_value;
        if values.len() % 2 == 1 {
            upper_value
        } else {
            let lower_value = values[..middle]
                .iter()
                .copied()
                .max_by(|left, right| left.total_cmp(right))
                .unwrap_or(upper_value);
            (lower_value + upper_value) / 2.0
        }
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

    #[cfg(test)]
    fn clear(&mut self) {
        self.entries.clear();
        self.access_counter = 0;
    }

    fn next_access(&mut self) -> u64 {
        self.access_counter = self.access_counter.saturating_add(1);
        self.access_counter
    }
}

static DEPTH_CACHE: OnceLock<Mutex<DepthCache>> = OnceLock::new();

#[cfg(test)]
static DEPTH_FILE_LOAD_COUNT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

#[cfg(test)]
static MEDIAN_NONZERO_COMPUTE_COUNT: std::sync::atomic::AtomicU64 =
    std::sync::atomic::AtomicU64::new(0);

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
    #[cfg(test)]
    DEPTH_FILE_LOAD_COUNT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
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
    std::env::var("RUST_API_DEPTH_CACHE_CAPACITY")
        .ok()
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

#[cfg(test)]
fn clear_depth_cache_for_tests() {
    if let Some(cache) = DEPTH_CACHE.get() {
        cache.lock().expect("depth cache lock").clear();
    }
    DEPTH_FILE_LOAD_COUNT.store(0, std::sync::atomic::Ordering::Relaxed);
}

#[cfg(test)]
fn depth_file_load_count_for_tests() -> u64 {
    DEPTH_FILE_LOAD_COUNT.load(std::sync::atomic::Ordering::Relaxed)
}

#[cfg(test)]
fn clear_median_nonzero_compute_count_for_tests() {
    MEDIAN_NONZERO_COMPUTE_COUNT.store(0, std::sync::atomic::Ordering::Relaxed);
}

#[cfg(test)]
fn median_nonzero_compute_count_for_tests() -> u64 {
    MEDIAN_NONZERO_COMPUTE_COUNT.load(std::sync::atomic::Ordering::Relaxed)
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
    Ok(DepthMap {
        array,
        median_nonzero: OnceLock::new(),
    })
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

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::sync::{Mutex, OnceLock};
    use std::time::{SystemTime, UNIX_EPOCH};

    use ndarray::arr2;
    use ndarray_npy::write_npy;

    use super::{
        clear_depth_cache_for_tests, clear_median_nonzero_compute_count_for_tests,
        depth_file_load_count_for_tests, load_depth_map_from_dir,
        median_nonzero_compute_count_for_tests,
    };

    static TEMP_DIR_COUNTER: AtomicU64 = AtomicU64::new(0);
    static TEST_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

    fn unique_temp_dir() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time")
            .as_nanos();
        let counter = TEMP_DIR_COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!("lg3d_depth_cache_test_{suffix}_{counter}"))
    }

    #[test]
    fn depth_map_cache_reuses_unchanged_depth_file() {
        let _guard = TEST_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("test lock");
        clear_depth_cache_for_tests();
        let dir = unique_temp_dir();
        fs::create_dir_all(&dir).expect("temp dir");
        write_npy(dir.join("3D.npy"), &arr2(&[[10.0]])).expect("write npy");

        let first = load_depth_map_from_dir(&dir).expect("first load");
        let second = load_depth_map_from_dir(&dir).expect("second load");

        assert_eq!(first.value_i32(0, 0), Some(10));
        assert_eq!(second.value_i32(0, 0), Some(10));
        assert_eq!(depth_file_load_count_for_tests(), 1);

        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn depth_map_caches_median_nonzero_for_repeated_coil_info_requests() {
        let _guard = TEST_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("test lock");
        clear_depth_cache_for_tests();
        clear_median_nonzero_compute_count_for_tests();
        let dir = unique_temp_dir();
        fs::create_dir_all(&dir).expect("temp dir");
        write_npy(
            dir.join("3D.npy"),
            &arr2(&[[0.0, 10.0, 30.0], [50.0, 0.0, 70.0]]),
        )
        .expect("write npy");

        let depth_map = load_depth_map_from_dir(&dir).expect("depth map");

        assert_eq!(depth_map.median_nonzero(), 40.0);
        assert_eq!(depth_map.median_nonzero(), 40.0);
        assert_eq!(median_nonzero_compute_count_for_tests(), 1);

        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn depth_map_cache_invalidates_when_depth_file_metadata_changes() {
        let _guard = TEST_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("test lock");
        clear_depth_cache_for_tests();
        let dir = unique_temp_dir();
        fs::create_dir_all(&dir).expect("temp dir");
        let path = dir.join("3D.npy");
        write_npy(&path, &arr2(&[[10.0]])).expect("write npy");

        let first = load_depth_map_from_dir(&dir).expect("first load");
        std::thread::sleep(std::time::Duration::from_millis(20));
        write_npy(&path, &arr2(&[[42.0, 43.0], [44.0, 45.0]])).expect("rewrite npy");
        let second = load_depth_map_from_dir(&dir).expect("second load");

        assert_eq!(first.height(), 1);
        assert_eq!(second.height(), 2);
        assert_eq!(second.value_i32(0, 0), Some(42));
        assert_eq!(depth_file_load_count_for_tests(), 2);

        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn depth_map_cache_evicts_least_recently_used_depth_file_when_capacity_is_exceeded() {
        let _guard = TEST_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("test lock");
        clear_depth_cache_for_tests();
        let root = unique_temp_dir();
        fs::create_dir_all(&root).expect("temp root");
        let mut dirs = Vec::new();
        for index in 0..5 {
            let dir = root.join(format!("coil_{index}"));
            fs::create_dir_all(&dir).expect("temp depth dir");
            write_npy(dir.join("3D.npy"), &arr2(&[[index as f64]])).expect("write npy");
            dirs.push(dir);
        }

        for dir in dirs.iter().take(4) {
            load_depth_map_from_dir(dir).expect("initial cache fill");
        }
        assert_eq!(depth_file_load_count_for_tests(), 4);

        load_depth_map_from_dir(&dirs[0]).expect("refresh first cache entry");
        assert_eq!(depth_file_load_count_for_tests(), 4);

        load_depth_map_from_dir(&dirs[4]).expect("exceed cache capacity");
        assert_eq!(depth_file_load_count_for_tests(), 5);

        load_depth_map_from_dir(&dirs[1]).expect("reload evicted least-recently-used entry");
        assert_eq!(depth_file_load_count_for_tests(), 6);

        load_depth_map_from_dir(&dirs[0]).expect("recently used entry should still be cached");
        assert_eq!(depth_file_load_count_for_tests(), 6);

        let _ = fs::remove_dir_all(root);
    }
}
