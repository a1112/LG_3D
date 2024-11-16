import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import QtQuick.Layouts
import "../../../../types"
BaseSelectPop {
    width:240
    height:170
    id:root
    Pane{
        anchors.fill:parent
    }
    property DateTime dateTime
    Row {
        id: row
        anchors.centerIn:parent
        Tumbler {
            width: 60
            height:root.height
            id: hoursTumbler
            model: 24
            currentIndex:dateTime.hour
            onCurrentIndexChanged:dateTime.hour=currentIndex
            delegate :Label {
                text: modelData
                opacity: 1.0 - Math.abs(Tumbler.displacement) / (Tumbler.tumbler.visibleItemCount / 2)
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pointSize:18
                font.bold:true
                color:hoursTumbler.currentIndex==modelData?Material.color(Material.Orange):coreStyle.textColor
                font.family:"Roboto-Medium"
            }
        }
        Label {
            anchors.verticalCenter:parent.verticalCenter
            text: "点"
            font.pointSize:18
            font.bold:true
            font.family:"Roboto-Medium"
        }
        Tumbler {
            width: 60
            height:root.height
            id: minutesTumbler
            model: 60

            currentIndex:dateTime.minute
            onCurrentIndexChanged:dateTime.minute=currentIndex
            delegate :              Label {
                text: modelData
                opacity: 1.0 - Math.abs(Tumbler.displacement) / (Tumbler.tumbler.visibleItemCount / 2)
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pointSize:18
                font.bold:true
                color:minutesTumbler.currentIndex==modelData?Material.color(Material.Green):coreStyle.textColor
                font.family:"Roboto-Medium"


            }
        }
        Label {
            anchors.verticalCenter:parent.verticalCenter
            text: "分"
            font.pointSize:18
            font.bold:true
            font.family:"Roboto-Medium"



        }
    }


}
