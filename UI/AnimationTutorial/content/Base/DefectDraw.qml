import QtQuick 2.15
import "../Comp/CrossView"
Rectangle {
    id:drawView
    color: "#20000000"
    property bool selectCanView: true
    property alias containsMouse: mouse.containsMouse
    SelectItem{
        visible: selectCanView
        id:sel
    }
    BorderToolItem{
        width: sel.width
        height: sel.height
        x:sel.x
        y:sel.y
        checked:!selectCanView
    }
    CrossView{
        id:cross
        visible: mouse.containsMouse
        labelX: flick.contentX
        cross_x:mouse.mouseX
        cross_y:mouse.mouseY
    }
    MouseArea{
        id:mouse
        hoverEnabled: true
        cursorShape: Qt.TouchPointMoved
        anchors.fill: parent
        onPressed:{
            selectCanView=true
            sel.startX=mouse.x
            sel.startY=mouse.y
            sel.endX=mouse.x
            sel.endY=mouse.y
            defectViewState.selectRec=Qt.rect(sel.minX,sel.minY,sel.maxX,sel.maxY)
        }
        onPositionChanged: {
            if (selectCanView){
                sel.endX=mouse.x
                sel.endY=mouse.y
                defectViewState.selectRec=Qt.rect(sel.minX,sel.minY,sel.maxX,sel.maxY)
            }
        }
        onReleased: {
            selectCanView=false
        }
        onClicked: {
            if (hoveredDefectIndex>=0){ //单击某个缺陷
                showOtherView(hoveredDefectIndex)
            }
            else
                otherImageModel=0
        }
        onDoubleClicked: {
            if (hoveredDefectIndex>=0){ //双击某个缺陷
                oneDefectViewDialog.updata(hoveredDefectObj)
            }
        }
    }
//    Repeater{
//        model:defectViewModel
//        delegate: DefectItemDelegate{}
//    }
}

