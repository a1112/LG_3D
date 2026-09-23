import QtQuick
import QtQuick.Window
import "../Model"
Item {
    id: root
    required property var appWindow
    required property var settings
    required property var apiClient
    required property var modelStore
    required property var initController
    required property var dataController
    required property var scriptLauncher
    required property var globalContext
    signal redetectionCompleted(int coilId)

    function refreshAfterRedetection(){
        root.dataController.refreshAfterRedetection()
    }

    Connections {
        target: root.dataController
        function onRedetectionCompleted(coilId) {
            root.redetectionCompleted(coilId)
        }
    }

    property var nowTime: new Date()
    Timer{
        interval: 1000
        running: root.appWindow.visibility !== Window.Minimized
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            root.nowTime = new Date()
        }
    }

property string appTitle: qsTr("热轧 1580 端面缺陷检测系统")

function scriptDeveloperMode() {
    if (!root.scriptLauncher || typeof root.scriptLauncher.developerMode !== "function") {
        return false
    }
    return root.scriptLauncher.developerMode()
}

property bool developer_mode: root.settings.testMode || root.scriptDeveloperMode()

property bool isLocal: root.apiClient.apiConfig.hostname === "127.0.0.1"

    readonly property bool isLast:coilIndex==0
    property int coilIndex: 0
    onCoilIndexChanged: {
        flushListItem()
    }

    property CoilModel currentCoilModel: CoilModel {
        globalContext: root.globalContext
        apiClient: root.apiClient
    }

    function flushListItem(){
        let model = root.modelStore.currentCoilListModel
        if (!model || model.count <= 0) {
            return
        }

        let safeIndex = Math.max(0, Math.min(coilIndex, model.count - 1))
        if (safeIndex !== coilIndex) {
            coilIndex = safeIndex
            return
        }

        let c_data = model.get(safeIndex)

        if (!c_data) {
            return
        }
        // Coil list rows use `Id`; checking only `SecondaryCoilId` made every
        // periodic /flush look like a coil switch.  That restarted data_has,
        // coilInfo, point-data and heightData loads for both surfaces.
        let nextCoilId = Number(c_data.Id !== undefined
                                ? c_data.Id : c_data.SecondaryCoilId)
        if (isFinite(nextCoilId) && nextCoilId > 0
                && nextCoilId === Number(currentCoilModel.coilId)) {
            return
        }
        currentCoilModel.init(c_data)
        root.dataController.init_data_has()
        // 使用 hasCoil 字段判断是否有检测数据（摘要表中的 HasCoil）
        if (c_data.hasCoil) {
            root.modelStore.surfaceL.hasData = true
            root.modelStore.surfaceS.hasData = true
        }
        else {
            root.modelStore.surfaceL.hasData = false
            root.modelStore.surfaceS.hasData = false
        }
        root.modelStore.surfaceS.setCoilId(currentCoilModel.coilId)
        root.modelStore.surfaceL.setCoilId(currentCoilModel.coilId)

    }

    function flushList() {
        root.initController.flushList()
    }

    function setCoilIndex(index) {
        let model = root.modelStore.currentCoilListModel
        if (!model || model.count <= 0) {
            return
        }

        let safeIndex = Math.max(0, Math.min(index, model.count - 1))
        if (coilIndex === safeIndex) {
            flushListItem()
            return
        }
        coilIndex = safeIndex
    }

    property var allKey:["S","L"]
}
