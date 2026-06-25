import QtQuick

Item {
    id: root
    property int intervalMs: 10000
    property int alarmCode: 3001
    property bool requestRunning: false

    Timer {
        interval: root.intervalMs
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    function setCaptureAlarm(hasError, message) {
        if (app && app.coreModel && app.coreModel.coreGlobalError) {
            app.coreModel.coreGlobalError._setGlobalError(root.alarmCode, message, hasError)
        }
    }

    function refresh() {
        if (requestRunning || !app || !app.api) {
            return
        }
        requestRunning = true
        app.api.getCameraAlarm(function(data) {
            requestRunning = false
            let payload = {}
            try {
                payload = JSON.parse(data)
            } catch (e) {
                root.setCaptureAlarm(true, qsTr("采集报警数据解析失败"))
                return
            }

            let alarms = []
            for (let key in payload) {
                let item = payload[key] || {}
                let level = Number(item.level || 0)
                if (level > 1 || item.captureOk === false) {
                    let msg = item.msg || qsTr("采集异常")
                    alarms.push(key + ": " + msg)
                }
            }
            root.setCaptureAlarm(alarms.length > 0, alarms.join("；"))
        }, function(error) {
            requestRunning = false
            root.setCaptureAlarm(true, qsTr("采集服务连接失败"))
        })
    }
}
