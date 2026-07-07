# Render and Overlay Pixel Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove and close pixel-level parity gaps for Rust `/coilData/Render`, `/coilData/Area`, and `/coilData/Error` against Python `ApiDataServer.py`, including full-size render, thumbnail cache behavior, error-cache metadata, malformed TestData paths, and React image URL parameters.

**Architecture:** Keep Rust native image generation as the default path, but drive it from a Python/Rust fixture comparison harness that renders identical small `.npy`/mask/cache samples through both implementations. Treat Python OpenCV behavior as authoritative for normalization, resizing, JET/GRAY color maps, mask handling, cache hit/miss rules, and HTTP response status/body semantics.

**Tech Stack:** Rust image generation in `app/Server/rust_api_service/src/routes.rs`, Python FastAPI reference in `app/Server/api/ApiDataServer.py`, Python `cache/falsecolor_cache.py`, synthetic `.npy`/PNG/JPEG fixtures, React `app/UI/MotionStudioWeb/src/services/api.ts`.

---

### Task 1: Add a Python/Rust render comparison fixture set

**Files:**
- Create: `test/render_parity/fixtures.py`
- Create: `test/render_parity/test_render_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing tests**

Create deterministic fixture helpers for:

- `DEPTH.npy`: small matrix with values below min, at min, midpoint, max, above max, zero, and `1001` valid baseline values.
- `MASK.png`: single-channel mask with both zero and nonzero pixels.
- `cache/falsecolor/{jet,gray}/thumbnail_1024.jpg` optional cache files.
- `png/Error.png` plus sibling `Error.json` metadata.

Add Rust route tests named:

```rust
#[tokio::test]
async fn render_full_size_matches_python_fixture_pixels_for_jet_and_gray() {
    let fixture = write_render_parity_fixture();
    let app = app_with_data_config(fixture.data_config());

    let jet = request_bytes(app.clone(), "/coilData/Render/S/900001?scale=1&mask=true&minValue=0&maxValue=10").await;
    let gray = request_bytes(app, "/coilData/Render/S/900001?scale=1&mask=true&minValue=0&maxValue=10&grayscale=true").await;

    assert_image_matches_fixture("python-render-jet-mask.jpg", &jet, 1);
    assert_image_matches_fixture("python-render-gray-mask.jpg", &gray, 1);
}
```

**Step 2: Run tests to verify they fail or reveal drift**

Run:

```bash
pytest test/render_parity/test_render_reference.py -v
cargo test render_full_size_matches_python_fixture_pixels_for_jet_and_gray --test routes
```

Expected: FAIL until Python reference images are generated and Rust output is compared against them.

**Step 3: Write minimal implementation**

- Make the Python fixture generator produce canonical JPEG/PNG bytes using `ApiDataServer.py` logic, not duplicated formulas.
- Store tiny expected outputs under `test/render_parity/expected/` only if they are stable and small; otherwise generate them at test runtime.
- Add Rust helpers to decode returned images and compare pixels with a small JPEG tolerance.

**Step 4: Run tests to verify they pass**

Run:

```bash
pytest test/render_parity/test_render_reference.py -v
cargo test render_full_size_matches_python_fixture_pixels_for_jet_and_gray --test routes
```

Expected: PASS.

**Step 5: Commit**

```bash
git add test/render_parity app/Server/rust_api_service/tests/routes.rs
git commit -m "test: add render parity fixtures"
```

### Task 2: Lock full-size Render OpenCV semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing tests**

Add coverage for Python-specific behavior:

```rust
#[tokio::test]
async fn render_full_size_matches_python_resize_threshold_and_mask_interpolation() {
    let fixture = write_render_parity_fixture();
    let app = app_with_data_config(fixture.data_config());

    let no_resize = request_bytes(app.clone(), "/coilData/Render/S/900001?scale=0.99&mask=true&minValue=0&maxValue=10").await;
    let resized = request_bytes(app, "/coilData/Render/S/900001?scale=0.5&mask=true&minValue=0&maxValue=10").await;

    assert_image_matches_fixture("python-render-scale-099.jpg", &no_resize, 1);
    assert_image_matches_fixture("python-render-scale-05.jpg", &resized, 1);
}
```

**Step 2: Run test to verify it fails if any drift remains**

Run: `cargo test render_full_size_matches_python_resize_threshold_and_mask_interpolation --test routes`

Expected: FAIL if Rust still differs in `cv2.resize`, mask interpolation, dimension truncation, JPEG quality, or `maxValue <= minValue` correction.

**Step 3: Write minimal implementation**

In `routes.rs` render path:

- Preserve `max_value <= min_value => max_value = min_value + 1` like Python.
- Preserve `scale < 0.99` resize threshold.
- Preserve `int(width * scale)` / `int(height * scale)` truncation.
- Preserve OpenCV-style bilinear resize for full render depth and Python-compatible mask resizing.
- Preserve `cv2.applyColorMap(COLORMAP_JET)` lookup table.
- Preserve JPEG quality `90` and response headers `X-Thumbnail=false`, `X-Colormap=JET|GRAY`.

**Step 4: Run test to verify it passes**

Run: `cargo test render_full_size_matches_python_resize_threshold_and_mask_interpolation --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: align full render OpenCV semantics"
```

### Task 3: Lock thumbnail falsecolor cache behavior

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`
- Reference: `app/Server/cache/falsecolor_cache.py`

**Step 1: Write the failing tests**

Add tests for both cache hit and cold-cache generation:

```rust
#[tokio::test]
async fn render_thumbnail_uses_python_falsecolor_cache_paths_and_headers() {
    let fixture = write_render_parity_fixture_with_cached_thumbnail("jet");
    let app = app_with_data_config(fixture.data_config());

    let response = request_response(app, "GET", "/coilData/Render/S/900001?thumbnail=true&minValue=0&maxValue=10").await;

    assert_eq!(response.headers()["X-Thumbnail"], "true");
    assert_eq!(response.headers()["X-From-Cache"], "true");
    assert_eq!(response.headers()["X-Colormap"], "JET");
    assert_eq!(body_bytes(response).await, fixture.cached_thumbnail_bytes("jet"));
}
```

**Step 2: Run test to verify it fails if drift remains**

Run: `cargo test render_thumbnail_uses_python_falsecolor_cache_paths_and_headers --test routes`

Expected: FAIL if Rust uses wrong cache path/case, wrong headers, wrong JPEG quality, or wrong mask behavior.

**Step 3: Write minimal implementation**

- Use `cache/falsecolor/{jet|gray}/thumbnail_1024.jpg` path under coil dir.
- Return Python-compatible headers: `X-Thumbnail=true`, `X-From-Cache=true|false`, `X-Colormap=JET|GRAY`.
- On cold cache, generate with Python `FalseColorCache.generate_thumbnail` semantics: INTER_AREA for depth resize, INTER_NEAREST for mask resize, JPEG quality `85`.
- Keep Python cold-cache grayscale+mask quirk if already observed and documented.

**Step 4: Run test to verify it passes**

Run: `cargo test render_thumbnail_uses_python_falsecolor_cache_paths_and_headers --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: align falsecolor thumbnail cache"
```

### Task 4: Lock Error overlay cache and threshold semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing tests**

Add tests for metadata cache hit/miss and threshold conversion:

```rust
#[tokio::test]
async fn error_overlay_uses_python_cache_metadata_before_dynamic_generation() {
    let fixture = write_error_cache_fixture(threshold_down: 15.0, threshold_up: 20.0);
    let app = app_with_data_config(fixture.data_config());

    let response = request_response(app, "GET", "/coilData/Error/S/900001?minValue=15&maxValue=20&force_cache=true").await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(response.headers()[CONTENT_TYPE], "image/png");
    assert_eq!(body_bytes(response).await, fixture.error_png_bytes());
}
```

**Step 2: Run test to verify it fails if drift remains**

Run: `cargo test error_overlay_uses_python_cache_metadata_before_dynamic_generation --test routes`

Expected: FAIL if Rust ignores metadata, applies thresholds in raw units instead of mm around median, or filters through mask incorrectly.

**Step 3: Write minimal implementation**

- Mirror Python `_get_error_render_baseline()` fallback order: `CoilState.scan3dCoordinateScaleZ`, `CoilState.median_3d`, otherwise median of `npy_data > 1000`.
- Mirror `_error_cache_matches()` with absolute mm thresholds and `math.isclose(..., abs_tol=1e-9)` equivalent.
- Preserve Python `force_cache=true` behavior: return matching `png/Error.png` before dynamic generation; if forced and no match, return Python-compatible blank/placeholder behavior already documented in row 51.
- Preserve raw 3D threshold behavior without applying `MASK.png` filtering.
- Preserve PNG output content type.

**Step 4: Run test to verify it passes**

Run: `cargo test error_overlay_uses_python_cache_metadata_before_dynamic_generation --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: align error overlay cache semantics"
```

### Task 5: Decide and lock malformed/TestData behavior for Area overlay

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Row 51 currently says Area mirrors Python's unhandled-error behavior for malformed/non-TestData string ids. Lock that explicitly:

```rust
#[tokio::test]
async fn area_overlay_preserves_python_malformed_testdata_error_behavior() {
    let app = app_with_test_mode_enabled();
    let response = request_response(app, "GET", "/coilData/Area/S/abc?valueFrom=0&valueTo=10").await;

    assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    assert_eq!(body_text(response).await, "Internal Server Error");
}
```

**Step 2: Run test to verify current behavior**

Run: `cargo test area_overlay_preserves_python_malformed_testdata_error_behavior --test routes`

Expected: PASS if current parity is intentional; FAIL if Rust has drifted.

**Step 3: Write minimal implementation or document exception**

- If Python reference still returns 500, keep Rust 500 and document it as intentional parity.
- If Python has changed, update Rust to match current Python behavior and update row 51.
- Ensure Area overlay still does not filter by `MASK.png` in dynamic success path.

**Step 4: Run test to verify it passes**

Run: `cargo test area_overlay_preserves_python_malformed_testdata_error_behavior --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs docs/rust-tauri-parity.md
git commit -m "api: lock area overlay malformed-id parity"
```

### Task 6: Validate React/Tauri image URL contract against Python parameter aliases

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Test: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Write the failing tests**

Add route-builder tests for all aliases Python accepts:

```ts
it('builds Python-compatible Render and Error URLs for QML/Tauri image requests', () => {
  expect(buildCoilDataRenderPath('S', 900001, {
    scale: 0.5,
    mask: true,
    minValue: -30,
    maxValue: 45,
    thumbnail: true,
    grayscale: true,
  })).toBe('/coilData/Render/S/900001?scale=0.5&mask=true&minValue=-30&maxValue=45&thumbnail=true&grayscale=true')

  expect(buildCoilDataErrorPath('L', 900001, { minValue: 15, maxValue: 20 })).toBe(
    '/coilData/Error/L/900001?minValue=15&maxValue=20',
  )
})
```

**Step 2: Run test to verify it fails if URL aliases drift**

Run: `npm test -- api`

Expected: PASS if current builders are already correct, otherwise FAIL until fixed.

**Step 3: Write minimal implementation**

- Keep `minValue`/`maxValue` aliases for QML compatibility.
- Do not rename to `min_value`/`max_value` in React unless both aliases are sent intentionally.
- Preserve `force_cache` for Error route and avoid sending it to Render.

**Step 4: Run test to verify it passes**

Run: `npm test -- api`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/UI/MotionStudioWeb/src/services/api.ts app/UI/MotionStudioWeb/src/services/api.test.ts
git commit -m "ui: lock render overlay URL aliases"
```

### Task 7: Representative production-sample parity gate

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-render-overlay-pixel-parity.md`

**Step 1: Prepare non-destructive sample matrix**

Use copied or read-only sample folders only. Cover:

- One coil with full-size `3D/*.npy` and `MASK.png` for `S`.
- One coil with full-size `3D/*.npy` and `MASK.png` for `L`.
- One coil with existing `cache/falsecolor` thumbnails.
- One coil with matching `png/Error.png` and `Error.json` metadata.
- One coil where caches are absent, to force dynamic generation into a copied temp folder.

**Step 2: Run final checks only with explicit authorization**

```bash
cargo test render_ error_overlay area_overlay --test routes
pytest test/render_parity/test_render_reference.py -v
npm test -- api
```

Expected: PASS.

**Step 3: Live comparison only after approval**

Start Python and Rust against read-only/copy data and compare bytes or decoded pixels for:

```text
/coilData/Render/S/{coil}?scale=1&mask=true&minValue=0&maxValue=255
/coilData/Render/S/{coil}?scale=0.5&mask=true&minValue=0&maxValue=255
/coilData/Render/S/{coil}?thumbnail=true&mask=true&minValue=0&maxValue=255
/coilData/Render/S/{coil}?thumbnail=true&mask=true&grayscale=true&minValue=0&maxValue=255
/coilData/Area/S/{coil}?scale=1&mask=false&valueFrom=0&valueTo=255
/coilData/Error/S/{coil}?scale=1&mask=false&minValue=-100&maxValue=100&force_cache=true
```

**Step 4: Update parity row only after evidence**

Keep row Partial until evidence proves:

- Full-size Render decoded pixels match or remain within documented JPEG tolerance.
- Thumbnail cache hit/miss headers and bytes match Python.
- Error overlay cache metadata and threshold conversion match Python.
- Area malformed/TestData behavior matches current Python.
- React/Tauri URL aliases are covered.

**Step 5: Commit**

```bash
git add docs/rust-tauri-parity.md docs/plans/2026-07-06-render-overlay-pixel-parity.md
git commit -m "infra: document render overlay parity gate"
```