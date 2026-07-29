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


def test_2d_export_prefers_existing_classifier_crop_without_margin(
        monkeypatch, tmp_path):
    from Base.utils.export import export_image

    defect = SimpleNamespace(
        secondaryCoilId=789,
        surface="S",
        defectName="2D_SCRATCH",
        defectX=20,
        defectY=30,
        defectW=5,
        defectH=6,
    )
    classifier_dir = tmp_path / "classifier" / "2D_SCRATCH"
    classifier_dir.mkdir(parents=True)
    saved_crop_path = classifier_dir / "789_20_30_25_36.png"
    Image.new("RGB", (5, 6), "black").save(saved_crop_path)

    monkeypatch.setattr(
        export_image,
        "_classifier_dirs",
        lambda defect_, defect_name=None: [classifier_dir],
    )

    def fail_source_crop(defect_, source_image_cache=None):
        raise AssertionError("source image crop should not run")

    monkeypatch.setattr(export_image, "_crop_defect_image_cached",
                        fail_source_crop)

    image = export_image.get_pil_image_for_export(defect, {}, "2D_SCRATCH")

    try:
        assert image is not None
        assert image.size == (5, 6)
    finally:
        if image is not None:
            image.close()


def test_export_source_cache_evicts_and_closes_old_image(monkeypatch):
    from Base.utils.export import export_image

    created_copies = []

    class FakeImage:

        def __init__(self):
            self.closed = False

        def copy(self):
            copied = FakeImage()
            created_copies.append(copied)
            return copied

        def close(self):
            self.closed = True

    monkeypatch.setattr(export_image, "MAX_EXPORT_SOURCE_IMAGE_CACHE_ITEMS", 1)
    monkeypatch.setattr(export_image, "get_pil_image",
                        lambda *args, **kwargs: FakeImage())
    source_cache = {}
    first = SimpleNamespace(secondaryCoilId=1,
                            surface="S",
                            defectName="D")
    second = SimpleNamespace(secondaryCoilId=2,
                             surface="S",
                             defectName="D")

    first_cached = export_image._get_cached_source_image(first, source_cache)
    second_cached = export_image._get_cached_source_image(second, source_cache)

    assert first_cached.closed is True
    assert second_cached.closed is False
    assert len(source_cache) == 1
    export_image._close_source_image_cache(source_cache)
    assert second_cached.closed is True


def test_export_config_skips_images_when_defect_info_is_disabled():
    from Base.utils.export.export_config import ExportConfig

    request = SimpleNamespace(
        export_plc_data=False,
        detection_3d_info=True,
        defect_info=False,
        defect_show_info=True,
        defect_un_show_info=False,
        area_defect_image=True,
    )

    config = ExportConfig(request)

    assert config.export_defect_data is False
    assert config.export_defect_image is False
