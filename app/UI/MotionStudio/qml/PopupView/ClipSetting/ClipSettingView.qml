import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Base"

ApplicationWindow {
    id: root

    required property var apiClient
    required property var settings
    required property var style

    width: 720
    height: 560
    visible: false
    title: qsTr("裁剪设置")
    color: style.appBackgroundColor

    function openDialog() {
        root.visible = true
        root.raise()
        root.requestActivate()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        TitleLabel {
            text: qsTr("裁剪设置")
        }

        TabBar {
            id: tabBar
            Layout.fillWidth: true
            TabButton { text: qsTr("S端") }
            TabButton { text: qsTr("L端") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            SurfaceClipSettings {
                apiClient: root.apiClient
                settings: root.settings
                style: root.style
                surfaceKey: "S"
            }

            SurfaceClipSettings {
                apiClient: root.apiClient
                settings: root.settings
                style: root.style
                surfaceKey: "L"
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: qsTr("关闭")
                onClicked: root.close()
            }
        }
    }
}
