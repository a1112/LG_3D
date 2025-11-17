import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout{
    property bool mm_label_visible: true
    property string title: "标题"
    Label{
        text: title
    }
    Item{
        height:30
        Layout.fillWidth: true
    TextField{
        anchors.fill: parent
        selectByMouse: true
    }
    }
    Label{
        id:lab
        visible:mm_label_visible
        text: "mm"
    color: "#747474"
    }

}




