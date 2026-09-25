import QtQuick
import QtQuick.Controls
import "../../Base"
Row {
    id: root
    required property var controller
    height: 25

    LabelBase{
        text:"Z轴缩放"
    }

    Slider{
        from:0.1
        to:2
        stepSize:0.01
        value: root.controller.controls3D.scaleZ
        onMoved: root.controller.controls3D.scaleZ = value
        height:25
        width: 100
    }
    LabelBase{
        text: root.controller.controls3D.scaleZ.toFixed(2)
    }
}
