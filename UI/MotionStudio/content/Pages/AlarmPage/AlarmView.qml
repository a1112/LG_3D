import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
CardBase{
    id:root
    width: parent.width
    title: "报警"
content_body:
Item{
        height: 50
        width: parent.width
        Layout.fillWidth: true
        Layout.fillHeight: true
    GridView {
    id: gridView
    anchors.fill: parent
    cellWidth: gridView.width / 3
    cellHeight: 25
    model: coreModel.alarmModel
    delegate: ItemDelegate {
        width: gridView.cellWidth
        height: gridView.cellHeight
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
                text:key
                width: 50
                font.pixelSize: 18
                font.family: "Arial"
                font.bold:true
            }
            DropShadowRec{
                radius: 15
                width: 20
                height: 20
                color: {
                    if (level==1){
                        return Material.color(Material.Green)
                    }
                    if (level==2){
                        return Material.color(Material.Yellow)
                    }
                    if (level==3){
                        return Material.color(Material.Red)
                    }
                    return Material.color(Material.Grey)
                }
            }
        }
    }
}

}
}
