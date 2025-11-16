import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "ControlItem"
Item {
    anchors.fill: parent
    // 缩放
    WheelHandler{
        // acceptedModifiers: Qt.NoModifier|Qt.ControlModifier|Qt.ShiftModifier
        onWheel: (wheel)=> {
                     if (wheel.modifiers & Qt.ControlModifier) {
                         if (wheel.angleDelta.y > 0) {
                             core3D.objectOffsetZ += 20
                         } else {
                             core3D.objectOffsetZ -= 20
                         }
                     }
                     else{
                         if (wheel.angleDelta.y > 0) {
                             core3D.objectOffsetZ += 20
                         } else {
                             core3D.objectOffsetZ -= 20
                         }
                     }
                 }
    }

    MouseArea{
        anchors.fill: parent
        acceptedButtons:Qt.RightButton
        onPressed: {
            core3D.setMouseMoveStart(mouse.x, mouse.y)
        }
        onPositionChanged: {
            core3D.setMouseMove(mouse.x, mouse.y)
        }
        onReleased: {
            core3D.setMouseMoveEnd(mouse.x, mouse.y)
        }
    }
    MouseArea{
        anchors.fill: parent
        acceptedButtons:Qt.LeftButton
        onPressed: {
            core3D.setMouseRotateStart(mouse.x, mouse.y)
        }
        onPositionChanged: {
            core3D.setMouseRotate(mouse.x, mouse.y)
        }
        onReleased: {
            core3D.setMouseRotateMoveEnd(mouse.x, mouse.y)
        }
    }


    Row{
        x:50
        spacing: 15
        DialItem{
            value: core3D.objectRotationZ
            onValueChanged:  core3D.objectRotationZ = value
        }
        Column{
            SliderItem{
                title:"X 旋转"
                width: 60
                value: core3D.objectRotationX
                onValueChanged:  core3D.objectRotationX = value
            }
            SliderItem{
                title:"Y 旋转"
                width: 60
                value: core3D.objectRotationY
                onValueChanged:  core3D.objectRotationY = value
            }
        }
    }
}
