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
        Label{
            font.bold:true
            font.pointSize:12
            text:defectItem.defectName + root.x
            color:defectItem.defectColor
            background:Rectangle{
                color:"#88000000"
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
                           defectDataViewMenu.popup()
                       }

                   }
    }
}
