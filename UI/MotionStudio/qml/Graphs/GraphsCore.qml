import QtQuick

Item {

    property int stratCoilId: 0
    property int endCoilId:0

    function init(){
        endCoilId=coreModel.getMaxCoilId()
        stratCoilId = coreModel.getMinCoilId()
    }

}
