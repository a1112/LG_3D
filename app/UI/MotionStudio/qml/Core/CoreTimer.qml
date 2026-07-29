import QtQuick

Item {
    id: root

    property bool dataFlushBusy: false

    function flushData() {
        if (dataFlushBusy || !api || !coreModel) {
            return
        }
        if (app && app.init && app.init.isListLoading) {
            return
        }

        let lastId = coreModel.getLastCoilId()
        if (lastId <= 0) {
            return
        }

        dataFlushBusy = true
        api.getDataFlush(
                    Math.max(0, lastId - 3),
                    (result)=>{
                        try {
                            coreModel.updateData(JSON.parse(result))
                        } catch (e) {
                            console.log("data flush parse error", e)
                        }
                        dataFlushBusy = false
                    },
                    (error)=>{
                        console.log("data flush error", error)
                        dataFlushBusy = false
                    }
                )
    }

    Timer {
        id: dataFlushTimer
        interval: Math.max(1000, coreSetting.updataTime)
        repeat: true
        running: true
        onTriggered: root.flushData()
    }

    Timer {
        interval: 7000
        running: !coreModel.keepLatest
        repeat: true
        onTriggered: {
            coreModel.autoKeepTime += 1
            if (coreModel.autoKeepTime >= coreModel.autoKeepTimeMax) {
                coreModel.keepLatest = true
                coreModel.autoKeepTime = 0
            }
        }
    }
}
