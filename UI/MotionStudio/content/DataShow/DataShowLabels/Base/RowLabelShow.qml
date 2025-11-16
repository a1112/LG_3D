import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout{
    property alias text: lab.text
    property alias color: lab.color
    ValueLabel{
        id:lab
        Layout.fillWidth: true
    }
    Label{
        visible:mm_label_visible
        text: "mm"
    color: "#747474"
    }
}
