import QtQuick 2.15
import "../Model"
Item {

    property string appTitle: "涟钢热轧1580端面缺陷检测系统"

    property bool isLocal:app.api.apiConfig.hostname=="127.0.0.1"

    readonly property bool isLast:coilIndex==0
    property int coilIndex: 0
    onCoilIndexChanged: {
        let c_data = app.coreModel.currentCoilListModel.get(coilIndex)

        if (c_data.SecondaryCoilId===currentCoilModel.coilId) {
            return
        }
        currentCoilModel.init(c_data)
        if (currentCoilModel.coilStatus_L>=0) {
            coreModel.surfaceL.hasData = true
        }
        else {
            coreModel.surfaceL.hasData = false
        }
        if (currentCoilModel.coilStatus_S>=0) {
            coreModel.surfaceS.hasData = true
        }
        else {
            coreModel.surfaceS.hasData = false
        }
        coreModel.surfaceS.setCoilId(currentCoilModel.coilId)
        coreModel.surfaceL.setCoilId(currentCoilModel.coilId)
        coreModel.surfaceS.setCoilId(currentCoilModel.coilId)

    }

    property CoilModel currentCoilModel: CoilModel {
    }

    function flushList() {
        init.flushList()
    }

    function setCoilIndex(index) {
        coilIndex = index
    }

    property var allKey:["S","L"]
}
