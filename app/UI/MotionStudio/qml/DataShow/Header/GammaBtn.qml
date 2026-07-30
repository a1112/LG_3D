import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../Pages/Header"
Row {
    id: root

    required property var controller
    required property var style

    CheckRec{
        style: root.style
        visible:false
        height: 20
        text: "亮度"
        // visible: dataShowCore.image_is_gray
        checkColor: Material.color(Material.Red)
        onCheckedChanged:
            root.controller.adjustConfig.image_gamma_enable_btn = checked
        checked: root.controller.adjustConfig.image_gamma_enable_btn
    }
    Slider{
        visible: root.controller.adjustConfig.image_gamma_enable
        id:gammaSlider
        width:100
        height:20
            from: 0.3
            value: root.controller.adjustConfig.image_gamma
            onValueChanged: {
                root.controller.adjustConfig.image_gamma = gammaSlider.value
            }
            to: 1.3
            stepSize:0.05
    }
    Label{
        visible: root.controller.adjustConfig.image_gamma_enable
        height: 20
        text: gammaSlider.value.toFixed(2)
    }
}
