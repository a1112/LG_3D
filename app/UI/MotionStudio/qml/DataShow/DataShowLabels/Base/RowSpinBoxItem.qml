import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout{
    id:root
    property bool mm_label_visible: true
    property string title: "标题"
    property alias from: spin.from
    property alias to: spin.to
    property alias stepSize: spin.stepSize
    property alias value: spin.value
    Label{
        text: root.title
    }
    Item{
        implicitHeight: 28
        Layout.fillWidth: true
        SpinBox{
            scale: 0.9
            id:spin
            anchors.fill: parent
            editable: true
        }
    }
    Label{
        id:lab
        visible:root.mm_label_visible
        text: "mm"
        color: "#747474"
    }
}
