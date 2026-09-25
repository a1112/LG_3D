import QtQuick

Item {
    id: root

    required property var modelStore

    property int stratCoilId: 0
    property int endCoilId:0

    function init(){
        root.endCoilId = root.modelStore.getMaxCoilId()
        root.stratCoilId = root.modelStore.getMinCoilId()
    }

}
