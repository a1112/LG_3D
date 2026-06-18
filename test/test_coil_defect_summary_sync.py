import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COIL_MODULE_PATH = (
    PROJECT_ROOT / "package" / "CoilDataBase" / "CoilDataBase" / "Coil.py"
)


def _load_coil_module(monkeypatch, events):
    package = ModuleType("CoilDataBase")
    package.__path__ = [str(COIL_MODULE_PATH.parent)]

    core = ModuleType("CoilDataBase.core")

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def add_all(self, rows):
            events.append(("add_all", rows))

        def commit(self):
            events.append(("commit", None))

    core.Session = FakeSession

    tool = ModuleType("CoilDataBase.tool")
    tool.add_obj = lambda obj: obj
    tool.to_dict = lambda obj: obj

    class DummyModel:
        CoilInside = object()
        CoilDia = object()
        Thickness = object()
        Width = object()
        secondaryCoilId = object()
        surface = object()

    model_names = [
        "SecondaryCoil",
        "Coil",
        "AlarmInfo",
        "CoilDefect",
        "CoilState",
        "CoilCheck",
        "PlcData",
        "ManualDefect",
        "DefectClassDict",
        "ServerDetectionError",
    ]
    models = ModuleType("CoilDataBase.models")
    models.__all__ = model_names
    for name in model_names:
        setattr(models, name, type(name, (DummyModel,), {}))

    monkeypatch.setitem(sys.modules, "CoilDataBase", package)
    monkeypatch.setitem(sys.modules, "CoilDataBase.core", core)
    monkeypatch.setitem(sys.modules, "CoilDataBase.tool", tool)
    monkeypatch.setitem(sys.modules, "CoilDataBase.models", models)

    spec = importlib.util.spec_from_file_location(
        "CoilDataBase.Coil_under_test", COIL_MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_add_defects_syncs_unique_coil_summaries_after_commit(monkeypatch):
    events = []
    coil_module = _load_coil_module(monkeypatch, events)
    monkeypatch.setattr(
        coil_module,
        "_create_coil_defect",
        lambda defect: SimpleNamespace(coil_id=defect["secondaryCoilId"]),
    )
    monkeypatch.setattr(
        coil_module,
        "_sync_summary_counts",
        lambda coil_ids: events.append(("sync", coil_ids)),
    )

    coil_module.add_defects(
        [
            {"secondaryCoilId": 30},
            {"secondaryCoilId": "20"},
            {"secondaryCoilId": 30},
        ]
    )

    assert events == [
        (
            "add_all",
            [
                SimpleNamespace(coil_id=30),
                SimpleNamespace(coil_id="20"),
                SimpleNamespace(coil_id=30),
            ],
        ),
        ("commit", None),
        ("sync", [20, 30]),
    ]


def test_add_defects_empty_list_skips_database_and_summary_sync(monkeypatch):
    events = []
    coil_module = _load_coil_module(monkeypatch, events)
    monkeypatch.setattr(
        coil_module,
        "_sync_summary_counts",
        lambda coil_ids: events.append(("sync", coil_ids)),
    )

    coil_module.add_defects([])

    assert events == []
