pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

Item {
    id: root
    required property var controller
    required property var style

    component CaptionLabel: Label {
        color: root.style.secondaryTextColor
        font.pixelSize: 12
    }

    component ValueLabel: Label {
        color: root.style.textColor
        font.family: "Consolas"
        font.pixelSize: 12
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 10
        width: infoColumn.implicitWidth + 20
        height: infoColumn.implicitHeight + 16
        radius: root.style.controlRadius + 2
        color: root.style.infoOverlayColor
        border.color: root.style.infoOverlayBorderColor
        border.width: 1

        Column {
            id: infoColumn
            anchors.centerIn: parent
            spacing: 4

            Row {
                spacing: 6

                CaptionLabel {
                    text: qsTr("卷号")
                }

                ValueLabel {
                    text: root.controller.currentCoilModel && root.controller.currentCoilModel.coilNo
                          ? root.controller.currentCoilModel.coilNo
                          : root.controller.coilId
                    color: root.style.statusSuccessColor
                    font.bold: true
                }
            }

            Row {
                spacing: 14

                Row {
                    spacing: 4
                    CaptionLabel { text: "X" }
                    ValueLabel { text: root.controller.hoverPoint.x.toFixed(0) }
                }

                Row {
                    spacing: 4
                    CaptionLabel { text: "Y" }
                    ValueLabel { text: root.controller.hoverPoint.y.toFixed(0) }
                }
            }

            Row {
                spacing: 4
                CaptionLabel { text: qsTr("尺寸") }
                ValueLabel {
                    text: (root.controller.sourceWidth * root.controller.scan3dScaleX).toFixed(0)
                          + " × "
                          + (root.controller.sourceHeight * root.controller.scan3dScaleY).toFixed(0)
                }
                CaptionLabel { text: "mm" }
            }

            Row {
                spacing: 4
                CaptionLabel { text: qsTr("分辨率") }
                ValueLabel {
                    text: root.controller.sourceWidth + " × " + root.controller.sourceHeight
                }
                CaptionLabel { text: "px" }
            }
        }
    }
}
