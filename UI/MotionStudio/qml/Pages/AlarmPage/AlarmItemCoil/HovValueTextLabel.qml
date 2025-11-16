import QtQuick
import QtQuick.Controls.Material


    Label{
    property string toolTipText: ""
    property int show_level: 0
    font.pixelSize: 18
    color:show_level>=3?"red":show_level>=2?"yellow":show_level>=1?Material.color(Material.Green): coreStyle.isDark?"#eee":"black"
    horizontalAlignment: Text.AlignHCenter
    font.bold: true
        background: Rectangle {
            color: coreStyle.isDark?"black":"#eee"
            radius: 5
            // border.width:2


        }
    ItemDelegate{
        anchors.fill:parent
        ToolTip.visible:hovered && toolTipText
        ToolTip.text:toolTipText
    }
    }
