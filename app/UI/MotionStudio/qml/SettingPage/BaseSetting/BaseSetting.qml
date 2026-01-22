import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
Item {
    property int index: 0

    Text{
        font.pointSize: 40
        text:"index:"+ parent.index
        color: "red"
        anchors.centerIn: parent
    }
}
