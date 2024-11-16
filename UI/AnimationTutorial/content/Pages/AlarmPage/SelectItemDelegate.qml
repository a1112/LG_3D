import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

import "../../animation"

ItemDelegate {
        property alias titleText:lab.text
        property int alarmLevel:coreModel.coreGlobalError.errorLevelDict[titleText]
        property int level_:alarmLevel
    property color levelColor:
    {
        if (level_<=1){
            return Material.color(Material.Green)
        }
        if (level_==2){
            return Material.color(Material.Yellow)
        }
        if (level_==3){
            return Material.color(Material.Red)
        }
        return Material.color(Material.Grey)
                    }
        property bool checked_:false

    onClicked:{
        checked_ = !checked_

    }
    Row{
            anchors.centerIn: parent
            spacing: 5
            Label{
               horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                background: Rectangle{
                    color: coreStyle.backColor
                    border.width: 1
                }
                id:lab
                // text:key
                width: 50
                font.pixelSize: 18
                font.family: "Arial"
                font.bold:true
            }
            AnimRec{
                radius: 10
               running:level_>2
                width: 20
                height: 20
                color:levelColor
            }
        }

    Rectangle{
        visible:checked_
        width:parent.width
        height:parent.height
        color:"#00000000"
        border.width:2
        border.color:levelColor
    }
}
