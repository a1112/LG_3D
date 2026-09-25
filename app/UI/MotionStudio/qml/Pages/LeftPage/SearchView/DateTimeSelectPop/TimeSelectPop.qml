pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../../types"

BaseSelectPop {
    id: root
    width: 240
    height: 170

    required property DateTime dateTime

    Pane {
        anchors.fill: parent
        Material.background: root.style.panelElevatedColor
    }

    Row {
        id: row
        anchors.centerIn: parent

        Tumbler {
            id: hoursTumbler
            width: 60
            height: root.height
            model: 24
            currentIndex: root.dateTime.hour
            onCurrentIndexChanged: {
                if (moving) {
                    root.dateTime.setTime(currentIndex, root.dateTime.minute)
                }
            }

            delegate: Item {
                id: hourDelegate
                required property int modelData
                width: hoursTumbler.width
                height: hoursTumbler.height / hoursTumbler.visibleItemCount

                Label {
                    anchors.centerIn: parent
                    text: hourDelegate.modelData
                    opacity: 1.0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pointSize: 18
                    font.bold: true
                    color: hoursTumbler.currentIndex === hourDelegate.modelData
                           ? root.style.statusWarningColor
                           : root.style.textColor
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
            currentIndex: root.dateTime.minute
            onCurrentIndexChanged: {
                if (moving) {
                    root.dateTime.setTime(root.dateTime.hour, currentIndex)
                }
            }

            delegate: Item {
                id: minuteDelegate
                required property int modelData
                width: minutesTumbler.width
                height: minutesTumbler.height / minutesTumbler.visibleItemCount

                Label {
                    anchors.centerIn: parent
                    text: minuteDelegate.modelData
                    opacity: 1.0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pointSize: 18
                    font.bold: true
                    color: minutesTumbler.currentIndex === minuteDelegate.modelData
                           ? root.style.statusSuccessColor
                           : root.style.textColor
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
