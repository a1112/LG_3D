import QtQuick
import "../Model"
Item {
    id:root
    property var nowTime: new Date()
    Timer{
        interval:1000
        running:true
        repeat:true
        onTriggered:{
            root.nowTime = new Date()
        }
    }

property string appTitle: qsTr("涟钢热轧1580端面缺陷检测系统")

property bool developer_mode: app.coreSetting.testMode

property bool isLocal:app.api.apiConfig.hostname=="127.0.0.1"

    readonly property bool isLast:coilIndex==0
    property int coilIndex: 0
    onCoilIndexChanged: {
        flushListItem()
    }

    property CoilModel currentCoilModel: CoilModel {
    }

    function flushListItem(){
        let c_data = app.coreModel.currentCoilListModel.get(coilIndex)

        if (!c_data) {
            return
        }
        if (c_data.SecondaryCoilId === currentCoilModel.coilId) {
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
        coilIndex = index
        flushListItem()
    }

    property var allKey:["S","L"]
}
