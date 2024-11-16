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
        onPressed: {
            core3D.setMouseStart(mouse.x, mouse.y)
        }
        onPositionChanged: {
            core3D.setMouseMove(mouse.x, mouse.y)
        }
        onReleased: {
            core3D.setMouseEnd(mouse.x, mouse.y)
        }
    }
    Row{
        x:50
        spacing: 15
        DialItem{
            value: modelNode.eulerRotation.z
            onValueChanged:  modelNode.eulerRotation.z = value
        }
        Column{
            SliderItem{
                title:"X 旋转"
                width: 60
                value: modelNode.eulerRotation.x
                onValueChanged:  modelNode.eulerRotation.x = value
            }
            SliderItem{
                title:"Y 旋转"
                width: 60
                value: modelNode.eulerRotation.y
                onValueChanged:  modelNode.eulerRotation.y = value
            }
        }
    }
}
