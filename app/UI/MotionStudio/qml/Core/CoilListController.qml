import QtQuick

Item {
    id: root

    required property var apiClient
    required property var model
    required property var coreController

    property int limit: 80
    property int batchSize: 12
    property bool loading: false
    property bool refreshQueued: false
    property int generation: 0
    property var pendingData: []
    property int pendingIndex: 0
    property string lastError: ""

    readonly property int loadedCount: model && model.coilListModel
                                       ? model.coilListModel.count : 0

    signal refreshed(int count)
    signal failed(string message)

    Timer {
        id: appendTimer
        interval: 0
        repeat: true
        onTriggered: root._appendBatch()
    }

    function _normalizePayload(payload) {
        var value = payload && payload.value !== undefined ? payload.value : payload
        return Array.isArray(value) ? value : []
    }

    function _beginPopulate(data, requestGeneration) {
        if (requestGeneration !== generation) {
            return
        }
        model.coilListModel.clear()
        pendingData = _normalizePayload(data)
        pendingIndex = 0
        if (pendingData.length === 0) {
            _finishRefresh()
            return
        }
        appendTimer.start()
    }

    function _appendBatch() {
        if (!pendingData || pendingIndex >= pendingData.length) {
            appendTimer.stop()
            pendingData = []
            pendingIndex = 0
            if (model.coilListModel.count > 0) {
                coreController.setCoilIndex(0)
            }
            _finishRefresh()
            return
        }

        var endIndex = Math.min(pendingIndex + batchSize, pendingData.length)
        for (var index = pendingIndex; index < endIndex; index++) {
            model.coilListModel.append(pendingData[index])
        }
        pendingIndex = endIndex
    }

    function _finishRefresh() {
        loading = false
        refreshed(loadedCount)
        if (refreshQueued) {
            refreshQueued = false
            Qt.callLater(refresh)
        }
    }

    function refresh() {
        if (loading) {
            refreshQueued = true
            return false
        }

        loading = true
        lastError = ""
        generation += 1
        var requestGeneration = generation
        apiClient.getCoilList(limit, function(result) {
            if (requestGeneration !== generation) {
                return
            }
            try {
                _beginPopulate(JSON.parse(result), requestGeneration)
            } catch (error) {
                lastError = "coil list: " + error
                loading = false
                failed(lastError)
                if (refreshQueued) {
                    refreshQueued = false
                    Qt.callLater(refresh)
                }
            }
        }, function(error) {
            if (requestGeneration !== generation) {
                return
            }
            lastError = "coil list: " + error
            loading = false
            failed(lastError)
            if (refreshQueued) {
                refreshQueued = false
                Qt.callLater(refresh)
            }
        })
        return true
    }
}
