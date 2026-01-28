import QtQuick
import QtQuick.Controls
import "../../Model/server"
Item {
    id:root
    property alias hoved :hh.hovered
    onHovedChanged: {
        if(hoved){
            grid.currentIndex = index
        }
    }
    scale: hoved?1.2:1
    Behavior on scale {NumberAnimation{duration: 450}}
    property DefectItemModel defectItem:DefectItemModel{}

    //visible: index>50//defectViewCore.controlCore.getShowName(defectItem.defectName)
    Item{
        anchors.centerIn: parent
        width: parent.width*0.9
        height: parent.height*0.9
        Image {
            width:parent.width
            height:parent.height
            id: image_name
            source: root.defectItem.defect_url
            fillMode:Image.PreserveAspectFit
        }
        // 缺陷名称和 coil_id 标签
        Column{
            anchors.top: parent.top
            anchors.left: parent.left
            spacing: 2
            Label{
                font.bold:true
                font.pointSize:12
                text:defectItem.defectName
                color:defectItem.defectColor
                background:Rectangle{
                    color:"#88000000"
                }
            }
            Label{
                font.pointSize:10
                text:"ID:" + defectItem.coilId
                color:"#FFFFFF"
                background:Rectangle{
                    color:"#88000000"
                }
            }
        }
    }

    // 悬停显示详细信息
    Rectangle {
        id: tooltip
        visible: hoved
        width: detailColumn.width + 16
        height: detailColumn.height + 16
        color: "#E8E8E8"
        border.color: "#666666"
        border.width: 1
        radius: 4
        z: 1000
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.top
        anchors.bottomMargin: 8

        Column {
            id: detailColumn
            anchors.centerIn: parent
            spacing: 4

            Label {
                font.bold: true
                font.pointSize: 12
                text: defectItem.defectName
                color: defectItem.defectColor
            }
            Label {
                font.pointSize: 10
                text: "Coil ID: " + defectItem.coilId
                color: "#333333"
            }
            Label {
                font.pointSize: 10
                text: "Surface: " + defectItem.surface
                color: "#333333"
            }
            Label {
                font.pointSize: 10
                text: "Level: " + defectItem.defectLevel
                color: "#333333"
            }
            Label {
                font.pointSize: 10
                text: "Position: (" + defectItem.defectX + ", " + defectItem.defectY + ")"
                color: "#333333"
            }
            Label {
                font.pointSize: 10
                text: "Size: " + defectItem.defectW + " x " + defectItem.defectH
                color: "#333333"
            }
        }
    }

    Component.onCompleted:{
        defectItem.init(defectCoreModel.defectsModel.get(index))
    }

    HoverHandler{
        id:hh
    }

    MouseArea{
        id:mou
        anchors.fill: parent
        acceptedButtons: Qt.RightButton|Qt.LeftButton
        onClicked: (mouse) => {
                       if (mouse.button===Qt.RightButton){
                           // 将当前缺陷项传递给菜单
                           defectDataViewMenu.defectItem = defectItem
                           defectDataViewMenu.popup()
                       }

                   }
    }
}
