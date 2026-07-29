import QtQuick
import QtQuick.Window
import "../Model"
Item {
    id:root
    property var nowTime: new Date()
    Timer{
        interval: 1000
        running: app.visibility !== Window.Minimized
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            root.nowTime = new Date()
        }
    }

property string appTitle: qsTr("热轧 1580 端面缺陷检测系统")

function scriptDeveloperMode() {
    if (!ScriptLauncher || typeof ScriptLauncher.developerMode !== "function") {
        return false
    }
    return ScriptLauncher.developerMode()
}

property bool developer_mode: app.coreSetting.testMode || scriptDeveloperMode()

property bool isLocal:app.api.apiConfig.hostname=="127.0.0.1"

    readonly property bool isLast:coilIndex==0
    property int coilIndex: 0
    onCoilIndexChanged: {
        flushListItem()
    }

    property CoilModel currentCoilModel: CoilModel {
    }

    function flushListItem(){
        let model = app.coreModel.currentCoilListModel
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
        coreControl.init_data_has()
        // 使用 hasCoil 字段判断是否有检测数据（摘要表中的 HasCoil）
        if (c_data.hasCoil) {
            coreModel.surfaceL.hasData = true
            coreModel.surfaceS.hasData = true
        }
        else {
            coreModel.surfaceL.hasData = false
            coreModel.surfaceS.hasData = false
        }
        coreModel.surfaceS.setCoilId(currentCoilModel.coilId)
        coreModel.surfaceL.setCoilId(currentCoilModel.coilId)

    }

    function flushList() {
        init.flushList()
    }

    function setCoilIndex(index) {
        let model = app.coreModel.currentCoilListModel
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
