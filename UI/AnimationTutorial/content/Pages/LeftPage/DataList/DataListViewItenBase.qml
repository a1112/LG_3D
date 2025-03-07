import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "Core"
import "../../../Model"
Item {
    id:root
    width: 300
    height: 25
    visible:leftCore.fliterEnable? coilModel.checkDefectShow(leftCore.fliterDict) :true

    property bool isCurrentIndex: index == core.coilIndex
    property  CoilModel coilModel: CoilModel{}  // 数据
    Component.onCompleted:{
        coilModel.init(model)
    }

    // property CoilState coilState: CoilState{}

    property ListItemCoil listItemCoil:ListItemCoil{}

    Pane{
        Material.elevation: 7
        anchors.fill: parent
    }
    Rectangle {
        anchors.fill: parent
        color: "#32eeeeee"
        radius: 5
        visible: index%2==0
    }

    ItemDelegate{
        anchors.fill:parent
            onClicked: {
                core.setCoilIndex(index)
                coreModel.setKeepLatest(false)
            }
    }
    Rectangle {
        anchors.fill: parent
        color: "#00000000"
        radius: 5
        visible: root.isCurrentIndex
        border.color:"orange"
        border.width: 2
    }

    MouseArea{  //打开菜单
        acceptedButtons: Qt.RightButton
        anchors.fill: parent
        onClicked: {
            popManage.popupDataListItemMenu(coilModel)
        }
    }
    Rectangle{
        width: 3
        height: parent.height
        anchors.bottom: parent.bottom
        color: root.isCurrentIndex?"red":"#00000000"
    }
    HoverHandler{
        id:hov
        onHoveredChanged: {
            if(hovered){
                leftCore.hovedIndex = index
                // leftCore.leftMsg = msg
                leftCore.hovedCoilModel = coilModel
            }
        }
    }
}
