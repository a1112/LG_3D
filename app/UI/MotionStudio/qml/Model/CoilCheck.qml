import QtQuick

Item {
    id: root

    property int coilId: 0
    property int status: 0
    property string msg: ""
    readonly property color statusColor:
        root.status === 0 ? "#00000000"
                          : root.status === 2 ? "red" : "green"

    function setStatus(nextStatus) {
        root.status = nextStatus
    }

    function setMsg(nextMessage) {
        root.msg = nextMessage
    }

    function init(source) {
        if (!source) {
            return
        }

        let count = typeof source.count === "number"
                    ? source.count
                    : typeof source.length === "number" ? source.length : 0
        for (let index = 0; index < count; index++) {
            let item = typeof source.get === "function"
                       ? source.get(index) : source[index]
            if (!item) {
                continue
            }
            root.coilId = item.secondaryCoilId || 0
            root.status = item.status || 0
            root.msg = item.msg || ""
        }
    }
}
