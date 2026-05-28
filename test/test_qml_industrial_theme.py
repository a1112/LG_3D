import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOTION_STUDIO_ROOT = PROJECT_ROOT / "app" / "UI" / "MotionStudio"
QML_ROOT = MOTION_STUDIO_ROOT / "qml"


THEMED_SURFACE_FILES = [
    QML_ROOT / "App.qml",
    QML_ROOT / "AppBase.qml",
    QML_ROOT / "MainLayout.qml",
    QML_ROOT / "Core" / "CoreStyle.qml",
    QML_ROOT / "Comp" / "Card" / "CardBase.qml",
    QML_ROOT / "Pages" / "Header" / "TopHeader.qml",
    QML_ROOT / "Pages" / "Header" / "TopTabBar.qml",
    QML_ROOT / "Pages" / "Header" / "CheckRec.qml",
    QML_ROOT / "Pages" / "LeftPage" / "LeftPageView.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "DataListView.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "DataListViewItenBase.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "ListTitleView.qml",
    QML_ROOT / "DataShow" / "_base_" / "DataShowBackground.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "DataShowItemSelectView.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "CheckRecItem.qml",
    QML_ROOT / "DataShow" / "Header" / "View3DChangeItem.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "DataShowItem" / "ShowCharts" / "ChartHead.qml",
    QML_ROOT / "Style" / "StyleMenu.qml",
]


def read_qml(relative_path):
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def test_dark_theme_defines_industrial_solid_color_tokens():
    text = read_qml(Path("Core") / "CoreStyle.qml")

    assert 'name: "工业深色主题"' in text
    for token in (
        "appBackgroundColor",
        "panelBackgroundColor",
        "panelElevatedColor",
        "panelAlternateColor",
        "headerBackgroundColor",
        "headerBorderColor",
        "buttonHoverColor",
        "selectionColor",
    ):
        assert f"property color {token}" in text
        assert f"{token} =" in text


def test_main_window_and_layout_use_solid_theme_backgrounds():
    app_base = read_qml(Path("AppBase.qml"))
    app = read_qml(Path("App.qml"))
    main_layout = read_qml(Path("MainLayout.qml"))

    assert 'color: "transparent"' not in app_base
    assert 'color: "transparent"' not in app
    assert "color: coreStyle.appBackgroundColor" in app
    assert "color: coreStyle.appBackgroundColor" in main_layout
    assert "Material.background: coreStyle.panelBackgroundColor" in app


def test_primary_chrome_files_do_not_use_transparent_or_alpha_backgrounds():
    forbidden_patterns = [
        re.compile(r'color\s*:\s*"transparent"'),
        re.compile(r'color\s*:\s*"#00000000"', re.IGNORECASE),
        re.compile(r"rgba\s*\("),
        re.compile(r"opacity\s*:"),
    ]

    violations = []
    for path in THEMED_SURFACE_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern.search(text):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} matches {pattern.pattern}")

    assert violations == []


def test_style_menu_applies_complete_theme_presets():
    text = read_qml(Path("Style") / "StyleMenu.qml")

    assert 'coreStyle.applyTheme("dark")' in text
    assert 'coreStyle.applyTheme("light")' in text
    assert "coreStyle.isDark=true" not in text
    assert "coreStyle.isDark=false" not in text


def test_qml_resource_file_builds(tmp_path):
    rcc = PROJECT_ROOT / ".venv" / "Scripts" / "pyside6-rcc.exe"
    if not rcc.exists():
        rcc = PROJECT_ROOT / ".venv" / "Scripts" / "pyside6-rcc"
    output_file = tmp_path / "qml-test.rcc"

    completed = subprocess.run(
        [str(rcc), str(MOTION_STUDIO_ROOT / "qml.qrc"), "--binary", "-o", str(output_file)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_file.exists()
    assert output_file.stat().st_size > 0
