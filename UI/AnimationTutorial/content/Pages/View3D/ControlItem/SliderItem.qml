import QtQuick
import QtQuick.Controls
Column{
    property alias value: slid.value
    property alias title: title_id.text
Row{
    spacing: 20
    Label{
        id:title_id
        text: "X 旋转"
    }
     Label{
        text: slid.value.toFixed(0)
     }
}
        Slider {
            width: 120
            height: 20
            id:slid
            from: -45
            to: 45
        }

}
