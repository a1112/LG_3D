import QtQuick

Item {
    id: root

    required property var apiClient
    required property var model
    required property var settings
    required property var initController
    required property var connectionState

    property bool dataFlushBusy: false
    property string lastDataFlushError: ""

    function flushData() {
        if (dataFlushBusy || !connectionState.connected || initController.isListLoading) {
            return false
        }

        var lastId = model.getLastCoilId()
        if (lastId <= 0) {
            return false
        }

        dataFlushBusy = true
        lastDataFlushError = ""
        apiClient.getDataFlush(Math.max(0, lastId - 3), function(result) {
            try {
                model.updateData(JSON.parse(result))
            } catch (error) {
                lastDataFlushError = "data refresh: " + error
                console.warn(lastDataFlushError)
            }
            dataFlushBusy = false
        }, function(error) {
            lastDataFlushError = "data refresh: " + error
            dataFlushBusy = false
        })
        return true
    }

    Timer {
        id: dataFlushTimer
        interval: Math.max(1000, root.settings.updataTime)
        repeat: true
        running: root.connectionState.connected
        onTriggered: root.flushData()
    }

    Timer {
        interval: 7000
        running: root.connectionState.connected && !root.model.keepLatest
        repeat: true
        onTriggered: {
            root.model.autoKeepTime += 1
            if (root.model.autoKeepTime >= root.model.autoKeepTimeMax) {
                root.model.keepLatest = true
                root.model.autoKeepTime = 0
            }
        }
    }
}
