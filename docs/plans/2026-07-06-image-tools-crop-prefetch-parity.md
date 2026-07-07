# Image Tools, Crop, and Prefetch Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close parity for `/image/preview`, `/image/source`, `/image/area`, `/classifier_image`, `/defect_image`, and `/clipMaxImage` across the Rust main API, standalone Rust image service, and Tauri+React image workflows.

**Architecture:** Treat the Python `ApiDataServer.py`/`ApiDataBase.py` image behavior as the authority, then lock Rust main API and standalone `6013` image-service behavior to the same resolver, crop, cache, and failure semantics. Validate the React image-service mode with deterministic URL generation, cancellation, and background prefetch behavior so UI consumers do not depend on stale or service-specific cache quirks.

**Tech Stack:** Rust Axum services, Python FastAPI/Pillow/OpenCV reference implementation, Vitest/React Testing Library, pytest, image byte and decoded-pixel fixture comparison.

---

### Task 1: Build the cross-service image fixture matrix

**Files:**
- Create: `test/image_tools_parity/README.md`
- Create: `test/image_tools_parity/fixtures.py`
- Create: `test/image_tools_parity/test_image_tools_reference.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`

**Step 1: Write the failing Python fixture tests**

Create a small fixture builder that copies or synthesizes the exact folder shapes used by production image requests:

```python
from pathlib import Path

from PIL import Image


def write_rgb(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (8, 8)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', size, color).save(path)


def build_image_tool_fixture(root: Path, coil_id: str = '193113') -> Path:
    surface = root / coil_id / 'S'
    write_rgb(surface / 'jpg' / 'GRAY.jpg', (20, 40, 60), (16, 12))
    write_rgb(surface / 'cache' / 'preview' / 'GRAY.jpg', (80, 100, 120), (4, 3))
    write_rgb(surface / 'cache' / 'classifier' / 'scratch' / f'{coil_id}_S_scratch_1_2.png', (200, 10, 20), (2, 2))
    write_rgb(surface / 'Detection' / 'scratch' / '1_2_4_4.jpg', (10, 200, 20), (4, 4))
    write_rgb(surface / 'cache' / 'AREA' / 'L4' / '0_0.jpg', (20, 20, 200), (256, 256))
    return surface
```

**Step 2: Run the reference fixture tests to verify the fixture is meaningful**

Run: `pytest test/image_tools_parity/test_image_tools_reference.py -v`

Expected: FAIL until the tests assert the Python reference paths and expected bytes/pixels.

**Step 3: Add Rust fixture helpers without changing route behavior**

In both Rust services, add test-only helpers that create the same directory matrix under `temp_dir()` and expose shared expectations:

```rust
#[cfg(test)]
struct ImageToolFixture {
    root: std::path::PathBuf,
    coil_id: &'static str,
}
```

Do not introduce a new production abstraction yet; first make the existing behavior observable.

**Step 4: Run focused Rust fixture tests**

Run: `cargo test -p rust_api_service image_tool_fixture -- --nocapture`

Run: `cargo test -p rust_image_service image_tool_fixture -- --nocapture`

Expected: fixture setup passes, route parity assertions still fail where behavior is incomplete.

### Task 2: Lock `/image/preview` and `/image/source` resolver parity

**Files:**
- Modify: `app/Server/api/ApiDataServer.py`
- Modify: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`
- Test: `test/image_tools_parity/test_image_tools_reference.py`

**Step 1: Write failing parity cases**

Cover these cases against Python reference expectations:

```python
def test_preview_prefers_preview_cache_when_available(fixture_root):
    # /image/preview/S/193113/GRAY returns cache/preview/GRAY.jpg
    pass


def test_source_returns_full_source_when_preview_cache_exists(fixture_root):
    # /image/source/S/193113/GRAY returns jpg/GRAY.jpg, not preview cache
    pass


def test_missing_source_uses_python_no_find_image_contract(fixture_root):
    # Match status/content contract from Python, not a generic Rust 500.
    pass
```

**Step 2: Run targeted reference tests**

Run: `pytest test/image_tools_parity/test_image_tools_reference.py::test_preview_prefers_preview_cache_when_available -v`

Expected: FAIL until the expected Python behavior is encoded.

**Step 3: Add matching Rust route assertions**

Assert main API and image service return the same content type, status code, and decoded dimensions for preview/source requests.

**Step 4: Implement the minimal resolver correction**

If main API and image service differ, extract only the path-selection logic into a small shared helper module or duplicate an explicitly tested helper in each crate. Prefer shared behavior only if it does not create a broader workspace refactor.

**Step 5: Run the focused parity checks**

Run: `cargo test -p rust_api_service image_preview_source -- --nocapture`

Run: `cargo test -p rust_image_service image_preview_source -- --nocapture`

Expected: PASS for resolver parity cases.

### Task 3: Close classifier crop parity

**Files:**
- Modify: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`
- Test: `test/image_tools_parity/test_image_tools_reference.py`

**Step 1: Write failing tests for cache hit, crop fallback, and invalid coordinates**

Required cases:
- Cached classifier PNG wins over runtime crop.
- Missing cache crops from `jpg/GRAY.jpg` using Python coordinate semantics.
- Negative and out-of-bounds coordinates pad consistently.
- Invalid `coil_id` and invalid coordinate paths match Python route conversion behavior.
- Test mode prefers production classifier cache when Python does.

**Step 2: Run the classifier reference test**

Run: `pytest test/image_tools_parity/test_image_tools_reference.py::test_classifier_cached_png_wins -v`

Expected: FAIL until reference expectations are complete.

**Step 3: Implement minimal Rust crop corrections**

Keep the production code small:

```rust
fn crop_with_python_padding(source: &RgbImage, x: i32, y: i32, w: i32, h: i32) -> RgbImage {
    // Clamp source reads, leave out-of-bounds pixels black, and preserve requested output size.
}
```

Do not change response JSON or headers for unrelated image routes.

**Step 4: Run classifier route tests**

Run: `cargo test -p rust_api_service classifier_image -- --nocapture`

Run: `cargo test -p rust_image_service classifier_image -- --nocapture`

Expected: PASS for cached and fallback classifier requests.

### Task 4: Close defect image parity

**Files:**
- Modify: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`
- Test: `test/image_tools_parity/test_image_tools_reference.py`

**Step 1: Write failing tests for detection lookup and source fallback**

Required cases:
- Detection folder exact match wins when present.
- Missing detection crop falls back to named source image.
- `NaN` path coordinates use Python defaults.
- Invalid `coil_id` is rejected like Python path converter behavior.
- Test mode prefers production detection folder when Python does.

**Step 2: Run the defect reference test**

Run: `pytest test/image_tools_parity/test_image_tools_reference.py::test_defect_detection_lookup_wins -v`

Expected: FAIL until Python reference behavior is captured.

**Step 3: Implement minimal Rust corrections**

Keep lookup order explicit and covered by test names. Do not broaden matching beyond Python's actual file naming rules.

**Step 4: Run defect route tests**

Run: `cargo test -p rust_api_service defect_image -- --nocapture`

Run: `cargo test -p rust_image_service defect_image -- --nocapture`

Expected: PASS for lookup, fallback, NaN, and invalid path cases.

### Task 5: Close AREA tile cache and background prefetch parity

**Files:**
- Modify: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`
- Modify: `app/UI/MotionStudioWeb/src/components/TileImageViewer/utils.ts`
- Test: `app/UI/MotionStudioWeb/src/components/TileImageViewer/utils.test.ts`

**Step 1: Write failing AREA cache tests**

Required cases:
- L4-only cache derives lower levels consistently.
- `count=0`, malformed row/col, and missing `level` match Python fallback behavior.
- Stale cache vs source-newer behavior matches Python cache invalidation.
- AREA and AREA_MASK typed routes do not cross-contaminate cache folders.

**Step 2: Run focused AREA tests**

Run: `cargo test -p rust_image_service area_image -- --nocapture`

Expected: FAIL for any uncovered Python behavior.

**Step 3: Implement minimal cache-generation corrections**

Keep generated cache paths under the same coil/surface cache root Python uses. Avoid background writes outside the fixture or configured data root.

**Step 4: Write React prefetch URL tests**

Add tests for image-service mode:

```ts
expect(buildTileImageUrl({ imageServiceMode: true, surfaceKey: 'S', coilId: 193113, type: 'AREA' }))
  .toBe('/image-api/image/area/S/193113/AREA')
```

Also assert preview cache is only used when the QML-equivalent preference says it should be used.

**Step 5: Run focused React tests**

Run: `npm test -- TileImageViewer/utils.test.ts --runInBand`

Expected: PASS after URL and prefetch logic matches QML behavior.

### Task 6: Close `/clipMaxImage` parity

**Files:**
- Modify: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_image_service/src/image_service.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/coilActions.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/coilActions.test.ts`

**Step 1: Write failing clipMax tests**

Required cases:
- 10 by 10 split behavior matches Python.
- 20 pixel overlap is preserved.
- 2 percent mask threshold selects or skips tiles like Python.
- `save_url` path conversion behavior matches Python and Windows paths.
- Missing input image returns the same Python-compatible error contract.

**Step 2: Run focused clipMax tests**

Run: `cargo test -p rust_image_service clip_max -- --nocapture`

Expected: FAIL until split and response semantics are locked.

**Step 3: Implement minimal Rust corrections**

Keep output naming and folder shape identical to Python so downstream manual inspection tools can reuse the generated files.

**Step 4: Run focused UI action tests**

Run: `npm test -- coilActions.test.ts --runInBand`

Expected: PASS for request URL construction and no-op guards.

### Task 7: Add representative production-sample gates

**Files:**
- Create: `scripts/image_tools_parity/check_image_tools_parity.py`
- Create: `docs/image-tools-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the parity checker script**

The script should accept explicit roots and service URLs. It must never scan the full production tree by default.

```bash
python scripts/image_tools_parity/check_image_tools_parity.py --coil 193113 --surface S --python-url http://127.0.0.1:5011 --rust-url http://127.0.0.1:6013
```

**Step 2: Compare stable response attributes**

For each route compare:
- HTTP status.
- Content type.
- Decoded width and height.
- Pixel hash for deterministic generated crops.
- Error body class for missing inputs.

Avoid byte-for-byte assertions when JPEG encoder differences make that unstable.

**Step 3: Document accepted samples**

Record the coil ids, surfaces, route matrix, and known tolerated JPEG differences in `docs/image-tools-parity-samples.md`.

**Step 4: Update the parity ledger only after evidence exists**

Change row 52 from Partial to Complete only after the checker passes for fixture data and at least one representative production classifier/detection folder.

### Task 8: Rollout and safety gates

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/serviceConnection.ts`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Keep image-service routing behind existing configuration**

Do not make React require standalone `6013`; it must still work through the main `/api` proxy when the standalone service is disabled.

**Step 2: Add visible service-health fallback behavior**

If `6013` is unavailable, React should route image URLs through the main API or show the existing degraded-service state instead of silently breaking image loads.

**Step 3: Run final focused checks**

Run: `pytest test/image_tools_parity -v`

Run: `cargo test -p rust_api_service image_ -- --nocapture`

Run: `cargo test -p rust_image_service image_ -- --nocapture`

Run: `npm test -- TileImageViewer/utils.test.ts coilActions.test.ts --runInBand`

Expected: PASS for all focused image parity coverage.

**Step 4: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If the owner asks for a commit, use scope `api` or `ui` depending on the changed files, for example:

```bash
git add app/Server/rust_api_service app/Server/rust_image_service app/UI/MotionStudioWeb test/image_tools_parity docs

git commit -m "api: close image tool parity"
```
