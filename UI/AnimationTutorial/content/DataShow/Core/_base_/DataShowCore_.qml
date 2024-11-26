import QtQuick
import "../"
Item {
    readonly property bool show_visible:surfaceData.show_visible    // 是否显示
    property CircleConfig circleConfig:CircleConfig{}   // 圆的参数

        property string errorScaleColor:"red"   // 超限制报警色
        property bool errorScaleSignal: false
        function setMaxErrorScale(col){
            errorScaleColor = col
            errorScaleSignal = true
        }
}
