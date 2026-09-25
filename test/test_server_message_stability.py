from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.ServerMsg import ServerMsg


def test_server_message_history_is_bounded_and_json_compatible(monkeypatch):
    monkeypatch.setenv("LG3D_SERVER_MESSAGE_HISTORY", "3")
    messages = ServerMsg()

    for index in range(5):
        messages.addMsg("state", index)

    assert messages.msgList == [
        ["state", 2],
        ["state", 3],
        ["state", 4],
    ]
    assert isinstance(messages.msgList, list)
    assert messages.getLastMsg() == ["state", 4]
    assert messages.getLastMsg("state") == 4
