import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var apiClient
    required property var style
    required property var model
    required property var popupManager

    Layout.fillWidth: true
    implicitHeight: 30

    RowLayout {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            Layout.preferredWidth: connectionRow.implicitWidth + 16
            Layout.preferredHeight: 24
            radius: 12
            color: root.style.panelElevatedColor
            border.width: 1
            border.color: root.apiClient.connectColor

            RowLayout {
                id: connectionRow
                anchors.centerIn: parent
                spacing: 6

                Rectangle {
                    Layout.preferredWidth: 7
                    Layout.preferredHeight: 7
                    radius: 4
                    color: root.apiClient.connectColor
                }

                Label {
                    text: root.apiClient.connectionText
                    color: root.style.textColor
                    font.pixelSize: 12
                }

                Label {
                    visible: root.apiClient.connected
                    text: root.apiClient.delay + " ms"
                    color: root.style.labelColor
                    font.pixelSize: 12
                }
            }

            TapHandler {
                onTapped: root.popupManager.popupConnectDialog()
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.apiClient.apiConfig.hostname
            color: root.style.labelColor
            elide: Text.ElideMiddle
            font.pixelSize: 12
        }

        CheckDelegate {
            Layout.preferredHeight: 28
            text: qsTr("保持最新")
            checked: root.model.keepLatest
            onClicked: root.model.setKeepLatest(checked)
        }
    }
}
