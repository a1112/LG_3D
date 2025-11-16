import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../Base"
ItemDelegate{
    id:root
    property bool selected: false
    property alias source:image.source
    ToolTip.visible:root.hovered
    width:height
    height: parent.height

    Pane{
        width: parent.width
        height: parent.height
        Material.elevation: 3
    }
    Rectangle{
    visible: root.selected
    anchors.fill: parent
    border.width: 2
    border.color: Material.color(Material.accent)
    color:"#00000000"
    }
    EffectImage {
        scale:0.8
        width:parent.width
        height:parent.height
        id:image
    }

    MouseArea{
        anchors.fill:parent
        cursorShape: Qt.PointingHandCursor
        onClicked:{root.clicked()}
    }
}
