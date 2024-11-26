import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../btns"
import "../../Pages/Header"
Row {
    CheckRec{
        visible:false
        height: 20
        text: "亮度"
        // visible: dataShowCore.image_is_gray
        checkColor: Material.color(Material.Red)
        onCheckedChanged: dataShowCore.adjustConfig.image_gamma_enable_btn = checked
        checked: dataShowCore.adjustConfig.image_gamma_enable_btn
    }
    Slider{
        visible: dataShowCore.adjustConfig.image_gamma_enable
        id:gammaSlider
        width:100
        height:20
            from: 0.3
            value: dataShowCore.adjustConfig.image_gamma
            onValueChanged: {
                dataShowCore.adjustConfig.image_gamma = gammaSlider.value
            }
            to: 1.3
            stepSize:0.05
    }
    Label{
        visible: dataShowCore.adjustConfig.image_gamma_enable
        height: 20
        text: gammaSlider.value.toFixed(2)
    }
}
