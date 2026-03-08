use std::collections::HashMap;
use std::io::Cursor;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};

use axum::body::Body;
use axum::extract::{Path as AxumPath, Query, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use bytes::Bytes;
use image::codecs::jpeg::JpegEncoder;
use image::imageops::FilterType;
use image::{DynamicImage, GenericImageView, GrayImage, ImageReader};
use lru::LruCache;
use quick_xml::de::from_str;
use serde::Deserialize;
use serde::Serialize;
use tracing::warn;

use crate::app_config::{RuntimeConfig, SurfaceConfig};

#[derive(Clone)]
pub struct AppState {
    config: RuntimeConfig,
    detection_index: Arc<RwLock<HashMap<String, Arc<Vec<DetectionCandidate>>>>>,
    file_cache: Arc<Mutex<LruCache<String, Bytes>>>,
    area_gray_cache: Arc<Mutex<LruCache<String, Arc<GrayImage>>>>,
    tile_bytes_cache: Arc<Mutex<LruCache<String, Bytes>>>,
}

impl AppState {
    pub fn new(config: RuntimeConfig) -> Self {
        Self {
            config,
            detection_index: Arc::new(RwLock::new(HashMap::new())),
            file_cache: Arc::new(Mutex::new(LruCache::new(NonZeroUsize::new(64).expect("non-zero")))),
            area_gray_cache: Arc::new(Mutex::new(LruCache::new(NonZeroUsize::new(1).expect("non-zero")))),
            tile_bytes_cache: Arc::new(Mutex::new(LruCache::new(NonZeroUsize::new(64).expect("non-zero")))),
        }
    }

    fn surface(&self, key: &str) -> Option<&SurfaceConfig> {
        self.config.surface(key)
    }
}

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    status: &'static str,
    service: &'static str,
}

#[derive(Debug, Deserialize)]
pub struct AreaQuery {
    #[serde(default)]
    pub row: Option<i32>,
    #[serde(default)]
    pub col: Option<i32>,
    #[serde(default)]
    pub count: Option<i32>,
    #[serde(default)]
    pub level: Option<i32>,
}

#[derive(Debug, Serialize)]
struct ImageMeta {
    width: u32,
    height: u32,
}

#[derive(Debug, Clone)]
struct DetectionCandidate {
    xmin: i32,
    ymin: i32,
    xmax: i32,
    ymax: i32,
    image_path: PathBuf,
}

#[derive(Debug, Deserialize)]
struct Annotation {
    #[serde(rename = "object", default)]
    objects: Vec<AnnotationObject>,
}

#[derive(Debug, Deserialize)]
struct AnnotationObject {
    bndbox: Option<BoundingBox>,
}

#[derive(Debug, Deserialize)]
struct BoundingBox {
    xmin: i32,
    ymin: i32,
    xmax: i32,
    ymax: i32,
}

pub async fn health() -> impl IntoResponse {
    axum::Json(HealthResponse {
        status: "ok",
        service: "rust_image_service",
    })
}

pub async fn preview_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_)): AxumPath<(String, String, String)>,
) -> Response {
    match resolve_preview_path(&state, &surface_key, &coil_id, &type_) {
        Some(path) => serve_file(&state, path),
        None => not_found("preview image not found"),
    }
}

pub async fn source_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_)): AxumPath<(String, String, String)>,
) -> Response {
    match resolve_source_path(&state, &surface_key, &coil_id, &type_, false) {
        Some(path) => serve_file(&state, path),
        None => not_found("source image not found"),
    }
}

pub async fn area_image_compat(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id)): AxumPath<(String, String)>,
    Query(query): Query<AreaQuery>,
) -> Response {
    let row = query.row.unwrap_or(0);
    let col = query.col.unwrap_or(0);
    let count = query.count.unwrap_or(0);
    let level = query.level.unwrap_or(4).clamp(0, 4);
    let tile_count = 3;

    if count == 0 {
        return match resolve_area_meta(&state, &surface_key, &coil_id) {
            Some(meta) => axum::Json(meta).into_response(),
            None => not_found("area image metadata not found"),
        };
    }

    if row == -2 {
        return match resolve_preview_path(&state, &surface_key, &coil_id, "AREA") {
            Some(path) => serve_file(&state, path),
            None => not_found("area preview not found"),
        };
    }

    if row == -1 {
        return match resolve_source_path(&state, &surface_key, &coil_id, "AREA", false) {
            Some(path) => serve_file(&state, path),
            None => not_found("area source not found"),
        };
    }

    if count == 1 {
        return StatusCode::NO_CONTENT.into_response();
    }

    match resolve_area_tile_path(&state, &surface_key, &coil_id, row, col, level) {
        Some(path) => {
            let mut response = serve_file(&state, path);
            set_tile_headers(&mut response, level, "hit");
            response
        }
        None => match generate_area_tile_response(&state, &surface_key, &coil_id, row, col, tile_count, level) {
            Some(response) => response,
            None => not_found("tile cache not found"),
        },
    }
}

pub async fn defect_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_, x, y, w, h)): AxumPath<(
        String,
        i32,
        String,
        i32,
        i32,
        i32,
        i32,
    )>,
) -> Response {
    if let Some(path) = resolve_defect_tile(&state, &surface_key, coil_id, x, y, w, h) {
        return serve_file(&state, path);
    }

    match resolve_source_path(&state, &surface_key, &coil_id.to_string(), &type_, false) {
        Some(path) => serve_file(&state, path),
        None => not_found("defect image source not found"),
    }
}

fn resolve_preview_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
) -> Option<PathBuf> {
    let surface = state.surface(surface_key)?;
    let preview_dir = surface.save_folder.join(coil_id).join("preview");
    let jpg = preview_dir.join(format!("{type_}.jpg"));
    if jpg.exists() {
        return Some(jpg);
    }
    if type_ == "AREA" {
        let mut entries = std::fs::read_dir(&preview_dir).ok()?;
        while let Some(Ok(entry)) = entries.next() {
            let path = entry.path();
            if path
                .file_stem()
                .and_then(|stem| stem.to_str())
                .map(|stem| stem.eq_ignore_ascii_case("AREA"))
                .unwrap_or(false)
            {
                return Some(path);
            }
        }
    }
    let png = preview_dir.join(format!("{type_}.png"));
    if png.exists() {
        return Some(png);
    }
    None
}

fn resolve_source_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    mask: bool,
) -> Option<PathBuf> {
    let surface = state.surface(surface_key)?;
    let base = surface.save_folder.join(coil_id);
    if mask {
        let mask_path = base.join("mask").join(format!("{type_}.png"));
        return mask_path.exists().then_some(mask_path);
    }
    let jpg_path = base.join("jpg").join(format!("{type_}.jpg"));
    jpg_path.exists().then_some(jpg_path)
}

fn resolve_area_meta(state: &AppState, surface_key: &str, coil_id: &str) -> Option<ImageMeta> {
    if let Some(tile_path) = resolve_area_l4_tile_path(state, surface_key, coil_id, 0, 0) {
        let (tile_width, tile_height) = image_dimensions(state, &tile_path)?;
        if tile_width > 0 && tile_height > 0 {
            return Some(ImageMeta {
                width: tile_width * 3,
                height: tile_height * 3,
            });
        }
    }
    let source_path = resolve_source_path(state, surface_key, coil_id, "AREA", false)?;
    let (width, height) = image_dimensions(state, &source_path)?;
    Some(ImageMeta { width, height })
}

fn resolve_area_tile_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    row: i32,
    col: i32,
    level: i32,
) -> Option<PathBuf> {
    if !(0..=2).contains(&row) || !(0..=2).contains(&col) {
        return None;
    }
    let source_path = resolve_source_path(state, surface_key, coil_id, "AREA", false)?;
    let coil_dir = source_path.parent()?.parent()?;
    let tile_path = coil_dir
        .join("cache")
        .join("area")
        .join("tild")
        .join(format!("L{level}"))
        .join(format!("{col}_{row}.jpg"));
    tile_path.exists().then_some(tile_path)
}

fn resolve_area_l4_tile_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    row: i32,
    col: i32,
) -> Option<PathBuf> {
    resolve_area_tile_path(state, surface_key, coil_id, row, col, 4)
}

fn generate_area_tile_response(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    row: i32,
    col: i32,
    tile_count: i32,
    level: i32,
) -> Option<Response> {
    if !(0..=2).contains(&row) || !(0..=2).contains(&col) {
        return None;
    }

    let source_path = resolve_source_path(state, surface_key, coil_id, "AREA", false)?;
    let cache_key = format!("{}|{}|{}|{}", source_path.display(), level, row, col);
    if let Some(bytes) = get_cached_tile_bytes(state, &cache_key) {
        let mut response = jpeg_cached_bytes_response(bytes);
        set_tile_headers(&mut response, level, "memory");
        return Some(response);
    }

    if let Some(l4_path) = resolve_area_l4_tile_path(state, surface_key, coil_id, row, col) {
        let tile = load_image(state, &l4_path)?;
        let bytes = encode_area_tile_for_level(tile, level)?;
        let mut response = jpeg_bytes_response(store_tile_bytes(state, cache_key, bytes));
        set_tile_headers(&mut response, level, "miss");
        return Some(response);
    }

    let image = load_area_gray_image(state, &source_path)?;
    let tile = crop_area_tile_gray(image.as_ref(), row, col, tile_count)?;
    let bytes = encode_area_gray_tile_for_level(tile, level)?;
    let mut response = jpeg_bytes_response(store_tile_bytes(state, cache_key, bytes));
    set_tile_headers(&mut response, level, "fallback");
    Some(response)
}

fn crop_area_tile_gray(image: &GrayImage, row: i32, col: i32, tile_count: i32) -> Option<GrayImage> {
    let (width, height) = image.dimensions();
    let tile_w = width / tile_count as u32;
    let tile_h = height / tile_count as u32;
    if tile_w == 0 || tile_h == 0 {
        return None;
    }
    let x = row as u32 * tile_w;
    let y = col as u32 * tile_h;
    Some(image::imageops::crop_imm(image, x, y, tile_w, tile_h).to_image())
}

fn encode_area_tile_for_level(tile: DynamicImage, level: i32) -> Option<Vec<u8>> {
    let (target_size, quality) = tile_level_config(level);
    let resized = if level < 4 {
        resize_tile_if_needed(tile, target_size)
    } else {
        tile
    };
    encode_jpeg(resized, quality)
}

fn encode_area_gray_tile_for_level(tile: GrayImage, level: i32) -> Option<Vec<u8>> {
    let (target_size, quality) = tile_level_config(level);
    let resized = if level < 4 {
        resize_gray_tile_if_needed(tile, target_size)
    } else {
        tile
    };
    encode_jpeg(DynamicImage::ImageLuma8(resized), quality)
}

fn tile_level_config(level: i32) -> (u32, u8) {
    match level {
        0 => (340, 60),
        1 => (682, 70),
        2 => (1364, 80),
        3 => (2728, 90),
        _ => (5460, 95),
    }
}

fn resize_tile_if_needed(tile: DynamicImage, target_size: u32) -> DynamicImage {
    let (width, height) = tile.dimensions();
    let max_side = width.max(height);
    if max_side <= target_size {
        return tile;
    }
    let scale = target_size as f64 / max_side as f64;
    let new_width = ((width as f64 * scale).floor() as u32).max(1);
    let new_height = ((height as f64 * scale).floor() as u32).max(1);
    tile.resize_exact(new_width, new_height, FilterType::Triangle)
}

fn resize_gray_tile_if_needed(tile: GrayImage, target_size: u32) -> GrayImage {
    let (width, height) = tile.dimensions();
    let max_side = width.max(height);
    if max_side <= target_size {
        return tile;
    }
    let scale = target_size as f64 / max_side as f64;
    let new_width = ((width as f64 * scale).floor() as u32).max(1);
    let new_height = ((height as f64 * scale).floor() as u32).max(1);
    image::imageops::resize(&tile, new_width, new_height, FilterType::Triangle)
}

fn load_image(state: &AppState, path: &Path) -> Option<DynamicImage> {
    let bytes = get_file_bytes(state, path)?;
    let mut reader = ImageReader::new(Cursor::new(bytes.as_ref())).with_guessed_format().ok()?;
    reader.no_limits();
    reader.decode().ok()
}

fn load_area_gray_image(state: &AppState, path: &Path) -> Option<Arc<GrayImage>> {
    let key = path.to_string_lossy().to_string();
    if let Ok(mut cache) = state.area_gray_cache.lock() {
        if let Some(image) = cache.get(&key) {
            return Some(image.clone());
        }
    }

    let bytes = get_file_bytes(state, path)?;
    let mut reader = ImageReader::new(Cursor::new(bytes.as_ref())).with_guessed_format().ok()?;
    reader.no_limits();
    let image = Arc::new(reader.decode().ok()?.into_luma8());

    if let Ok(mut cache) = state.area_gray_cache.lock() {
        cache.put(key, image.clone());
    }
    Some(image)
}

fn encode_jpeg(image: DynamicImage, quality: u8) -> Option<Vec<u8>> {
    let mut bytes = Vec::new();
    let mut encoder = JpegEncoder::new_with_quality(&mut bytes, quality);
    encoder.encode_image(&image).ok()?;
    Some(bytes)
}

fn image_dimensions(state: &AppState, path: &Path) -> Option<(u32, u32)> {
    let bytes = get_file_bytes(state, path)?;
    let reader = ImageReader::new(Cursor::new(bytes.as_ref())).with_guessed_format().ok()?;
    reader.into_dimensions().ok()
}

fn resolve_defect_tile(
    state: &AppState,
    _surface_key: &str,
    coil_id: i32,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> Option<PathBuf> {
    let candidates = detection_candidates(state, coil_id)?;
    let cx = x + w / 2;
    let cy = y + h / 2;
    candidates
        .iter()
        .find(|candidate| candidate.xmin <= cx && cx <= candidate.xmax && candidate.ymin <= cy && cy <= candidate.ymax)
        .map(|candidate| candidate.image_path.clone())
}

fn detection_candidates(state: &AppState, coil_id: i32) -> Option<Arc<Vec<DetectionCandidate>>> {
    let cache_key = coil_id.to_string();
    if let Ok(guard) = state.detection_index.read() {
        if let Some(cached) = guard.get(&cache_key) {
            return Some(cached.clone());
        }
    }

    let save_folder = state.config.surfaces.first()?.save_folder.clone();
    let detection_dir = save_folder.parent()?.join(coil_id.to_string()).join("detection");
    if !detection_dir.exists() {
        return None;
    }

    let mut candidates = Vec::new();
    for defect_dir in std::fs::read_dir(&detection_dir).ok()? {
        let defect_dir = defect_dir.ok()?.path();
        if !defect_dir.is_dir() {
            continue;
        }
        for entry in std::fs::read_dir(defect_dir).ok()? {
            let entry_path = entry.ok()?.path();
            if entry_path.extension().and_then(|ext| ext.to_str()) != Some("xml") {
                continue;
            }
            let image_path = entry_path.with_extension("png");
            if !image_path.exists() {
                continue;
            }
            let xml = match std::fs::read_to_string(&entry_path) {
                Ok(xml) => xml,
                Err(err) => {
                    warn!("failed to read {:?}: {}", entry_path, err);
                    continue;
                }
            };
            let annotation: Annotation = match from_str(&xml) {
                Ok(annotation) => annotation,
                Err(err) => {
                    warn!("failed to parse {:?}: {}", entry_path, err);
                    continue;
                }
            };
            for object in annotation.objects {
                let Some(bbox) = object.bndbox else {
                    continue;
                };
                candidates.push(DetectionCandidate {
                    xmin: bbox.xmin,
                    ymin: bbox.ymin,
                    xmax: bbox.xmax,
                    ymax: bbox.ymax,
                    image_path: image_path.clone(),
                });
            }
        }
    }

    let candidates = Arc::new(candidates);
    if let Ok(mut guard) = state.detection_index.write() {
        guard.insert(cache_key, candidates.clone());
    }
    Some(candidates)
}

fn serve_file(state: &AppState, path: PathBuf) -> Response {
    let content_type = mime_guess::from_path(&path)
        .first_raw()
        .unwrap_or("application/octet-stream");
    let bytes = match get_file_bytes(state, &path) {
        Some(bytes) => bytes,
        None => return not_found("file not found"),
    };
    let mut headers = HeaderMap::new();
    if let Ok(value) = HeaderValue::from_str(content_type) {
        headers.insert(header::CONTENT_TYPE, value);
    }
    (StatusCode::OK, headers, Body::from(bytes)).into_response()
}

fn jpeg_bytes_response(bytes: Vec<u8>) -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(header::CONTENT_TYPE, HeaderValue::from_static("image/jpeg"));
    (StatusCode::OK, headers, bytes).into_response()
}

fn jpeg_cached_bytes_response(bytes: Bytes) -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(header::CONTENT_TYPE, HeaderValue::from_static("image/jpeg"));
    (StatusCode::OK, headers, Body::from(bytes)).into_response()
}

fn set_tile_headers(response: &mut Response, level: i32, cache: &'static str) {
    response.headers_mut().insert(
        HeaderName::from_static("x-tile-level"),
        HeaderValue::from_str(&level.to_string()).unwrap_or(HeaderValue::from_static("4")),
    );
    response.headers_mut().insert(
        HeaderName::from_static("x-cache"),
        HeaderValue::from_static(cache),
    );
}

fn not_found(message: &'static str) -> Response {
    (StatusCode::NOT_FOUND, message).into_response()
}

fn get_file_bytes(state: &AppState, path: &Path) -> Option<Bytes> {
    let key = path.to_string_lossy().to_string();
    if let Ok(mut cache) = state.file_cache.lock() {
        if let Some(bytes) = cache.get(&key) {
            return Some(bytes.clone());
        }
    }

    let bytes = match std::fs::read(path) {
        Ok(bytes) => Bytes::from(bytes),
        Err(err) => {
            warn!("failed to read {:?}: {}", path, err);
            return None;
        }
    };

    if let Ok(mut cache) = state.file_cache.lock() {
        cache.put(key, bytes.clone());
    }
    Some(bytes)
}

fn get_cached_tile_bytes(state: &AppState, key: &str) -> Option<Bytes> {
    if let Ok(mut cache) = state.tile_bytes_cache.lock() {
        if let Some(bytes) = cache.get(key) {
            return Some(bytes.clone());
        }
    }
    None
}

fn store_tile_bytes(state: &AppState, key: String, bytes: Vec<u8>) -> Vec<u8> {
    if let Ok(mut cache) = state.tile_bytes_cache.lock() {
        cache.put(key, Bytes::from(bytes.clone()));
    }
    bytes
}

use axum::http::HeaderName;
