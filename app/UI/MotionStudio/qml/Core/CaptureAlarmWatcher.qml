import QtQuick

Item {
    id: root

    required property var apiClient
    required property var errorController
    required property var connectionState

    property int intervalMs: 10000
    property int alarmCode: 3001
    property bool requestRunning: false

    Timer {
        interval: root.intervalMs
        running: root.connectionState.connected
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    function setCaptureAlarm(hasError, message) {
        errorController._setGlobalError(alarmCode, message, hasError)
    }

    function refresh() {
        if (requestRunning || !connectionState.connected) {
            return false
        }
        requestRunning = true
        apiClient.getCameraAlarm(function(data) {
            requestRunning = false
            let payload
            try {
                payload = JSON.parse(data)
            } catch (error) {
                setCaptureAlarm(true, qsTr("采集报警数据解析失败"))
                return
            }

            let alarms = []
            for (let key in payload) {
                let item = payload[key] || {}
                let level = Number(item.level || 0)
                if (level > 1 || item.captureOk === false) {
                    alarms.push(key + ": " + (item.msg || qsTr("采集异常")))
                }
            }
            setCaptureAlarm(alarms.length > 0, alarms.join("；"))
        }, function() {
            requestRunning = false
            setCaptureAlarm(true, qsTr("采集服务连接失败"))
        })
        return true
    }
}
