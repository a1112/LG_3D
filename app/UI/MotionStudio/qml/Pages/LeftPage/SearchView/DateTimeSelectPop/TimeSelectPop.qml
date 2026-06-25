import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import QtQuick.Layouts
import "../../../../types"

BaseSelectPop {
    id: root
    width: 240
    height: 170

    property DateTime dateTime

    Pane {
        anchors.fill: parent
    }

    Row {
        id: row
        anchors.centerIn: parent

        Tumbler {
            id: hoursTumbler
            width: 60
            height: root.height
            model: 24
            currentIndex: dateTime.hour
            onCurrentIndexChanged: {
                if (moving) {
                    dateTime.hour = currentIndex
                }
            }

            delegate: Item {
                id: hourDelegate
                width: hoursTumbler.width
                height: hoursTumbler.height / hoursTumbler.visibleItemCount

                Label {
                    anchors.centerIn: parent
                    text: modelData
                    opacity: 1.0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pointSize: 18
                    font.bold: true
                    color: hoursTumbler.currentIndex === modelData ? Material.color(Material.Orange) : coreStyle.textColor
                    font.family: "Roboto-Medium"
                }
            }
        }

        Label {
            anchors.verticalCenter: parent.verticalCenter
            text: "时"
            font.pointSize: 18
            font.bold: true
            font.family: "Roboto-Medium"
        }

        Tumbler {
            id: minutesTumbler
            width: 60
            height: root.height
            model: 60
            currentIndex: dateTime.minute
            onCurrentIndexChanged: {
                if (moving) {
                    dateTime.minute = currentIndex
                }
            }

            delegate: Item {
                id: minuteDelegate
                width: minutesTumbler.width
                height: minutesTumbler.height / minutesTumbler.visibleItemCount

                Label {
                    anchors.centerIn: parent
                    text: modelData
                    opacity: 1.0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pointSize: 18
                    font.bold: true
                    color: minutesTumbler.currentIndex === modelData ? Material.color(Material.Green) : coreStyle.textColor
                    font.family: "Roboto-Medium"
                }
            }
        }

        Label {
            anchors.verticalCenter: parent.verticalCenter
            text: "分"
            font.pointSize: 18
            font.bold: true
            font.family: "Roboto-Medium"
        }
    }
}
