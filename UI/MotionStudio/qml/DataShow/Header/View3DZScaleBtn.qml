import QtQuick
import QtQuick.Controls
import "../../Base"
Row {
height: 25

LabelBase{
    text:"Z轴缩放"
}

Slider{
    from:0.1
    to:2
    stepSize:0.01
    value: dataShowCore.controls3D.scaleZ
    onValueChanged: dataShowCore.controls3D.scaleZ=value
    height:25
    width: 100
}
LabelBase{
    text:dataShowCore.controls3D.scaleZ.toFixed(2)
}
}
