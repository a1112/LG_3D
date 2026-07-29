pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

Item {
    id: root
    required property var dataController
    required property var areaController
    required property var surface
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
                spacing: 14

                Row {
                    spacing: 4
                    CaptionLabel { text: "X" }
                    ValueLabel { text: root.dataController.hoverPoint.x.toFixed(0) }
                }

                Row {
                    spacing: 4
                    CaptionLabel { text: "Y" }
                    ValueLabel { text: root.dataController.hoverPoint.y.toFixed(0) }
                }
            }

            Row {
                spacing: 4
                CaptionLabel { text: qsTr("尺寸") }
                ValueLabel {
                    text: (root.dataController.sourceWidth * root.surface.scan3dScaleX).toFixed(0)
                          + " × "
                          + (root.dataController.sourceHeight * root.surface.scan3dScaleY).toFixed(0)
                }
                CaptionLabel { text: "mm" }
            }

            Row {
                spacing: 4
                CaptionLabel { text: qsTr("分辨率") }
                ValueLabel {
                    text: root.areaController.sourceWidth + " × " + root.areaController.sourceHeight
                }
                CaptionLabel { text: "px" }
            }

            Row {
                spacing: 4
                visible: root.areaController.sourceWidth > 0 && root.areaController.sourceHeight > 0
                CaptionLabel { text: qsTr("瓦片") }
                ValueLabel {
                    text: Math.floor(root.areaController.sourceWidth / 3)
                          + " × "
                          + Math.floor(root.areaController.sourceHeight / 3)
                }
                CaptionLabel { text: "px" }
            }

            Row {
                spacing: 4
                visible: root.areaController.flick !== null
                CaptionLabel { text: qsTr("视口") }
                ValueLabel {
                    text: Math.round(root.areaController.flick.width)
                          + " × "
                          + Math.round(root.areaController.flick.height)
                }
                CaptionLabel { text: "px" }
            }
        }
    }
}
