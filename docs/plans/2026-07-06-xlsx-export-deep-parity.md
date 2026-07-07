# XLSX Export Deep Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Rust XLSX exports closer to Python `Base.utils.export` workbook output by matching table styling, cell formatting, defect-image insertion, and comparison coverage.

**Architecture:** Keep the existing Rust XLSX route and workbook builder, but deepen the generated Office Open XML package. Add focused tests that inspect workbook XML/ZIP entries rather than relying only on file existence. Where Python uses `xlsxwriter`, mirror the observable XLSX artifacts: worksheet tables, style entries, row heights, column widths, drawings, relationships, media files, and sheet names.

**Tech Stack:** Rust, Axum route tests, ZIP/XML inspection helpers in `app/Server/rust_api_service/tests/routes.rs`, current Rust workbook XML builder in `app/Server/rust_api_service/src/routes.rs`, Python references `app/Base/utils/export/export_config.py`, `export_database.py`, `export_image.py`, and `app/Server/api/ApiBackupServer.py`.

---

### Task 1: Mirror Python data-report table metadata

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Python `export_info_data()` calls `worksheet.add_table(0, 0, len(data)-1, len(data[0])-1, {"style": "Table Style Medium 9", "autofilter": True})`. Add a test that opens the Rust XLSX ZIP and asserts the data-report sheet has a table relationship and table XML with `TableStyleMedium9`.

```rust
#[tokio::test]
async fn xlsx_data_report_uses_python_table_style_medium_9() {
    let bytes = assert_xlsx_export_response(
        request_response(app_with_seed_data(), "GET", "/exportXlsxById/40/42?export_type=3D").await,
        "example",
    )
    .await;

    let workbook = xlsx_entry_text(&bytes, "xl/workbook.xml");
    assert!(workbook.contains("数据报表"));
    let sheet_rels = xlsx_entry_text(&bytes, "xl/worksheets/_rels/sheet1.xml.rels");
    assert!(sheet_rels.contains("table"));
    let table = xlsx_entry_text(&bytes, "xl/tables/table1.xml");
    assert!(table.contains("TableStyleMedium9"));
    assert!(table.contains("autoFilter"));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_data_report_uses_python_table_style_medium_9 --test routes
```

Expected: FAIL if Rust currently writes rows without table XML/style metadata.

**Step 3: Write minimal implementation**

Extend the Rust XLSX builder to add:

- `xl/tables/table1.xml`
- `xl/worksheets/_rels/sheet1.xml.rels` relationship to the table
- worksheet `<tableParts count="1"><tablePart r:id="..."/></tableParts>`
- content type override for `/xl/tables/table1.xml`

The table range must match actual used data rows/columns.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_data_report_uses_python_table_style_medium_9 --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: mirror xlsx data table style"
```

### Task 2: Mirror Python wrap/center/vcenter cell style for defect image labels

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

Python `XlsxWriterFormatConfig.cell_format` sets `text_wrap`, horizontal center, and vertical center. `insert_image_and_name()` writes defect label text with that format.

```rust
#[tokio::test]
async fn xlsx_defect_image_labels_use_python_wrap_center_style() {
    let bytes = assert_xlsx_export_response(
        request_json_body(
            app_with_xlsx_actual_defect_row_seed_data(),
            "POST",
            "/export_xlsx",
            json!({
                "export_type": "3D",
                "detection_3d_info": true,
                "defect_info": true,
                "defect_show_info": true,
                "defect_un_show_info": false,
                "area_defect_image": false,
                "export_plc_data": false,
                "startDate": "202606270000",
                "endDate": "202606282359"
            }),
        )
        .await,
        "example",
    )
    .await;

    let styles = xlsx_entry_text(&bytes, "xl/styles.xml");
    assert!(styles.contains("wrapText=\"1\""));
    assert!(styles.contains("horizontal=\"center\""));
    assert!(styles.contains("vertical=\"center\""));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_defect_image_labels_use_python_wrap_center_style --test routes
```

Expected: FAIL if Rust does not emit the corresponding style/alignment.

**Step 3: Write minimal implementation**

Add a reusable style index for defect image label cells:

```xml
<alignment horizontal="center" vertical="center" wrapText="1"/>
```

Apply it only to the text cells that correspond to Python `insert_image_and_name()` label cells.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_defect_image_labels_use_python_wrap_center_style --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: style xlsx defect labels"
```

### Task 3: Emit Python-compatible defect-image row heights and image columns

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

Python `insert_image_and_name()` uses `worksheet.set_row(row_num, 150)` and `worksheet.set_column(index + 1, index + 1, 25)`.

```rust
#[tokio::test]
async fn xlsx_defect_image_sheet_uses_python_row_height_and_image_column_width() {
    let bytes = assert_xlsx_export_response(
        request_response(app_with_xlsx_actual_defect_row_seed_data(), "GET", "/exportXlsxById/40/42?export_type=3D").await,
        "example",
    )
    .await;

    let sheet = xlsx_entry_text(&bytes, "xl/worksheets/sheet2.xml");
    assert!(sheet.contains("ht=\"150\""));
    assert!(sheet.contains("customHeight=\"1\""));
    assert!(sheet.contains("width=\"25\""));
    assert!(sheet.contains("customWidth=\"1\""));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_defect_image_sheet_uses_python_row_height_and_image_column_width --test routes
```

Expected: FAIL if row/column dimensions are not emitted.

**Step 3: Write minimal implementation**

For each defect-image sheet:

- Set `ht="150"` and `customHeight="1"` on rows containing exported defect image cells.
- Add `<cols>` entries for image columns with `width="25"` and `customWidth="1"`.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_defect_image_sheet_uses_python_row_height_and_image_column_width --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: size xlsx defect image cells"
```

### Task 4: Embed 3D defect crop images into XLSX media/drawings

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Possibly modify: `app/Server/rust_api_service/src/data_config.rs`

**Step 1: Write the failing test**

Python `insert_image_and_name()` writes PNG image streams through `worksheet.insert_image(...)`. Add a Rust test that seeds a runtime image and a defect row, then verifies media and drawing package parts exist.

```rust
#[tokio::test]
async fn xlsx_3d_defect_sheet_embeds_png_media_and_drawing_relationships() {
    let app = app_with_xlsx_actual_defect_row_seed_data();
    let bytes = assert_xlsx_export_response(
        request_response(app, "GET", "/exportXlsxById/40/42?export_type=3D").await,
        "example",
    )
    .await;

    assert!(xlsx_has_entry(&bytes, "xl/media/image1.png"));
    assert!(xlsx_has_entry(&bytes, "xl/drawings/drawing1.xml"));
    let sheet_rels = xlsx_entry_text(&bytes, "xl/worksheets/_rels/sheet2.xml.rels");
    assert!(sheet_rels.contains("drawing"));
    let drawing_rels = xlsx_entry_text(&bytes, "xl/drawings/_rels/drawing1.xml.rels");
    assert!(drawing_rels.contains("../media/image1.png"));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_3d_defect_sheet_embeds_png_media_and_drawing_relationships --test routes
```

Expected: FAIL until Rust emits real XLSX drawing/media parts.

**Step 3: Write minimal implementation**

Implement image insertion for 3D defect sheets:

- Resolve the source/crop image the same way existing Rust image endpoints resolve defect crops where possible.
- Encode the inserted crop as PNG.
- Add `/xl/media/imageN.png`.
- Add drawing XML with a two-cell or one-cell anchor near the label/image column.
- Add worksheet drawing relationship.
- Add drawing-to-media relationship.
- Add content type override/default for PNG and drawings.

Keep missing-image behavior Python-compatible: skip the defect image insertion but keep the row text and do not fail the export.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_3d_defect_sheet_embeds_png_media_and_drawing_relationships --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/data_config.rs
git commit -m "api: embed xlsx defect images"
```

### Task 5: Embed 2D AREA defect overview images when `area_defect_image=true`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

Python `_insert_area_defect_image()` inserts `area_defects.png` with `object_position=1`, scale 1, and a PNG stream.

```rust
#[tokio::test]
async fn xlsx_2d_area_sheet_embeds_area_defect_png_when_enabled() {
    let bytes = assert_xlsx_export_response(
        request_json_body(
            app_with_2d_xlsx_seed_data(),
            "POST",
            "/export_xlsx",
            json!({
                "export_type": "3D",
                "detection_3d_info": true,
                "defect_info": true,
                "defect_show_info": false,
                "defect_un_show_info": false,
                "area_defect_image": true,
                "export_plc_data": false,
                "startDate": "202606270000",
                "endDate": "202606282359"
            }),
        )
        .await,
        "example",
    )
    .await;

    assert!(xlsx_has_entry(&bytes, "xl/media/image1.png"));
    let workbook = xlsx_entry_text(&bytes, "xl/workbook.xml");
    assert!(workbook.contains("缺陷识别_2D"));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_2d_area_sheet_embeds_area_defect_png_when_enabled --test routes
```

Expected: FAIL until Rust inserts 2D AREA images.

**Step 3: Write minimal implementation**

For AREA/2D defect sheets:

- Build or reuse the current AREA defect overview image used by Rust image routes.
- Insert it as PNG media/drawing into the 2D worksheet.
- Keep sheet omission behavior unchanged when `area_defect_image=false`.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_2d_area_sheet_embeds_area_defect_png_when_enabled --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: embed xlsx area defect images"
```

### Task 6: Add a production workbook comparison harness

**Files:**
- Create: `scripts/compare_xlsx_exports.py`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the harness**

Create a script that compares two XLSX files at ZIP/XML level without requiring Excel:

```powershell
python scripts/compare_xlsx_exports.py --python python.xlsx --rust rust.xlsx
```

It should report:

- workbook sheet names/order
- worksheet row/column dimensions
- header row values
- table count and table style names
- drawing/media counts
- relationship targets
- shared string counts and selected text diffs

**Step 2: Add documented usage**

Document how to generate Python and Rust workbooks for the same ID/date range, then run the comparator.

**Step 3: Run only when authorized**

Do not run this script unless the user authorizes generating/reading XLSX files.

**Step 4: Commit**

```powershell
git add scripts/compare_xlsx_exports.py docs/rust-tauri-parity.md
git commit -m "infra: compare xlsx export packages"
```

### Task 7: Focused verification before changing status

**Files:**
- Modify only if verification exposes regressions.
- Read: `docs/rust-tauri-parity.md`

**Step 1: Run focused Rust XLSX tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test xlsx_ --test routes
```

Expected: PASS.

**Step 2: Optional live no-production-write smoke**

Only with explicit user authorization:

```powershell
Invoke-WebRequest http://127.0.0.1:5011/exportXlsxById/40/42?export_type=3D -OutFile rust.xlsx
```

Expected: XLSX opens as a valid workbook and contains `数据报表`, `缺陷识别_3D`, and optionally `缺陷识别_2D` depending on config/data.

**Step 3: Optional Python/Rust package comparison**

Only with explicit user authorization and same data source:

1. Generate Python workbook for the same range.
2. Generate Rust workbook for the same range.
3. Run `scripts/compare_xlsx_exports.py`.
4. Record remaining differences in `docs/rust-tauri-parity.md`.

Do not mark XLSX deep parity complete until table/style/media/drawing/package comparison passes for at least one populated 3D defect sample and one 2D AREA sample.
