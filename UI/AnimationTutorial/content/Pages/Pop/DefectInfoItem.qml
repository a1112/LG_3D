import QtQuick
import QtQuick.Controls
Rectangle {
    height: 50
    property ListModel defectModel: ListModel{}

    property int currentCoilId:coilModel.coilId
    onCurrentCoilIdChanged: {
    //
        api.getDefects(coilModel.coilId)
    }

    ListView{
        anchors.fill: parent

    }
}
