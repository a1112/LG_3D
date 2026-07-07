use std::collections::HashMap;
use std::io::Cursor;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use axum::body::Body;
use axum::extract::{Path as AxumPath, RawQuery, State};
use axum::http::{HeaderMap, HeaderName, HeaderValue, StatusCode, header};
use axum::response::{IntoResponse, Response};
use bytes::Bytes;
use image::codecs::jpeg::JpegEncoder;
use image::imageops::FilterType;
use image::{
    DynamicImage, GrayImage, ImageFormat, ImageReader, Luma, Rgb, RgbImage, Rgba, RgbaImage,
};
use lru::LruCache;
use quick_xml::de::from_str;
use serde::Deserialize;
use serde::Serialize;
use tracing::warn;

use crate::app_config::{RuntimeConfig, SurfaceConfig};
use crate::depth_data::{DepthMap, load_depth_map_from_dir};

#[derive(Clone)]
pub struct AppState {
    config: RuntimeConfig,
    file_cache: Arc<Mutex<LruCache<String, Bytes>>>,
    area_gray_cache: Arc<Mutex<LruCache<String, Arc<GrayImage>>>>,
    tile_bytes_cache: Arc<Mutex<LruCache<String, Bytes>>>,
}

impl AppState {
    pub fn new(config: RuntimeConfig) -> Self {
        Self {
            config,
            file_cache: Arc::new(Mutex::new(LruCache::new(
                NonZeroUsize::new(64).expect("non-zero"),
            ))),
            area_gray_cache: Arc::new(Mutex::new(LruCache::new(
                NonZeroUsize::new(1).expect("non-zero"),
            ))),
            tile_bytes_cache: Arc::new(Mutex::new(LruCache::new(
                NonZeroUsize::new(64).expect("non-zero"),
            ))),
        }
    }

    fn surface(&self, key: &str) -> Option<&SurfaceConfig> {
        self.config.surface(key)
    }

    fn testdata_surface_dir_for_string_request(&self, surface_key: &str) -> Option<PathBuf> {
        let test_data = self.config.test_data.as_ref()?;
        if test_data.enabled && test_data.data_available() {
            return Some(test_data.surface_asset_dir(surface_key));
        }
        None
    }

    fn production_surface_dir_for_coil(&self, surface_key: &str, coil_id: i64) -> Option<PathBuf> {
        self.surface(surface_key)
            .map(|surface| surface.save_folder.join(coil_id.to_string()))
    }

    fn main_api_test_mode_surface_dir_for_request(&self, surface_key: &str) -> Option<PathBuf> {
        let test_data = self.config.test_data.as_ref()?;
        if test_data.enabled && test_data.data_available() {
            return Some(test_data.surface_asset_dir(surface_key));
        }
        None
    }

    fn main_api_surface_dir_for_request(&self, surface_key: &str, coil_id: i64) -> Option<PathBuf> {
        self.main_api_test_mode_surface_dir_for_request(surface_key)
            .or_else(|| self.production_surface_dir_for_coil(surface_key, coil_id))
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

#[derive(Debug, Deserialize)]
pub struct CoilDataAreaQuery {
    #[serde(default)]
    pub scale: Option<f64>,
    #[serde(default)]
    pub mask: Option<bool>,
    #[serde(default, rename = "valueFrom")]
    pub value_from: Option<f64>,
    #[serde(default, rename = "valueTo")]
    pub value_to: Option<f64>,
    #[serde(default)]
    pub r: Option<u8>,
    #[serde(default)]
    pub g: Option<u8>,
    #[serde(default)]
    pub b: Option<u8>,
}

#[derive(Clone, Debug, Default, Deserialize)]
pub struct RenderQuery {
    #[serde(default)]
    pub thumbnail: Option<bool>,
    #[serde(default)]
    pub grayscale: Option<bool>,
    #[serde(default)]
    pub scale: Option<f64>,
    #[serde(default)]
    pub mask: Option<bool>,
    #[serde(default)]
    pub min_value: Option<i32>,
    #[serde(default)]
    pub max_value: Option<i32>,
    #[serde(default, rename = "minValue")]
    pub min_value_compat: Option<i32>,
    #[serde(default, rename = "maxValue")]
    pub max_value_compat: Option<i32>,
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

#[derive(Debug, Deserialize)]
pub struct ErrorImageQuery {
    #[serde(default)]
    pub scale: Option<f64>,
    #[serde(default, rename = "minValue")]
    pub min_value: Option<f64>,
    #[serde(default, rename = "maxValue")]
    pub max_value: Option<f64>,
    #[serde(default)]
    pub force_cache: Option<bool>,
}

#[derive(Debug, Serialize)]
struct ImageMeta {
    width: u32,
    height: u32,
}

const PLACEHOLDER_JPEG: &[u8] = &[0xff, 0xd8, 0xff, 0xdb, 0x00, 0x43, 0x00, 0xff, 0xd9];
const DEFAULT_SCAN3D_SCALE_Z: f64 = 0.016229506582021713;

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
        None => missing_image_response(),
    }
}

pub async fn source_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_)): AxumPath<(String, String, String)>,
) -> Response {
    match resolve_source_path(&state, &surface_key, &coil_id, &type_, false) {
        Some(path) => serve_file(&state, path),
        None => missing_image_response(),
    }
}

pub async fn classifier_image(
    State(state): State<Arc<AppState>>,
    AxumPath((coil_id, surface_key, class_name, x, y, w, h)): AxumPath<(
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
        state.production_surface_dir_for_coil(&surface_key, coil_id)
    {
        if let Some(path) =
            cached_classifier_image_path(&production_surface_dir, &class_name, coil_id, x, y)
        {
            return serve_file(&state, path);
        }
    }

    let Some(surface_dir) = state.main_api_surface_dir_for_request(&surface_key, coil_id) else {
        return missing_image_response();
    };

    let Some(source) = load_named_rgb_image_from_surface_dir(&state, &surface_dir, "GRAY") else {
        return missing_image_response();
    };
    let Some((clip_x, clip_y, clip_w, clip_h)) =
        image_clip_box(x, y, w, h, source.width(), source.height())
    else {
        return missing_image_response();
    };

    let crop = image::imageops::crop_imm(&source, clip_x, clip_y, clip_w, clip_h).to_image();
    match encode_jpeg(DynamicImage::ImageRgb8(crop), 90) {
        Some(bytes) => jpeg_bytes_response(bytes),
        None => missing_image_response(),
    }
}

pub async fn render_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id)): AxumPath<(String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let query = match parse_render_query(raw_query.as_deref()) {
        Ok(query) => query,
        Err(response) => return response,
    };
    let Some(surface_dir) = image_request_coil_dir(&state, &surface_key, &coil_id) else {
        return render_placeholder_response(&query);
    };
    render_image_from_surface_dir(&state, &surface_dir, &query)
        .unwrap_or_else(|| render_placeholder_response(&query))
}

pub async fn error_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id)): AxumPath<(String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let query = match parse_error_image_query(raw_query.as_deref()) {
        Ok(query) => query,
        Err(response) => return response,
    };
    if let Some(path) = resolve_error_cache_path(&state, &surface_key, &coil_id, &query) {
        return serve_file(&state, path);
    }
    if query.force_cache.unwrap_or(false) {
        return transparent_png_response(100, 100);
    }
    let Some(surface_dir) = image_request_coil_dir(&state, &surface_key, &coil_id) else {
        return transparent_png_response(100, 100);
    };
    let Some(depth_map) = load_depth_map_from_dir(&surface_dir) else {
        return transparent_png_response(100, 100);
    };
    if let Some(bytes) = generate_error_png(&depth_map, &query) {
        return png_bytes_response(bytes);
    }
    transparent_png_response(100, 100)
}

pub async fn coil_data_area_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id)): AxumPath<(String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let query = match parse_coil_data_area_query(raw_query.as_deref()) {
        Ok(query) => query,
        Err(response) => return response,
    };
    if coil_id
        .parse::<i64>()
        .ok()
        .filter(|value| *value >= 0)
        .is_none()
    {
        return python_internal_server_error_response();
    }
    let Some(surface_dir) = image_request_coil_dir(&state, &surface_key, &coil_id) else {
        return python_internal_server_error_response();
    };
    let Some(depth_map) = load_depth_map_from_dir(&surface_dir) else {
        return python_internal_server_error_response();
    };
    let _mask = query.mask.unwrap_or(true);
    match generate_area_png(&depth_map, &query) {
        Some(bytes) => png_bytes_response(bytes),
        None => transparent_png_response(100, 100),
    }
}

pub async fn area_image_compat(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id)): AxumPath<(String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let query = match parse_area_query(raw_query.as_deref()) {
        Ok(query) => query,
        Err(response) => return response,
    };
    area_image_response(&state, &surface_key, &coil_id, "AREA", query)
}

pub async fn area_image_typed(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_)): AxumPath<(String, String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let type_ = normalize_area_image_type(&type_);
    let query = match parse_area_query(raw_query.as_deref()) {
        Ok(query) => query,
        Err(response) => return response,
    };
    area_image_response(&state, &surface_key, &coil_id, &type_, query)
}

fn normalize_area_image_type(type_: &str) -> String {
    match type_.to_ascii_uppercase().as_str() {
        "AREA_MASK" => "AREA_MASK".to_string(),
        _ => "AREA".to_string(),
    }
}

fn area_image_response(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    query: AreaQuery,
) -> Response {
    if let Err(response) = validate_area_query_ranges(&query) {
        return response;
    }
    let row = query.row.unwrap_or(0);
    let col = query.col.unwrap_or(0);
    let count = query.count.unwrap_or(0);
    let level = query.level.unwrap_or(4);
    let tile_count = 3;

    if count == 0 {
        return match resolve_area_meta(state, surface_key, coil_id, type_) {
            Some(meta) => axum::Json(meta).into_response(),
            None => missing_image_response(),
        };
    }

    if row == -2 {
        return match area_image_file_response(state, surface_key, coil_id, "preview", type_) {
            Some(response) => response,
            None => missing_image_response(),
        };
    }

    if row == -1 {
        return match area_image_source_response(state, surface_key, coil_id, type_) {
            Some(response) => response,
            None => missing_image_response(),
        };
    }

    if count == 1 {
        return match area_image_source_response(state, surface_key, coil_id, type_) {
            Some(response) => response,
            None => missing_image_response(),
        };
    }

    match resolve_area_tile_path(state, surface_key, coil_id, type_, row, col, level) {
        Some(path) => {
            let mut response = serve_file(state, path);
            set_tile_headers(&mut response, level, "hit");
            response
        }
        None => match generate_area_tile_response(
            state,
            surface_key,
            coil_id,
            type_,
            row,
            col,
            tile_count,
            level,
        ) {
            Some(response) => response,
            None => {
                let mut response = missing_image_response();
                set_tile_headers(&mut response, level, "missing");
                response
            }
        },
    }
}

fn validate_area_query_ranges(query: &AreaQuery) -> Result<(), Response> {
    validate_optional_i32_range("row", query.row, -2, 2)?;
    validate_optional_i32_range("col", query.col, 0, 2)?;
    validate_optional_i32_range("count", query.count, 0, 3)?;
    validate_optional_i32_range("level", query.level, 0, 4)?;
    Ok(())
}

fn parse_area_query(raw_query: Option<&str>) -> Result<AreaQuery, Response> {
    let query = parse_raw_query(raw_query.unwrap_or_default());
    Ok(AreaQuery {
        row: parse_optional_i32_query_range(&query, "row", -2, 2)?,
        col: parse_optional_i32_query_range(&query, "col", 0, 2)?,
        count: parse_optional_i32_query_range(&query, "count", 0, 3)?,
        level: parse_optional_i32_query_range(&query, "level", 0, 4)?,
    })
}

fn parse_render_query(raw_query: Option<&str>) -> Result<RenderQuery, Response> {
    let query = parse_raw_query(raw_query.unwrap_or_default());
    Ok(RenderQuery {
        thumbnail: parse_optional_bool_query(&query, "thumbnail")?,
        grayscale: parse_optional_bool_query(&query, "grayscale")?,
        scale: parse_optional_f64_query(&query, "scale")?,
        mask: parse_optional_bool_query(&query, "mask")?,
        min_value: parse_optional_i32_query(&query, "min_value")?,
        max_value: parse_optional_i32_query(&query, "max_value")?,
        min_value_compat: parse_optional_i32_query(&query, "minValue")?,
        max_value_compat: parse_optional_i32_query(&query, "maxValue")?,
    })
}

fn parse_error_image_query(raw_query: Option<&str>) -> Result<ErrorImageQuery, Response> {
    let query = parse_raw_query(raw_query.unwrap_or_default());
    let scale = parse_optional_f64_query(&query, "scale")?;
    let _mask = parse_optional_bool_query(&query, "mask")?;
    Ok(ErrorImageQuery {
        scale,
        min_value: parse_optional_f64_query(&query, "minValue")?,
        max_value: parse_optional_f64_query(&query, "maxValue")?,
        force_cache: parse_optional_bool_query(&query, "force_cache")?,
    })
}

fn parse_coil_data_area_query(raw_query: Option<&str>) -> Result<CoilDataAreaQuery, Response> {
    let query = parse_raw_query(raw_query.unwrap_or_default());
    let scale = parse_optional_f64_query(&query, "scale")?;
    let mask = parse_optional_bool_query(&query, "mask")?;
    Ok(CoilDataAreaQuery {
        scale,
        mask,
        value_from: parse_optional_f64_query(&query, "valueFrom")?,
        value_to: parse_optional_f64_query(&query, "valueTo")?,
        r: parse_optional_u8_query(&query, "r")?,
        g: parse_optional_u8_query(&query, "g")?,
        b: parse_optional_u8_query(&query, "b")?,
    })
}

fn parse_python_int_converter_path(value: &str) -> Result<i64, Response> {
    if value.is_empty() || !value.chars().all(|character| character.is_ascii_digit()) {
        return Err(python_not_found_response());
    }
    Ok(value.parse::<i64>().unwrap_or(i64::MAX))
}

fn parse_defect_image_coord(value: &str, default_value: i32) -> Result<i32, ()> {
    let value = value.trim();
    if value.is_empty() || value.eq_ignore_ascii_case("nan") {
        return Ok(default_value);
    }
    value.parse::<i32>().map_err(|_| ())
}

fn clip_max_output_dir(raw_query: Option<&str>, surface_dir: &Path) -> PathBuf {
    query_param(raw_query, "save_url")
        .filter(|value| !value.trim().is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| surface_dir.to_path_buf())
        .join("clip_max")
}

fn query_param(raw_query: Option<&str>, field: &str) -> Option<String> {
    raw_query.unwrap_or_default().split('&').find_map(|part| {
        if part.is_empty() {
            return None;
        }
        let (key, value) = part.split_once('=').unwrap_or((part, ""));
        (key == field).then(|| percent_decode_query_value(value))
    })
}

fn percent_decode_query_value(value: &str) -> String {
    let bytes = value.as_bytes();
    let mut decoded = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'+' => {
                decoded.push(b' ');
                index += 1;
            }
            b'%' if index + 2 < bytes.len() => {
                if let (Some(high), Some(low)) =
                    (hex_value(bytes[index + 1]), hex_value(bytes[index + 2]))
                {
                    decoded.push((high << 4) | low);
                    index += 3;
                } else {
                    decoded.push(bytes[index]);
                    index += 1;
                }
            }
            byte => {
                decoded.push(byte);
                index += 1;
            }
        }
    }
    String::from_utf8_lossy(&decoded).into_owned()
}

fn hex_value(value: u8) -> Option<u8> {
    match value {
        b'0'..=b'9' => Some(value - b'0'),
        b'a'..=b'f' => Some(value - b'a' + 10),
        b'A'..=b'F' => Some(value - b'A' + 10),
        _ => None,
    }
}

fn parse_raw_query(raw_query: &str) -> HashMap<String, String> {
    raw_query
        .split('&')
        .filter(|part| !part.is_empty())
        .map(|part| {
            let (key, value) = part.split_once('=').unwrap_or((part, ""));
            (key.to_string(), value.to_string())
        })
        .collect()
}

fn parse_optional_i32_query(
    query: &HashMap<String, String>,
    field: &str,
) -> Result<Option<i32>, Response> {
    let Some(input) = query.get(field) else {
        return Ok(None);
    };
    input
        .parse::<i32>()
        .map(Some)
        .map_err(|_| fastapi_int_query_error(field, input))
}

fn parse_optional_i32_query_range(
    query: &HashMap<String, String>,
    field: &str,
    min: i32,
    max: i32,
) -> Result<Option<i32>, Response> {
    let Some(input) = query.get(field) else {
        return Ok(None);
    };
    let value = input
        .parse::<i32>()
        .map_err(|_| fastapi_int_query_error(field, input))?;
    validate_optional_i32_range(field, Some(value), min, max)?;
    Ok(Some(value))
}

fn parse_optional_f64_query(
    query: &HashMap<String, String>,
    field: &str,
) -> Result<Option<f64>, Response> {
    let Some(input) = query.get(field) else {
        return Ok(None);
    };
    input
        .parse::<f64>()
        .map(Some)
        .map_err(|_| fastapi_float_query_error(field, input))
}

fn parse_optional_bool_query(
    query: &HashMap<String, String>,
    field: &str,
) -> Result<Option<bool>, Response> {
    let Some(input) = query.get(field) else {
        return Ok(None);
    };
    match input.trim().to_ascii_lowercase().as_str() {
        "1" | "true" | "t" | "yes" | "y" | "on" => Ok(Some(true)),
        "0" | "false" | "f" | "no" | "n" | "off" => Ok(Some(false)),
        _ => Err(fastapi_bool_query_error(field, input)),
    }
}

fn parse_optional_u8_query(
    query: &HashMap<String, String>,
    field: &str,
) -> Result<Option<u8>, Response> {
    let Some(input) = query.get(field) else {
        return Ok(None);
    };
    input
        .parse::<u8>()
        .map(Some)
        .map_err(|_| fastapi_int_query_error(field, input))
}

fn validate_optional_i32_range(
    field: &str,
    value: Option<i32>,
    min: i32,
    max: i32,
) -> Result<(), Response> {
    let Some(value) = value else {
        return Ok(());
    };
    if value < min {
        return Err(fastapi_greater_than_equal_query_error(
            field,
            &value.to_string(),
            min,
        ));
    }
    if value > max {
        return Err(fastapi_less_than_equal_query_error(
            field,
            &value.to_string(),
            max,
        ));
    }
    Ok(())
}

fn fastapi_float_query_error(field: &str, input: &str) -> Response {
    fastapi_query_validation_response(format!(
        "{{\"detail\":[{{\"type\":\"float_parsing\",\"loc\":[\"query\",{}],\"msg\":\"Input should be a valid number, unable to parse string as a number\",\"input\":{}}}]}}",
        json_string(field),
        json_string(input),
    ))
}

fn fastapi_bool_query_error(field: &str, input: &str) -> Response {
    fastapi_query_validation_response(format!(
        "{{\"detail\":[{{\"type\":\"bool_parsing\",\"loc\":[\"query\",{}],\"msg\":\"Input should be a valid boolean, unable to interpret input\",\"input\":{}}}]}}",
        json_string(field),
        json_string(input),
    ))
}

fn fastapi_int_query_error(field: &str, input: &str) -> Response {
    fastapi_query_validation_response(format!(
        "{{\"detail\":[{{\"type\":\"int_parsing\",\"loc\":[\"query\",{}],\"msg\":\"Input should be a valid integer, unable to parse string as an integer\",\"input\":{}}}]}}",
        json_string(field),
        json_string(input),
    ))
}

fn fastapi_greater_than_equal_query_error(field: &str, input: &str, ge: i32) -> Response {
    fastapi_query_validation_response(format!(
        "{{\"detail\":[{{\"type\":\"greater_than_equal\",\"loc\":[\"query\",{}],\"msg\":\"Input should be greater than or equal to {ge}\",\"input\":{},\"ctx\":{{\"ge\":{ge}}}}}]}}",
        json_string(field),
        json_string(input),
    ))
}

fn fastapi_less_than_equal_query_error(field: &str, input: &str, le: i32) -> Response {
    fastapi_query_validation_response(format!(
        "{{\"detail\":[{{\"type\":\"less_than_equal\",\"loc\":[\"query\",{}],\"msg\":\"Input should be less than or equal to {le}\",\"input\":{},\"ctx\":{{\"le\":{le}}}}}]}}",
        json_string(field),
        json_string(input),
    ))
}

fn fastapi_query_validation_response(body: String) -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    (StatusCode::UNPROCESSABLE_ENTITY, headers, body).into_response()
}

fn json_string(value: &str) -> String {
    serde_json::to_string(value).expect("serialize query validation string")
}

pub async fn defect_image(
    State(state): State<Arc<AppState>>,
    AxumPath((surface_key, coil_id, type_, x, y, w, h)): AxumPath<(
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
        return missing_image_response();
    };
    let Ok(y) = parse_defect_image_coord(&y, 0) else {
        return missing_image_response();
    };
    let Ok(w) = parse_defect_image_coord(&w, 100) else {
        return missing_image_response();
    };
    let Ok(h) = parse_defect_image_coord(&h, 100) else {
        return missing_image_response();
    };

    if let Some(production_surface_dir) =
        state.production_surface_dir_for_coil(&surface_key, coil_id)
        && let Some(path) =
            matching_detection_defect_image_path(&production_surface_dir, coil_id, x, y, w, h)
    {
        return serve_file(&state, path);
    }

    let Some(surface_dir) = state.main_api_surface_dir_for_request(&surface_key, coil_id) else {
        return missing_image_response();
    };

    let Some(source) = load_named_rgb_image_from_surface_dir(&state, &surface_dir, &type_) else {
        return missing_image_response();
    };
    let crop = defect_image_crop(&source, x, y, w, h);
    match encode_jpeg(DynamicImage::ImageRgb8(crop), 85) {
        Some(bytes) => jpeg_bytes_response(bytes),
        None => missing_image_response(),
    }
}

pub async fn clip_max_image(
    State(state): State<Arc<AppState>>,
    AxumPath((coil_id, surface_key)): AxumPath<(String, String)>,
    RawQuery(raw_query): RawQuery,
) -> Response {
    let coil_id = match parse_python_int_converter_path(&coil_id) {
        Ok(coil_id) => coil_id,
        Err(response) => return response,
    };
    let coil_id_path = coil_id.to_string();
    let Some(surface_dir) = image_request_coil_dir(&state, &surface_key, &coil_id_path) else {
        return json_null_response();
    };
    let output_dir = clip_max_output_dir(raw_query.as_deref(), &surface_dir);
    if output_dir.exists() {
        return json_null_response();
    }
    if std::fs::create_dir_all(&output_dir).is_err() {
        return json_null_response();
    }

    let _ =
        clip_max_images_from_surface_dir(&state, &surface_dir, &output_dir, coil_id, &surface_key);
    json_null_response()
}

fn load_named_rgb_image_from_surface_dir(
    state: &AppState,
    surface_dir: &Path,
    name: &str,
) -> Option<RgbImage> {
    let name = name.trim();
    if name.is_empty() {
        return None;
    }
    find_named_image_file(&surface_dir.join("jpg"), name)
        .or_else(|| find_named_image_file(&surface_dir.join("png"), name))
        .or_else(|| find_named_image_file(&surface_dir.join("preview"), name))
        .and_then(|path| load_image(state, &path))
        .map(|image| image.to_rgb8())
}

fn find_named_image_file(dir: &Path, name: &str) -> Option<PathBuf> {
    for extension in ["jpg", "jpeg", "png", "bmp"] {
        let path = dir.join(format!("{name}.{extension}"));
        if path.exists() {
            return Some(path);
        }
    }
    None
}

fn area_image_source_response(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
) -> Option<Response> {
    area_image_file_response(state, surface_key, coil_id, "jpg", type_)
        .or_else(|| area_image_file_response(state, surface_key, coil_id, "png", type_))
}

fn area_image_file_response(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    folder: &str,
    type_: &str,
) -> Option<Response> {
    let dir = image_request_coil_dir(state, surface_key, coil_id)?.join(folder);
    let path = find_named_image_file(&dir, type_)?;
    get_file_bytes(state, &path).map(jpeg_cached_bytes_response)
}

fn cached_classifier_image_path(
    surface_dir: &Path,
    class_name: &str,
    coil_id: i64,
    x: i32,
    y: i32,
) -> Option<PathBuf> {
    let classifier_dir = surface_dir
        .join("classifier")
        .join(safe_folder_name(class_name));
    let prefix = format!("{coil_id}_{x}_{y}_");
    std::fs::read_dir(classifier_dir)
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

    let crop = image::imageops::crop_imm(
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
    image::imageops::replace(&mut padded, &crop, paste_x, paste_y);
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

fn clip_max_images_from_surface_dir(
    state: &AppState,
    surface_dir: &Path,
    output_dir: &Path,
    coil_id: i64,
    surface_key: &str,
) -> Result<usize, String> {
    let source = load_named_rgb_image_from_surface_dir(state, surface_dir, "GRAY")
        .ok_or_else(|| "source image not found".to_string())?;
    let mask = load_mask_image(surface_dir)
        .unwrap_or_else(|| GrayImage::from_pixel(source.width(), source.height(), Luma([255])));
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

            let crop = image::imageops::crop_imm(
                &source,
                clip_x as u32,
                clip_y as u32,
                actual_w as u32,
                actual_h as u32,
            )
            .to_image();
            let output_path = output_dir.join(format!(
                "{coil_id}_{surface_key}_{clip_x}_{clip_y}_{clip_w}_{clip_h}.png"
            ));
            DynamicImage::ImageRgb8(crop)
                .save_with_format(output_path, ImageFormat::Png)
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

fn resolve_preview_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
) -> Option<PathBuf> {
    let preview_dir = image_request_coil_dir(state, surface_key, coil_id)?.join("preview");
    if let Some(path) = find_standard_named_image_file(&preview_dir, type_) {
        return Some(path);
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
    None
}

fn resolve_source_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    mask: bool,
) -> Option<PathBuf> {
    let base = image_request_coil_dir(state, surface_key, coil_id)?;
    if mask {
        let mask_path = base.join("mask").join(format!("{type_}.png"));
        return mask_path.exists().then_some(mask_path);
    }
    find_standard_named_image_file(&base.join("jpg"), type_)
        .or_else(|| find_standard_named_image_file(&base.join("png"), type_))
}

fn find_standard_named_image_file(dir: &Path, name: &str) -> Option<PathBuf> {
    for extension in ["jpg", "jpeg", "png"] {
        let path = dir.join(format!("{name}.{extension}"));
        if path.exists() {
            return Some(path);
        }
    }
    None
}

fn image_request_coil_dir(state: &AppState, surface_key: &str, coil_id: &str) -> Option<PathBuf> {
    state
        .testdata_surface_dir_for_string_request(surface_key)
        .or_else(|| {
            state
                .surface(surface_key)
                .map(|surface| surface.save_folder.join(coil_id))
        })
}

#[cfg(test)]
fn resolve_render_cache_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    query: &RenderQuery,
) -> Option<PathBuf> {
    if !query.thumbnail() {
        return None;
    }
    let colormap_dir = query.colormap().to_ascii_lowercase();
    let path = image_request_coil_dir(state, surface_key, coil_id)?
        .join("cache")
        .join("falsecolor")
        .join(colormap_dir)
        .join("thumbnail_1024.jpg");
    path.exists().then_some(path)
}

fn render_image_from_surface_dir(
    state: &AppState,
    surface_dir: &Path,
    query: &RenderQuery,
) -> Option<Response> {
    let colormap = query.colormap();
    if !query.thumbnail() {
        return render_dynamic_response(surface_dir, query);
    }

    if let Some(path) = falsecolor_thumbnail_path(surface_dir, colormap) {
        return Some(render_file_response(state, path, query, true));
    }

    if query.grayscale() && query.mask() {
        return render_dynamic_response(surface_dir, &query.with_thumbnail(false));
    }

    let bytes = render_dynamic_image_from_surface_dir(surface_dir, query)?;
    write_falsecolor_thumbnail_cache(surface_dir, colormap, &bytes);
    let mut response = jpeg_bytes_response(bytes);
    set_render_headers(&mut response, query, false);
    Some(response)
}

fn falsecolor_thumbnail_path(surface_dir: &Path, colormap: &str) -> Option<PathBuf> {
    let path = falsecolor_thumbnail_cache_path(surface_dir, colormap)?;
    path.exists().then_some(path)
}

fn falsecolor_thumbnail_cache_path(surface_dir: &Path, colormap: &str) -> Option<PathBuf> {
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

fn write_falsecolor_thumbnail_cache(surface_dir: &Path, colormap: &str, bytes: &[u8]) {
    let Some(path) = falsecolor_thumbnail_cache_path(surface_dir, colormap) else {
        return;
    };
    let Some(parent) = path.parent() else {
        return;
    };
    if std::fs::create_dir_all(parent).is_ok() {
        let _ = std::fs::write(path, bytes);
    }
}

fn render_dynamic_response(surface_dir: &Path, query: &RenderQuery) -> Option<Response> {
    let bytes = render_dynamic_image_from_surface_dir(surface_dir, query)?;
    let mut response = jpeg_bytes_response(bytes);
    set_render_headers(&mut response, query, false);
    Some(response)
}

fn render_dynamic_image_from_surface_dir(
    surface_dir: &Path,
    query: &RenderQuery,
) -> Option<Vec<u8>> {
    let depth_map = load_depth_map_from_dir(surface_dir)?;
    let mask = if query.mask() {
        load_mask_image(surface_dir)
    } else {
        None
    };
    generate_render_jpeg(&depth_map, mask.as_ref(), query)
}

fn load_mask_image(surface_dir: &Path) -> Option<GrayImage> {
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

    encode_jpeg(DynamicImage::ImageRgb8(image), 90)
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

fn generate_area_png(depth_map: &DepthMap, query: &CoilDataAreaQuery) -> Option<Vec<u8>> {
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

    encode_png(DynamicImage::ImageRgba8(image))
}

fn generate_error_png(depth_map: &DepthMap, query: &ErrorImageQuery) -> Option<Vec<u8>> {
    let source_width = depth_map.width();
    let source_height = depth_map.height();
    if source_width <= 0 || source_height <= 0 {
        return None;
    }

    let median_z = median_depth_above(depth_map, 1000.0)?;
    let threshold_down_units =
        abs_finite_f64(query.min_value.unwrap_or(0.0)) / DEFAULT_SCAN3D_SCALE_Z;
    let threshold_up_units =
        abs_finite_f64(query.max_value.unwrap_or(255.0)) / DEFAULT_SCAN3D_SCALE_Z;
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
                depth_map.value_f64(source_x, source_y).unwrap_or(0.0)
            };
            if value > 1000.0 && value < min_value {
                image.put_pixel(x, y, Rgba([0, 0, 255, 255]));
            } else if value > max_value {
                image.put_pixel(x, y, Rgba([255, 0, 0, 255]));
            }
        }
    }

    encode_png(DynamicImage::ImageRgba8(image))
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

fn resolve_error_cache_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    query: &ErrorImageQuery,
) -> Option<PathBuf> {
    let threshold_down = query.min_value.map(abs_finite_f64).unwrap_or(0.0);
    let threshold_up = query.max_value.map(abs_finite_f64).unwrap_or(255.0);
    let path = image_request_coil_dir(state, surface_key, coil_id)?
        .join("png")
        .join("Error.png");
    (path.exists() && error_cache_matches(&path, threshold_down, threshold_up)).then_some(path)
}

fn error_cache_matches(error_cache_path: &Path, threshold_down: f64, threshold_up: f64) -> bool {
    let Ok(content) = std::fs::read_to_string(error_cache_path.with_extension("json")) else {
        return false;
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) else {
        return false;
    };
    let Some(cached_down) = value
        .get("threshold_down")
        .and_then(serde_json::Value::as_f64)
    else {
        return false;
    };
    let Some(cached_up) = value
        .get("threshold_up")
        .and_then(serde_json::Value::as_f64)
    else {
        return false;
    };
    (abs_finite_f64(cached_down) - threshold_down).abs() <= f64::EPSILON
        && (abs_finite_f64(cached_up) - threshold_up).abs() <= f64::EPSILON
}

fn abs_finite_f64(value: f64) -> f64 {
    if value.is_finite() { value.abs() } else { 0.0 }
}

fn resolve_area_meta(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
) -> Option<ImageMeta> {
    if let Some(tile_path) =
        resolve_area_l4_tile_path_for_metadata(state, surface_key, coil_id, type_, 0, 0)
    {
        let (tile_width, tile_height) = image_dimensions(state, &tile_path)?;
        if tile_width > 0 && tile_height > 0 {
            return Some(ImageMeta {
                width: tile_width * 3,
                height: tile_height * 3,
            });
        }
    }
    let source_path = resolve_source_path(state, surface_key, coil_id, type_, false)?;
    let (width, height) = image_dimensions(state, &source_path)?;
    Some(ImageMeta { width, height })
}

fn area_tile_cache_base_dir(coil_dir: &Path, _type_: &str) -> PathBuf {
    coil_dir.join("cache").join("area").join("tild")
}

fn area_tile_cache_is_fresh(tile_path: &Path, source_path: Option<&Path>) -> bool {
    let Ok(tile_metadata) = std::fs::metadata(tile_path) else {
        return false;
    };
    let Some(source_path) = source_path else {
        return true;
    };
    let Ok(source_metadata) = std::fs::metadata(source_path) else {
        return true;
    };
    let Ok(tile_modified) = tile_metadata.modified() else {
        return true;
    };
    let Ok(source_modified) = source_metadata.modified() else {
        return true;
    };
    tile_modified >= source_modified
}

fn resolve_area_tile_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    row: i32,
    col: i32,
    level: i32,
) -> Option<PathBuf> {
    if !(0..=2).contains(&row) || !(0..=2).contains(&col) {
        return None;
    }
    let (source_path, coil_dir) =
        resolve_area_source_path_and_coil_dir(state, surface_key, coil_id, type_)?;
    let tile_path = area_tile_cache_base_dir(&coil_dir, type_)
        .join(format!("L{level}"))
        .join(format!("{col}_{row}.jpg"));
    (area_tile_cache_is_fresh(&tile_path, source_path.as_deref())).then_some(tile_path)
}

fn resolve_area_l4_tile_path(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    row: i32,
    col: i32,
) -> Option<PathBuf> {
    resolve_area_tile_path(state, surface_key, coil_id, type_, row, col, 4)
}

fn resolve_area_l4_tile_path_for_metadata(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    row: i32,
    col: i32,
) -> Option<PathBuf> {
    if !(0..=2).contains(&row) || !(0..=2).contains(&col) {
        return None;
    }
    let (source_path, coil_dir) =
        resolve_area_source_path_and_coil_dir(state, surface_key, coil_id, type_)?;
    let tile_path = area_tile_cache_base_dir(&coil_dir, type_)
        .join("L4")
        .join(format!("{col}_{row}.jpg"));
    (area_tile_cache_is_fresh(&tile_path, source_path.as_deref())).then_some(tile_path)
}

fn resolve_area_source_path_and_coil_dir(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
) -> Option<(Option<PathBuf>, PathBuf)> {
    let source_path = resolve_source_path(state, surface_key, coil_id, type_, false);
    let coil_dir = source_path
        .as_deref()
        .and_then(|path| path.parent().and_then(Path::parent).map(Path::to_path_buf))
        .or_else(|| image_request_coil_dir(state, surface_key, coil_id))?;
    Some((source_path, coil_dir))
}

fn generate_area_tile_response(
    state: &AppState,
    surface_key: &str,
    coil_id: &str,
    type_: &str,
    row: i32,
    col: i32,
    tile_count: i32,
    level: i32,
) -> Option<Response> {
    if !(0..=2).contains(&row) || !(0..=2).contains(&col) {
        return None;
    }

    let source_path = resolve_source_path(state, surface_key, coil_id, type_, false);
    let cache_key = source_path
        .as_deref()
        .map(|path| area_tile_memory_cache_key(path, level, row, col));
    if let Some(cache_key) = cache_key.as_deref() {
        if let Some(bytes) = get_cached_tile_bytes(state, cache_key) {
            let mut response = jpeg_cached_bytes_response(bytes);
            set_tile_headers(&mut response, level, "memory");
            return Some(response);
        }
    }

    if let Some(l4_path) = resolve_area_l4_tile_path(state, surface_key, coil_id, type_, row, col) {
        let tile = load_image(state, &l4_path)?;
        let bytes = encode_area_tile_for_level(tile, level)?;
        let mut response = jpeg_bytes_response(bytes);
        set_tile_headers(&mut response, level, "miss");
        return Some(response);
    }

    let source_path = source_path?;
    let cache_key = area_tile_memory_cache_key(&source_path, level, row, col);
    let image = load_area_gray_image(state, &source_path)?;
    let tile = crop_area_tile_gray(image.as_ref(), row, col, tile_count)?;
    let bytes = encode_area_gray_tile_for_level(tile, level)?;
    if let Some(coil_dir) = source_path.parent().and_then(Path::parent) {
        write_area_l4_tile_cache_from_source(coil_dir, type_, image.as_ref(), tile_count);
        let _ = write_area_tile_cache_bytes(coil_dir, type_, row, col, level, &bytes);
    }
    let mut response = jpeg_bytes_response(store_tile_bytes(state, cache_key, bytes));
    set_tile_headers(&mut response, level, "fallback");
    Some(response)
}

fn area_tile_memory_cache_key(source_path: &Path, level: i32, row: i32, col: i32) -> String {
    format!("{}|{}|{}|{}", file_cache_key(source_path), level, row, col)
}

fn crop_area_tile_gray(
    image: &GrayImage,
    row: i32,
    col: i32,
    tile_count: i32,
) -> Option<GrayImage> {
    let (width, height) = image.dimensions();
    let tile_w = width / tile_count as u32;
    let tile_h = height / tile_count as u32;
    if tile_w == 0 || tile_h == 0 {
        return None;
    }
    // Match the Python main-service fallback quirk: row selects the x-axis
    // tile and col selects the y-axis tile when no disk cache is available.
    let x = row as u32 * tile_w;
    let y = col as u32 * tile_h;
    Some(image::imageops::crop_imm(image, x, y, tile_w, tile_h).to_image())
}

fn write_area_l4_tile_cache_from_source(
    coil_dir: &Path,
    type_: &str,
    image: &GrayImage,
    tile_count: i32,
) {
    if tile_count <= 1 {
        return;
    }

    for row in 0..tile_count {
        for col in 0..tile_count {
            let Some(tile) = crop_area_tile_gray(image, row, col, tile_count) else {
                continue;
            };
            let Some(bytes) = encode_area_gray_tile_for_level(tile, 4) else {
                continue;
            };
            let _ = write_area_tile_cache_bytes(coil_dir, type_, row, col, 4, &bytes);
        }
    }
}

fn write_area_tile_cache_bytes(
    coil_dir: &Path,
    type_: &str,
    row: i32,
    col: i32,
    level: i32,
    bytes: &[u8],
) -> std::io::Result<()> {
    let path = area_tile_cache_base_dir(coil_dir, type_)
        .join(format!("L{level}"))
        .join(format!("{col}_{row}.jpg"));
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, bytes)
}

fn encode_area_tile_for_level(tile: DynamicImage, level: i32) -> Option<Vec<u8>> {
    encode_area_gray_tile_for_level(tile.to_luma8(), level)
}

fn encode_area_gray_tile_for_level(tile: GrayImage, level: i32) -> Option<Vec<u8>> {
    let (target_size, quality) = tile_level_config(level);
    let resized = if level < 4 {
        resize_gray_tile_if_needed(tile, target_size)
    } else {
        tile
    };
    encode_luma_jpeg(&resized, quality)
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

fn resize_gray_tile_if_needed(tile: GrayImage, target_size: u32) -> GrayImage {
    let (width, height) = tile.dimensions();
    let max_side = width.max(height);
    if max_side <= target_size {
        return tile;
    }
    let scale = target_size as f32 / max_side as f32;
    let new_width = ((width as f32) * scale).max(1.0) as u32;
    let new_height = ((height as f32) * scale).max(1.0) as u32;
    DynamicImage::ImageLuma8(tile)
        .resize(new_width, new_height, FilterType::Lanczos3)
        .to_luma8()
}

fn load_image(state: &AppState, path: &Path) -> Option<DynamicImage> {
    let bytes = get_file_bytes(state, path)?;
    let mut reader = ImageReader::new(Cursor::new(bytes.as_ref()))
        .with_guessed_format()
        .ok()?;
    reader.no_limits();
    reader.decode().ok()
}

fn load_area_gray_image(state: &AppState, path: &Path) -> Option<Arc<GrayImage>> {
    let key = file_cache_key(path);
    if let Ok(mut cache) = state.area_gray_cache.lock() {
        if let Some(image) = cache.get(&key) {
            return Some(image.clone());
        }
    }

    let bytes = get_file_bytes(state, path)?;
    let mut reader = ImageReader::new(Cursor::new(bytes.as_ref()))
        .with_guessed_format()
        .ok()?;
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

fn encode_luma_jpeg(image: &GrayImage, quality: u8) -> Option<Vec<u8>> {
    let mut bytes = Vec::new();
    let mut encoder = JpegEncoder::new_with_quality(&mut bytes, quality);
    encoder
        .encode(
            image.as_raw(),
            image.width(),
            image.height(),
            image::ExtendedColorType::L8,
        )
        .ok()?;
    Some(bytes)
}

fn encode_png(image: DynamicImage) -> Option<Vec<u8>> {
    let mut bytes = Cursor::new(Vec::new());
    image.write_to(&mut bytes, ImageFormat::Png).ok()?;
    Some(bytes.into_inner())
}

fn image_dimensions(state: &AppState, path: &Path) -> Option<(u32, u32)> {
    let bytes = get_file_bytes(state, path)?;
    let reader = ImageReader::new(Cursor::new(bytes.as_ref()))
        .with_guessed_format()
        .ok()?;
    reader.into_dimensions().ok()
}

fn matching_detection_defect_image_path(
    surface_dir: &Path,
    coil_id: i64,
    x: i32,
    y: i32,
    w: i32,
    h: i32,
) -> Option<PathBuf> {
    let detection_dir = surface_dir
        .parent()
        .and_then(Path::parent)?
        .join(coil_id.to_string())
        .join("detection");
    if !detection_dir.exists() {
        return None;
    }

    let center_x = x + w / 2;
    let center_y = y + h / 2;
    for defect_dir in std::fs::read_dir(detection_dir).ok()? {
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
            if annotation.objects.into_iter().any(|object| {
                let Some(bbox) = object.bndbox else {
                    return false;
                };
                bbox.xmin <= center_x
                    && center_x <= bbox.xmax
                    && bbox.ymin <= center_y
                    && center_y <= bbox.ymax
            }) {
                return Some(image_path);
            }
        }
    }
    None
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

fn render_file_response(
    state: &AppState,
    path: PathBuf,
    query: &RenderQuery,
    from_cache: bool,
) -> Response {
    let mut response = serve_file(state, path);
    set_render_headers(&mut response, query, from_cache);
    response
}

fn render_placeholder_response(query: &RenderQuery) -> Response {
    let mut response = missing_image_response();
    set_render_headers(&mut response, query, false);
    response
}

fn set_render_headers(response: &mut Response, query: &RenderQuery, from_cache: bool) {
    response.headers_mut().insert(
        HeaderName::from_static("x-thumbnail"),
        HeaderValue::from_str(&query.thumbnail().to_string())
            .unwrap_or(HeaderValue::from_static("false")),
    );
    response.headers_mut().insert(
        HeaderName::from_static("x-colormap"),
        HeaderValue::from_static(query.colormap()),
    );
    response.headers_mut().insert(
        HeaderName::from_static("x-from-cache"),
        HeaderValue::from_str(&from_cache.to_string()).unwrap_or(HeaderValue::from_static("false")),
    );
}

fn jpeg_bytes_response(bytes: Vec<u8>) -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(header::CONTENT_TYPE, HeaderValue::from_static("image/jpeg"));
    (StatusCode::OK, headers, bytes).into_response()
}

fn png_bytes_response(bytes: Vec<u8>) -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(header::CONTENT_TYPE, HeaderValue::from_static("image/png"));
    (StatusCode::OK, headers, bytes).into_response()
}

fn transparent_png_response(width: u32, height: u32) -> Response {
    let image = RgbaImage::from_pixel(width.max(1), height.max(1), Rgba([0, 0, 0, 0]));
    match encode_png(DynamicImage::ImageRgba8(image)) {
        Some(bytes) => png_bytes_response(bytes),
        None => StatusCode::NO_CONTENT.into_response(),
    }
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

fn missing_image_response() -> Response {
    jpeg_bytes_response(PLACEHOLDER_JPEG.to_vec())
}

fn json_null_response() -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    (StatusCode::OK, headers, "null").into_response()
}

fn python_not_found_response() -> Response {
    let mut headers = HeaderMap::new();
    headers.insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/json"),
    );
    (StatusCode::NOT_FOUND, headers, "{\"detail\":\"Not Found\"}").into_response()
}

fn not_found(message: &'static str) -> Response {
    (StatusCode::NOT_FOUND, message).into_response()
}

fn python_internal_server_error_response() -> Response {
    (StatusCode::INTERNAL_SERVER_ERROR, "Internal Server Error").into_response()
}

fn get_file_bytes(state: &AppState, path: &Path) -> Option<Bytes> {
    let key = file_cache_key(path);
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

fn file_cache_key(path: &Path) -> String {
    let mut key = path.to_string_lossy().to_string();
    let Ok(metadata) = std::fs::metadata(path) else {
        return key;
    };

    key.push_str("|len=");
    key.push_str(&metadata.len().to_string());
    if let Ok(modified) = metadata.modified()
        && let Ok(duration) = modified.duration_since(std::time::UNIX_EPOCH)
    {
        key.push_str("|mtime=");
        key.push_str(&duration.as_nanos().to_string());
    }
    key
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app_config::{RuntimeConfig, SurfaceConfig};
    use image::GenericImageView;
    use image::Luma;
    use ndarray::arr2;
    use ndarray_npy::write_npy;
    use std::fs;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{Duration, SystemTime, UNIX_EPOCH};
    use tower::ServiceExt;

    static TEMP_DIR_COUNTER: AtomicU64 = AtomicU64::new(0);

    fn unique_temp_dir() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time")
            .as_nanos();
        let counter = TEMP_DIR_COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!("lg3d_rust_image_service_test_{suffix}_{counter}"))
    }

    fn write_jpeg(path: &Path, width: u32, height: u32, color: Rgb<u8>) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create jpeg parent");
        }
        let image = RgbImage::from_pixel(width, height, color);
        let bytes = encode_jpeg(DynamicImage::ImageRgb8(image), 90).expect("encode jpeg");
        fs::write(path, bytes).expect("write jpeg");
    }

    fn write_pattern_jpeg(path: &Path, width: u32, height: u32) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create pattern jpeg parent");
        }
        let mut image = RgbImage::new(width, height);
        for y in 0..height {
            for x in 0..width {
                image.put_pixel(x, y, Rgb([(x * 40) as u8, (y * 50) as u8, 120]));
            }
        }
        let bytes = encode_jpeg(DynamicImage::ImageRgb8(image), 90).expect("encode pattern jpeg");
        fs::write(path, bytes).expect("write pattern jpeg");
    }

    fn encode_query_path(path: &Path) -> String {
        path.to_string_lossy()
            .replace('%', "%25")
            .replace('\\', "%5C")
            .replace(':', "%3A")
            .replace(' ', "%20")
    }

    fn write_testdata_config(config_path: &Path, save_s: &Path, testdata_dir: &Path) {
        let value = serde_json::json!({
            "testMode": true,
            "testDataCoilId": 193113,
            "testDataDir": testdata_dir,
            "surface": [
                {
                    "key": "S",
                    "saveFolder": save_s,
                },
            ],
        });
        fs::write(config_path, value.to_string()).expect("write image service config");
    }

    fn write_png(path: &Path, width: u32, height: u32, color: Rgb<u8>) {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create png parent");
        }
        let image = RgbImage::from_pixel(width, height, color);
        DynamicImage::ImageRgb8(image)
            .save_with_format(path, image::ImageFormat::Png)
            .expect("write png");
    }

    fn encode_luma_jpeg_like_main_api(image: &GrayImage, quality: u8) -> Vec<u8> {
        let mut bytes = Vec::new();
        let mut encoder = JpegEncoder::new_with_quality(&mut bytes, quality);
        encoder
            .encode(
                image.as_raw(),
                image.width(),
                image.height(),
                image::ExtendedColorType::L8,
            )
            .expect("encode luma jpeg");
        bytes
    }

    #[test]
    fn preview_resolution_uses_testdata_when_test_mode_enabled_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let preview_path = testdata_dir.join("preview").join("AREA.jpg");
        let config_path = temp_dir.join("Server3D.json");
        write_jpeg(&preview_path, 4, 3, Rgb([10, 20, 30]));
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        write_testdata_config(&config_path, &save_s, &testdata_dir);

        let config = RuntimeConfig::load(&config_path).expect("load config");
        let state = AppState::new(config);
        let resolved = resolve_preview_path(&state, "S", "193113", "AREA");

        assert_eq!(resolved.as_deref(), Some(preview_path.as_path()));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn area_tile_resolution_uses_testdata_cache_when_test_mode_enabled_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let area_path = testdata_dir.join("jpg").join("AREA.jpg");
        let tile_path = testdata_dir
            .join("cache")
            .join("area")
            .join("tild")
            .join("L4")
            .join("2_1.jpg");
        let config_path = temp_dir.join("Server3D.json");
        write_jpeg(&area_path, 90, 60, Rgb([20, 30, 40]));
        write_jpeg(&tile_path, 30, 20, Rgb([50, 60, 70]));
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        write_testdata_config(&config_path, &save_s, &testdata_dir);

        let config = RuntimeConfig::load(&config_path).expect("load config");
        let state = AppState::new(config);
        let resolved = resolve_area_tile_path(&state, "S", "193113", "AREA", 1, 2, 4);

        assert_eq!(resolved.as_deref(), Some(tile_path.as_path()));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_rejects_count_above_python_limit_with_fastapi_validation() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let area_path = save_s.join("193113").join("jpg").join("AREA.jpg");
        write_jpeg(&area_path, 90, 60, Rgb([20, 30, 40]));
        let state = AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        });

        let response = area_image_response(
            &state,
            "S",
            "193113",
            "AREA",
            AreaQuery {
                row: Some(0),
                col: Some(2),
                count: Some(4),
                level: Some(4),
            },
        );

        assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let text = String::from_utf8(body.to_vec()).expect("json body");
        assert_eq!(
            text,
            r#"{"detail":[{"type":"less_than_equal","loc":["query","count"],"msg":"Input should be less than or equal to 3","input":"4","ctx":{"le":3}}]}"#
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_rejects_level_above_python_limit_with_fastapi_validation() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let area_path = save_s.join("193113").join("jpg").join("AREA.jpg");
        write_jpeg(&area_path, 90, 60, Rgb([20, 30, 40]));
        let state = AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        });

        let response = area_image_response(
            &state,
            "S",
            "193113",
            "AREA",
            AreaQuery {
                row: Some(0),
                col: Some(2),
                count: Some(3),
                level: Some(5),
            },
        );

        assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let text = String::from_utf8(body.to_vec()).expect("json body");
        assert_eq!(
            text,
            r#"{"detail":[{"type":"less_than_equal","loc":["query","level"],"msg":"Input should be less than or equal to 4","input":"5","ctx":{"le":4}}]}"#
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_rejects_non_integer_row_with_fastapi_validation() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/193113?row=abc&col=2&count=3&level=4")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let text = String::from_utf8(body.to_vec()).expect("json body");
        assert_eq!(
            text,
            r#"{"detail":[{"type":"int_parsing","loc":["query","row"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"abc"}]}"#
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_full_image_reads_png_source_with_python_content_type() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let area_path = save_s.join("42").join("png").join("AREA.png");
        write_png(&area_path, 9, 7, Rgb([40, 50, 60]));
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}/{type_}",
                axum::routing::get(area_image_typed),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/42/AREA?row=-1&count=3")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("area full image");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (9, 7));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_missing_metadata_returns_placeholder_jpeg_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        fs::create_dir_all(save_s.join("511")).expect("empty coil dir");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/511?count=0")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert!(body.starts_with(&[0xff, 0xd8]));
        assert!(body.ends_with(&[0xff, 0xd9]));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_missing_typed_source_returns_main_api_placeholder_bytes() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        fs::create_dir_all(save_s.join("517")).expect("empty coil dir");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}/{type_}",
                axum::routing::get(area_image_typed),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/517/AREA_MASK?row=0&col=0&count=1&level=4")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(
            body.as_ref(),
            &[0xff, 0xd8, 0xff, 0xdb, 0x00, 0x43, 0x00, 0xff, 0xd9]
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_metadata_uses_l4_tile_cache_when_source_is_missing_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("506");
        write_jpeg(
            &coil_dir
                .join("cache")
                .join("area")
                .join("tild")
                .join("L4")
                .join("0_0.jpg"),
            21,
            19,
            Rgb([40, 50, 60]),
        );
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/506?count=0")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let meta: serde_json::Value = serde_json::from_slice(&body).expect("area metadata json");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            headers.get(header::CONTENT_TYPE).unwrap(),
            "application/json"
        );
        assert_eq!(meta["width"], 63);
        assert_eq!(meta["height"], 57);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_serves_tile_cache_when_source_is_missing_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("513");
        write_jpeg(
            &coil_dir
                .join("cache")
                .join("area")
                .join("tild")
                .join("L2")
                .join("2_1.jpg"),
            17,
            13,
            Rgb([50, 60, 70]),
        );
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/513?row=1&col=2&count=3&level=2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("source-missing cached area tile image");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-tile-level").unwrap(), "2");
        assert_eq!(headers.get("x-cache").unwrap(), "hit");
        assert_eq!(image.dimensions(), (17, 13));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_resizes_l4_cache_when_requested_level_is_missing_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("514");
        let l4_dir = coil_dir.join("cache").join("area").join("tild").join("L4");
        for row in 0..3 {
            for col in 0..3 {
                write_jpeg(
                    &l4_dir.join(format!("{col}_{row}.jpg")),
                    2000,
                    1500,
                    Rgb([50, 60, 70]),
                );
            }
        }
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/514?row=1&col=2&count=3&level=2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("resized l4 cached area tile");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-tile-level").unwrap(), "2");
        assert_eq!(headers.get("x-cache").unwrap(), "miss");
        assert_eq!(image.dimensions(), (1364, 1023));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_keeps_l4_derived_lower_level_cache_header_as_miss_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("519");
        write_jpeg(
            &coil_dir.join("jpg").join("AREA.jpg"),
            4500,
            3000,
            Rgb([10, 20, 30]),
        );
        let l4_dir = coil_dir.join("cache").join("area").join("tild").join("L4");
        for row in 0..3 {
            for col in 0..3 {
                write_jpeg(
                    &l4_dir.join(format!("{col}_{row}.jpg")),
                    1500,
                    1000,
                    Rgb([20 + row as u8, 30 + col as u8, 40]),
                );
            }
        }
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);
        let uri = "/image/area/S/519?row=0&col=0&count=3&level=2";

        let first_response = app
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("first response");
        let first_headers = first_response.headers().clone();
        let first_body = axum::body::to_bytes(first_response.into_body(), usize::MAX)
            .await
            .expect("first body");
        assert_eq!(first_headers.get("x-cache").unwrap(), "miss");

        let second_response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("second response");
        let second_status = second_response.status();
        let second_headers = second_response.headers().clone();
        let second_body = axum::body::to_bytes(second_response.into_body(), usize::MAX)
            .await
            .expect("second body");

        assert_eq!(second_status, StatusCode::OK);
        assert_eq!(second_headers.get("x-cache").unwrap(), "miss");
        assert_eq!(second_body.as_ref(), first_body.as_ref());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_resizes_l4_cache_with_lanczos_luma_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("518");
        let l4_path = coil_dir
            .join("cache")
            .join("area")
            .join("tild")
            .join("L4")
            .join("0_0.jpg");
        fs::create_dir_all(l4_path.parent().expect("l4 parent")).expect("l4 parent dir");
        let mut source = GrayImage::new(1500, 1000);
        for y in 0..1000 {
            for x in 0..1500 {
                source.put_pixel(x, y, Luma([((x * 7 + y * 11) % 251) as u8]));
            }
        }
        source
            .save_with_format(&l4_path, ImageFormat::Jpeg)
            .expect("write l4 tile");
        let decoded = image::open(&l4_path).expect("decode l4 tile").to_luma8();
        let scale = 1364.0_f32 / decoded.width().max(decoded.height()) as f32;
        let width = ((decoded.width() as f32) * scale).max(1.0) as u32;
        let height = ((decoded.height() as f32) * scale).max(1.0) as u32;
        let expected_image = DynamicImage::ImageLuma8(decoded)
            .resize(width, height, FilterType::Lanczos3)
            .to_luma8();
        let expected_bytes = encode_luma_jpeg_like_main_api(&expected_image, 80);
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/518?row=0&col=0&count=3&level=2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-tile-level").unwrap(), "2");
        assert_eq!(headers.get("x-cache").unwrap(), "miss");
        assert_eq!(body.as_ref(), expected_bytes.as_slice());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_typed_route_uses_shared_python_tile_cache_for_area_mask_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("516");
        write_jpeg(
            &coil_dir.join("png").join("AREA_MASK.png"),
            90,
            60,
            Rgb([20, 30, 40]),
        );
        write_jpeg(
            &coil_dir
                .join("cache")
                .join("area")
                .join("tild")
                .join("L2")
                .join("2_1.jpg"),
            17,
            13,
            Rgb([50, 60, 70]),
        );
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}/{type_}",
                axum::routing::get(area_image_typed),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/516/AREA_MASK?row=1&col=2&count=3&level=2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("AREA_MASK cached tile image");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-tile-level").unwrap(), "2");
        assert_eq!(headers.get("x-cache").unwrap(), "hit");
        assert_eq!(image.dimensions(), (17, 13));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_ignores_stale_tile_cache_after_source_update() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("511");
        let cache_path = coil_dir
            .join("cache")
            .join("area")
            .join("tild")
            .join("L4")
            .join("2_1.jpg");
        fs::create_dir_all(cache_path.parent().expect("stale AREA cache parent"))
            .expect("stale AREA cache dir");
        GrayImage::from_pixel(30, 20, Luma([9]))
            .save_with_format(&cache_path, ImageFormat::Jpeg)
            .expect("write stale AREA tile cache");

        std::thread::sleep(Duration::from_millis(1100));

        fs::create_dir_all(coil_dir.join("png")).expect("runtime area png dir");
        let mut source = GrayImage::new(90, 60);
        for y in 0..60 {
            for x in 0..90 {
                let tile_x = x / 30;
                let tile_y = y / 20;
                source.put_pixel(x, y, Luma([(tile_y * 80 + tile_x * 20) as u8]));
            }
        }
        source
            .save_with_format(coil_dir.join("png").join("AREA.png"), ImageFormat::Png)
            .expect("write updated runtime area png");

        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/511?row=1&col=2&count=3&level=4")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("fresh area tile image")
            .to_luma8();

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-cache").unwrap(), "fallback");
        assert_eq!(image.dimensions(), (30, 20));

        let first_pixel = image.get_pixel(0, 0)[0];
        assert!(
            first_pixel.abs_diff(180) <= 2,
            "stale cache should be ignored after the AREA source image changes, got {first_pixel}"
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_fallback_prefetches_full_l4_tile_cache_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("515");
        let source_path = coil_dir.join("jpg").join("AREA.jpg");
        fs::create_dir_all(source_path.parent().expect("area source parent"))
            .expect("runtime area source dir");
        let mut source = GrayImage::new(90, 60);
        for y in 0..60 {
            for x in 0..90 {
                let tile_x = x / 30;
                let tile_y = y / 20;
                source.put_pixel(x, y, Luma([(tile_y * 80 + tile_x * 20) as u8]));
            }
        }
        source
            .save_with_format(&source_path, ImageFormat::Jpeg)
            .expect("write runtime area source");

        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);

        let first_response = app
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/515?row=1&col=2&count=3&level=4")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let first_headers = first_response.headers().clone();
        assert_eq!(first_response.status(), StatusCode::OK);
        assert_eq!(first_headers.get("x-cache").unwrap(), "fallback");

        for row in 0..3 {
            for col in 0..3 {
                let cache_path = coil_dir
                    .join("cache")
                    .join("area")
                    .join("tild")
                    .join("L4")
                    .join(format!("{col}_{row}.jpg"));
                assert!(
                    cache_path.exists(),
                    "fallback AREA tile generation should prefetch the full L4 cache, missing {cache_path:?}"
                );
            }
        }

        let lower_response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/area/S/515?row=0&col=0&count=3&level=2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let lower_headers = lower_response.headers().clone();
        let lower_body = axum::body::to_bytes(lower_response.into_body(), usize::MAX)
            .await
            .expect("body");
        let lower_image = image::load_from_memory(&lower_body).expect("L4-backed lower tile");

        assert_eq!(lower_headers.get("x-tile-level").unwrap(), "2");
        assert_eq!(lower_headers.get("x-cache").unwrap(), "miss");
        assert_eq!(lower_image.dimensions(), (30, 20));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn area_image_route_reuses_fallback_generated_tile_cache_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("508");
        let source_path = coil_dir.join("jpg").join("AREA.jpg");
        fs::create_dir_all(source_path.parent().expect("area source parent"))
            .expect("runtime area source dir");
        GrayImage::from_pixel(90, 60, Luma([120]))
            .save_with_format(&source_path, ImageFormat::Jpeg)
            .expect("write runtime area source");

        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/area/{surface_key}/{coil_id}",
                axum::routing::get(area_image_compat),
            )
            .with_state(state);
        let uri = "/image/area/S/508?row=1&col=2&count=3&level=2";
        let cache_path = coil_dir
            .join("cache")
            .join("area")
            .join("tild")
            .join("L2")
            .join("2_1.jpg");

        let first_response = app
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let first_headers = first_response.headers().clone();
        assert_eq!(first_response.status(), StatusCode::OK);
        assert_eq!(first_headers.get("x-cache").unwrap(), "fallback");
        assert!(
            cache_path.exists(),
            "fallback tile generation should populate the Python-compatible AREA tile cache"
        );

        let second_response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let second_headers = second_response.headers().clone();
        assert_eq!(second_response.status(), StatusCode::OK);
        assert_eq!(second_headers.get("x-cache").unwrap(), "hit");

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn source_image_route_reads_png_source_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let source_path = save_s.join("42").join("png").join("GRAY.png");
        write_png(&source_path, 11, 8, Rgb([80, 90, 100]));
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/source/{surface_key}/{coil_id}/{type_}",
                axum::routing::get(source_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/source/S/42/GRAY")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("source png");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/png");
        assert_eq!(image.dimensions(), (11, 8));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn preview_image_route_reads_jpeg_preview_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let preview_path = save_s.join("42").join("preview").join("GRAY.jpeg");
        write_jpeg(&preview_path, 13, 9, Rgb([20, 30, 40]));
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/image/preview/{surface_key}/{coil_id}/{type_}",
                axum::routing::get(preview_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/image/preview/S/42/GRAY")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("preview jpeg");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (13, 9));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn render_thumbnail_resolution_uses_testdata_falsecolor_cache_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let thumbnail_path = testdata_dir
            .join("S")
            .join("cache")
            .join("falsecolor")
            .join("gray")
            .join("thumbnail_1024.jpg");
        let config_path = temp_dir.join("Server3D.json");
        write_jpeg(&thumbnail_path, 16, 12, Rgb([80, 90, 100]));
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        write_testdata_config(&config_path, &save_s, &testdata_dir);

        let config = RuntimeConfig::load(&config_path).expect("load config");
        let state = AppState::new(config);
        let resolved = resolve_render_cache_path(
            &state,
            "S",
            "193113",
            &RenderQuery {
                thumbnail: Some(true),
                grayscale: Some(true),
                ..RenderQuery::default()
            },
        );

        assert_eq!(resolved.as_deref(), Some(thumbnail_path.as_path()));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn error_cache_resolution_requires_matching_threshold_metadata_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let error_path = testdata_dir.join("S").join("png").join("Error.png");
        let config_path = temp_dir.join("Server3D.json");
        write_png(&error_path, 8, 6, Rgb([255, 0, 0]));
        fs::write(
            error_path.with_extension("json"),
            serde_json::json!({
                "threshold_down": 10.0,
                "threshold_up": 250.0,
            })
            .to_string(),
        )
        .expect("write error metadata");
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        write_testdata_config(&config_path, &save_s, &testdata_dir);

        let config = RuntimeConfig::load(&config_path).expect("load config");
        let state = AppState::new(config);
        let matching = resolve_error_cache_path(
            &state,
            "S",
            "193113",
            &ErrorImageQuery {
                scale: None,
                min_value: Some(-10.0),
                max_value: Some(250.0),
                force_cache: None,
            },
        );
        let stale = resolve_error_cache_path(
            &state,
            "S",
            "193113",
            &ErrorImageQuery {
                scale: None,
                min_value: Some(10.0),
                max_value: Some(100.0),
                force_cache: None,
            },
        );

        assert_eq!(matching.as_deref(), Some(error_path.as_path()));
        assert!(stale.is_none());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_render_route_serves_testdata_thumbnail_cache_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let thumbnail_path = testdata_dir
            .join("S")
            .join("cache")
            .join("falsecolor")
            .join("gray")
            .join("thumbnail_1024.jpg");
        write_jpeg(&thumbnail_path, 16, 12, Rgb([80, 90, 100]));
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Render/{surface_key}/{coil_id}",
                axum::routing::get(render_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Render/S/193113?thumbnail=true&grayscale=true")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            response.headers().get(header::CONTENT_TYPE).unwrap(),
            "image/jpeg"
        );
        assert_eq!(response.headers().get("x-thumbnail").unwrap(), "true");
        assert_eq!(response.headers().get("x-colormap").unwrap(), "GRAY");
        assert_eq!(response.headers().get("x-from-cache").unwrap(), "true");

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_render_route_generates_scaled_jpeg_from_depth_when_cache_is_missing() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("324");
        fs::create_dir_all(&coil_dir).expect("render coil dir");
        let array = arr2(&[[0.0, 50.0, 100.0, 150.0], [200.0, 250.0, 300.0, 350.0]]);
        write_npy(coil_dir.join("3D.npy"), &array).expect("write render npy");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Render/{surface_key}/{coil_id}",
                axum::routing::get(render_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Render/S/324?scale=0.5&mask=false&minValue=0&maxValue=350")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("generated render jpeg")
            .to_rgb8();

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(headers.get("x-thumbnail").unwrap(), "false");
        assert_eq!(headers.get("x-colormap").unwrap(), "JET");
        assert_eq!(headers.get("x-from-cache").unwrap(), "false");
        assert_eq!(image.dimensions(), (2, 1));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_error_route_serves_matching_testdata_error_cache_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let error_path = testdata_dir.join("S").join("png").join("Error.png");
        write_png(&error_path, 8, 6, Rgb([255, 0, 0]));
        fs::write(
            error_path.with_extension("json"),
            serde_json::json!({
                "threshold_down": 100.0,
                "threshold_up": 100.0,
            })
            .to_string(),
        )
        .expect("write error metadata");
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Error/{surface_key}/{coil_id}",
                axum::routing::get(error_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Error/S/193113?scale=1&mask=false&minValue=-100&maxValue=100")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            response.headers().get(header::CONTENT_TYPE).unwrap(),
            "image/png"
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_error_route_generates_png_from_depth_when_cache_is_missing() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("407");
        fs::create_dir_all(coil_dir.join("mask")).expect("error mask dir");
        write_npy(coil_dir.join("3D.npy"), &arr2(&[[1100.0, 1100.0, 5000.0]]))
            .expect("write error npy");
        let mut mask = GrayImage::from_pixel(3, 1, Luma([255]));
        mask.put_pixel(2, 0, Luma([0]));
        mask.save_with_format(
            coil_dir.join("mask").join("MASK.png"),
            image::ImageFormat::Png,
        )
        .expect("write error mask");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Error/{surface_key}/{coil_id}",
                axum::routing::get(error_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Error/S/407?mask=true&minValue=0&maxValue=0")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        assert_eq!(status, StatusCode::OK);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("generated error png")
            .to_rgba8();

        assert_eq!(status, StatusCode::OK);
        assert_eq!(image.dimensions(), (3, 1));
        assert_eq!(image.get_pixel(2, 0).0, [255, 0, 0, 255]);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_area_route_generates_colored_png_from_depth_when_cache_is_missing() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("512");
        fs::create_dir_all(coil_dir.join("mask")).expect("area mask dir");
        write_npy(
            coil_dir.join("3D.npy"),
            &arr2(&[[5.0, 15.0, 25.0, 35.0], [45.0, 55.0, 65.0, 75.0]]),
        )
        .expect("write area npy");
        let mut mask = GrayImage::from_pixel(4, 2, Luma([255]));
        mask.put_pixel(2, 0, Luma([0]));
        mask.save_with_format(
            coil_dir.join("mask").join("MASK.png"),
            image::ImageFormat::Png,
        )
        .expect("write area mask");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Area/{surface_key}/{coil_id}",
                axum::routing::get(coil_data_area_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Area/S/512?scale=0.5&mask=true&valueFrom=20&valueTo=70&r=10&g=20&b=30")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("generated area png")
            .to_rgba8();

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/png");
        assert_eq!(image.dimensions(), (2, 1));
        assert_eq!(image.get_pixel(0, 0).0, [0, 0, 0, 0]);
        assert_eq!(image.get_pixel(1, 0).0, [10, 20, 30, 255]);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_area_route_uses_testdata_surface_dir_for_positive_coil_ids() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let surface_dir = testdata_dir.join("S");
        fs::create_dir_all(&surface_dir).expect("testdata area surface dir");
        write_npy(surface_dir.join("3D.npy"), &arr2(&[[10.0, 40.0]])).expect("write area npy");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Area/{surface_key}/{coil_id}",
                axum::routing::get(coil_data_area_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Area/S/193113?valueFrom=20&valueTo=60&r=1&g=2&b=3")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        assert_eq!(status, StatusCode::OK);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("generated testdata area png")
            .to_rgba8();

        assert_eq!(image.dimensions(), (2, 1));
        assert_eq!(image.get_pixel(0, 0).0, [0, 0, 0, 0]);
        assert_eq!(image.get_pixel(1, 0).0, [1, 2, 3, 255]);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_area_route_uses_testdata_dir_for_non_testdata_positive_coil_ids_like_main_api()
     {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let production_dir = save_s.join("1753");
        fs::create_dir_all(&production_dir).expect("production area surface dir");
        write_npy(production_dir.join("3D.npy"), &arr2(&[[10.0, 40.0, 80.0]]))
            .expect("write production area npy");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let testdata_surface_dir = testdata_dir.join("S");
        fs::create_dir_all(&testdata_surface_dir).expect("testdata area surface dir");
        write_npy(testdata_surface_dir.join("3D.npy"), &arr2(&[[10.0, 40.0]]))
            .expect("write testdata area npy");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Area/{surface_key}/{coil_id}",
                axum::routing::get(coil_data_area_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Area/S/1753?valueFrom=20&valueTo=60&r=1&g=2&b=3")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        assert_eq!(status, StatusCode::OK);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("generated testdata area png")
            .to_rgba8();

        assert_eq!(image.dimensions(), (2, 1));
        assert_eq!(image.get_pixel(0, 0).0, [0, 0, 0, 0]);
        assert_eq!(image.get_pixel(1, 0).0, [1, 2, 3, 255]);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_area_route_returns_python_internal_error_when_depth_file_is_missing() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        fs::create_dir_all(save_s.join("1701")).expect("area coil dir without depth");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Area/{surface_key}/{coil_id}",
                axum::routing::get(coil_data_area_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Area/S/1701?valueFrom=20&valueTo=70&r=10&g=20&b=30")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(
            axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .expect("body")
                .as_ref(),
            b"Internal Server Error"
        );

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn coil_data_error_route_returns_main_api_sized_transparent_png_without_cache() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        fs::create_dir_all(testdata_dir.join("S")).expect("create testdata surface");
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/coilData/Error/{surface_key}/{coil_id}",
                axum::routing::get(error_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/coilData/Error/S/193113?force_cache=true&minValue=-100&maxValue=100")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("transparent png");
        assert_eq!(image.dimensions(), (100, 100));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn defect_image_route_crops_named_source_image_like_main_api() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let source_path = save_s.join("42").join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 5, 4);
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
                axum::routing::get(defect_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/defect_image/S/42/GRAY/1/1/2/2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body)
            .expect("cropped defect jpeg")
            .to_rgb8();

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (2, 2));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn defect_image_route_uses_gray_crop_when_main_api_detection_lookup_misses_surface_detection_dir()
     {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let source_path = save_s.join("1753").join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 5, 4);
        let detection_dir = save_s.join("1753").join("detection").join("scratch");
        let detection_image = detection_dir.join("candidate.png");
        write_png(&detection_image, 7, 6, Rgb([250, 5, 10]));
        fs::write(
            detection_image.with_extension("xml"),
            "<annotation><object><bndbox><xmin>1</xmin><ymin>1</ymin><xmax>3</xmax><ymax>3</ymax></bndbox></object></annotation>",
        )
        .expect("write detection xml");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
                axum::routing::get(defect_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/defect_image/S/1753/GRAY/1/1/2/2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("defect gray crop");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (2, 2));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn defect_image_route_uses_python_defaults_for_nan_path_coordinates() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let source_path = save_s.join("42").join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 160, 130);
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
                axum::routing::get(defect_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/defect_image/S/42/GRAY/NaN/NaN/NaN/NaN")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("default defect jpeg");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (100, 100));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn defect_image_route_rejects_invalid_coil_id_like_python_int_converter() {
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: unique_temp_dir(),
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
                axum::routing::get(defect_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/defect_image/S/abc/GRAY/1/2/3/4")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");

        assert_eq!(status, StatusCode::NOT_FOUND);
        assert_eq!(
            headers.get(header::CONTENT_TYPE).unwrap(),
            "application/json"
        );
        assert_eq!(&body[..], br#"{"detail":"Not Found"}"#);
    }

    #[tokio::test]
    async fn classifier_image_route_crops_runtime_gray_image_when_cache_is_missing() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let source_path = save_s.join("42").join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 5, 4);
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
                axum::routing::get(classifier_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/classifier_image/42/S/scratch/1/1/2/2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("classifier jpeg");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/jpeg");
        assert_eq!(image.dimensions(), (2, 2));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn classifier_image_route_prefers_cached_classifier_png() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let cache_path = save_s
            .join("42")
            .join("classifier")
            .join("scratch")
            .join("42_1_2_99_99.png");
        write_png(&cache_path, 7, 6, Rgb([250, 5, 10]));
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
                axum::routing::get(classifier_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/classifier_image/42/S/scratch/1/2/99/99")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("classifier cached png");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/png");
        assert_eq!(image.dimensions(), (7, 6));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn classifier_image_route_prefers_production_cache_in_test_mode_like_python() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let cache_path = save_s
            .join("1753")
            .join("classifier")
            .join("scratch")
            .join("1753_0_0_7_6.png");
        write_png(&cache_path, 7, 6, Rgb([250, 5, 10]));
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        write_jpeg(
            &testdata_dir.join("S").join("jpg").join("GRAY.jpg"),
            3,
            2,
            Rgb([1, 2, 3]),
        );
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
                axum::routing::get(classifier_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/classifier_image/1753/S/scratch/0/0/20/20")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("classifier production png");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/png");
        assert_eq!(image.dimensions(), (7, 6));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn defect_image_route_prefers_production_detection_in_test_mode_like_python() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        write_pattern_jpeg(&save_s.join("1753").join("jpg").join("GRAY.jpg"), 20, 20);
        let detection_dir = temp_dir.join("1753").join("detection").join("scratch");
        let detection_image = detection_dir.join("candidate.png");
        write_png(&detection_image, 7, 6, Rgb([250, 5, 10]));
        fs::write(
            detection_image.with_extension("xml"),
            "<annotation><object><bndbox><xmin>0</xmin><ymin>0</ymin><xmax>20</xmax><ymax>20</ymax></bndbox></object></annotation>",
        )
        .expect("write detection xml");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        write_pattern_jpeg(&testdata_dir.join("S").join("jpg").join("GRAY.jpg"), 5, 4);
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
                axum::routing::get(defect_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/defect_image/S/1753/GRAY/1/1/2/2")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        let image = image::load_from_memory(&body).expect("defect production png");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(headers.get(header::CONTENT_TYPE).unwrap(), "image/png");
        assert_eq!(image.dimensions(), (7, 6));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn clip_max_image_route_splits_runtime_gray_image_into_python_named_tiles() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("42");
        let source_path = coil_dir.join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 1800, 1800);
        fs::create_dir_all(coil_dir.join("mask")).expect("clip mask dir");
        GrayImage::from_pixel(1800, 1800, Luma([255]))
            .save_with_format(
                coil_dir.join("mask").join("MASK.png"),
                image::ImageFormat::Png,
            )
            .expect("write full clip mask");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/clipMaxImage/{coil_id}/{surface_key}",
                axum::routing::get(clip_max_image),
            )
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri("/clipMaxImage/42/S")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        let status = response.status();
        let headers = response.headers().clone();
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");

        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            headers.get(header::CONTENT_TYPE).unwrap(),
            "application/json"
        );
        assert_eq!(&body[..], b"null");

        let output_dir = coil_dir.join("clip_max");
        let output_files = fs::read_dir(&output_dir)
            .expect("clip output dir")
            .map(|entry| entry.expect("clip output entry").path())
            .collect::<Vec<_>>();
        assert_eq!(output_files.len(), 100);
        let first_tile = output_dir.join("42_S_0_0_200_200.png");
        assert!(first_tile.exists());
        let image = image::open(first_tile).expect("first clip tile");
        assert_eq!(image.dimensions(), (200, 200));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn clip_max_image_route_honors_encoded_save_url_query() {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("42");
        let source_path = coil_dir.join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 1800, 1800);
        fs::create_dir_all(coil_dir.join("mask")).expect("clip mask dir");
        GrayImage::from_pixel(1800, 1800, Luma([255]))
            .save_with_format(
                coil_dir.join("mask").join("MASK.png"),
                image::ImageFormat::Png,
            )
            .expect("write full clip mask");
        let custom_output = temp_dir.join("custom clips");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: None,
        }));
        let app = axum::Router::new()
            .route(
                "/clipMaxImage/{coil_id}/{surface_key}",
                axum::routing::get(clip_max_image),
            )
            .with_state(state);

        let uri = format!(
            "/clipMaxImage/42/S?save_url={}",
            encode_query_path(&custom_output)
        );
        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);

        let output_dir = custom_output.join("clip_max");
        assert!(output_dir.join("42_S_0_0_200_200.png").exists());
        assert!(!coil_dir.join("clip_max").exists());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn clip_max_image_route_uses_testdata_dir_for_non_testdata_positive_coil_ids_like_main_api()
     {
        let temp_dir = unique_temp_dir();
        let save_s = temp_dir.join("Save_S");
        let coil_dir = save_s.join("1753");
        let source_path = coil_dir.join("jpg").join("GRAY.jpg");
        write_pattern_jpeg(&source_path, 1800, 1800);
        fs::create_dir_all(coil_dir.join("mask")).expect("clip mask dir");
        GrayImage::from_pixel(1800, 1800, Luma([255]))
            .save_with_format(
                coil_dir.join("mask").join("MASK.png"),
                image::ImageFormat::Png,
            )
            .expect("write full clip mask");
        let testdata_dir = temp_dir.join("TestData").join("to").join("193113");
        let testdata_surface_dir = testdata_dir.join("S");
        write_pattern_jpeg(
            &testdata_surface_dir.join("jpg").join("GRAY.jpg"),
            2200,
            2200,
        );
        fs::create_dir_all(testdata_surface_dir.join("mask")).expect("testdata clip mask dir");
        GrayImage::from_pixel(2200, 2200, Luma([255]))
            .save_with_format(
                testdata_surface_dir.join("mask").join("MASK.png"),
                image::ImageFormat::Png,
            )
            .expect("write testdata full clip mask");
        fs::write(testdata_dir.join("3D.npz"), b"").expect("write testdata depth marker");
        let custom_output = temp_dir.join("custom clips");
        let state = Arc::new(AppState::new(RuntimeConfig {
            surfaces: vec![SurfaceConfig {
                key: "S".to_string(),
                save_folder: save_s,
            }],
            test_data: Some(crate::app_config::TestDataConfig {
                enabled: true,
                coil_id: 193113,
                data_dir: testdata_dir,
            }),
        }));
        let app = axum::Router::new()
            .route(
                "/clipMaxImage/{coil_id}/{surface_key}",
                axum::routing::get(clip_max_image),
            )
            .with_state(state);

        let uri = format!(
            "/clipMaxImage/1753/S?save_url={}",
            encode_query_path(&custom_output)
        );
        let response = app
            .oneshot(
                axum::http::Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);

        let output_dir = custom_output.join("clip_max");
        assert!(output_dir.join("1753_S_0_0_240_240.png").exists());
        assert!(!output_dir.join("1753_S_0_0_200_200.png").exists());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn defect_image_crop_pads_out_of_bounds_like_main_api() {
        let source = RgbImage::from_pixel(4, 4, Rgb([200, 100, 50]));

        let crop = defect_image_crop(&source, -1, -1, 3, 3);

        assert_eq!(crop.dimensions(), (3, 3));
        assert_eq!(crop.get_pixel(0, 0).0, [200, 100, 50]);
        assert_eq!(crop.get_pixel(2, 2).0, [0, 0, 0]);
    }

    #[test]
    fn area_tile_fallback_crop_uses_python_swapped_row_col_axes() {
        let mut source = GrayImage::new(90, 60);
        for y in 0..60 {
            for x in 0..90 {
                let tile_x = x / 30;
                let tile_y = y / 20;
                source.put_pixel(x, y, Luma([(tile_y * 80 + tile_x * 20) as u8]));
            }
        }

        let tile = crop_area_tile_gray(&source, 1, 2, 3).expect("area tile");

        assert_eq!(tile.dimensions(), (30, 20));
        assert_eq!(
            tile.get_pixel(0, 0)[0],
            180,
            "Python's fallback crop uses x=row and y=col"
        );
    }
}
