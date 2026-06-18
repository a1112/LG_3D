import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def test_2d_export_crop_expands_40_pixels_on_each_side(monkeypatch):
    from Base.utils.export import export_image

    source_image = Image.new("RGB", (200, 200), "white")
    defect = SimpleNamespace(
        secondaryCoilId=123,
        surface="S",
        defectName="2D_EDGE",
        defectX=50,
        defectY=60,
        defectW=10,
        defectH=20,
    )

    monkeypatch.setattr(
        export_image,
        "_get_cached_source_image",
        lambda defect_, source_image_cache=None: source_image,
    )

    assert export_image._crop_margin_for_defect(
        defect) == export_image.AREA_2D_DEFECT_CROP_MARGIN_PX
    assert export_image._classifier_file_names(
        defect, export_image.AREA_2D_DEFECT_CROP_MARGIN_PX)[0].endswith(
            "_m40.png")

    cropped = export_image._crop_defect_image_cached(defect, {})

    # 2D defect (50, 60, 10, 20) expands to x=10..100 and y=20..120.
    assert cropped.size == (90, 100)


def test_2d_export_crop_clamps_40_pixel_margin_at_image_edges(monkeypatch):
    from Base.utils.export import export_image

    source_image = Image.new("RGB", (80, 70), "white")
    defect = SimpleNamespace(
        secondaryCoilId=456,
        surface="L",
        defectName="2D_EDGE",
        defectX=5,
        defectY=8,
        defectW=12,
        defectH=15,
    )

    monkeypatch.setattr(
        export_image,
        "_get_cached_source_image",
        lambda defect_, source_image_cache=None: source_image,
    )

    cropped = export_image._crop_defect_image_cached(defect, {})

    # The requested box would extend past the top-left edge, so it clamps to
    # x=0..57 and y=0..63 while still keeping the 40 px right/bottom margin.
    assert cropped.size == (57, 63)
