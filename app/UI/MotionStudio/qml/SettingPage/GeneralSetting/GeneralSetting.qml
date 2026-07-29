pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var settings
    required property var style
    clip: true

    ColumnLayout {
        width: root.availableWidth
        spacing: 14
        anchors.margins: 20

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
        }

        Section {
            title: qsTr("图像服务")

            GridLayout {
                columns: 3
                columnSpacing: 14
                rowSpacing: 10
                Layout.fillWidth: true

                FieldLabel { text: qsTr("后端") }
                ComboBox {
                    id: imageBackendBox
                    model: [qsTr("Python"), qsTr("Rust")]
                    currentIndex: root.settings.useRustImageServer ? 1 : 0
                    Layout.preferredWidth: 140
                    onActivated: root.settings.useRustImageServer
                                 = imageBackendBox.currentIndex === 1
                }
                HintLabel {
                    text: root.settings.useRustImageServer
                          ? qsTr("当前使用 Rust 图像服务")
                          : qsTr("当前使用 Python 图像服务")
                }
            }
        }

        Section {
            title: qsTr("Rust 测试服务")

            GridLayout {
                columns: 3
                columnSpacing: 14
                rowSpacing: 10
                Layout.fillWidth: true

                FieldLabel { text: qsTr("Rust API") }
                CheckBox {
                    id: rustTestServerCheckBox
                    text: qsTr("启用测试服务")
                    checked: root.settings.useRustTestServer
                    onToggled: root.settings.useRustTestServer
                               = rustTestServerCheckBox.checked
                }
                HintLabel {
                    text: root.settings.useRustTestServer
                          ? qsTr("已切换到 Rust API，用于联调测试")
                          : qsTr("默认使用 Python API")
                }
            }
        }

        Section {
            title: qsTr("AREA 瓦格")

            RowLayout {
                spacing: 14
                Layout.fillWidth: true

                FieldLabel { text: qsTr("初始分块") }
                SpinBox {
                    id: tileCountBox
                    from: 1
                    to: 10
                    value: root.settings.defaultAreaTileCount
                    Layout.preferredWidth: 120
                    onValueModified: root.settings.defaultAreaTileCount
                                     = tileCountBox.value
                }
                HintLabel {
                    text: qsTr("每边块数，默认 3；加载完成后按尺寸自动调整")
                    Layout.fillWidth: true
                }
            }
        }

        Section {
            title: qsTr("缓存与显示")

            ColumnLayout {
                spacing: 12
                Layout.fillWidth: true

                CheckBox {
                    id: enable1024CacheCheckBox
                    text: qsTr("启用 1024 缓存模式（falsecolor 缩略图）")
                    checked: root.settings.enable1024CacheMode
                    onToggled: root.settings.enable1024CacheMode
                               = enable1024CacheCheckBox.checked
                }

                CheckBox {
                    id: errorOverlayCheckBox
                    text: qsTr("显示叠加图层（塔形报警 Error 图层）")
                    checked: root.settings.showErrorOverlay
                    onToggled: root.settings.showErrorOverlay
                               = errorOverlayCheckBox.checked
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    component Section: Rectangle {
        id: section
        property string title: ""
        default property alias content: body.data

        Layout.fillWidth: true
        implicitHeight: sectionLayout.implicitHeight + 28
        color: root.style.panelElevatedColor
        border.color: root.style.headerBorderColor
        border.width: 1
        radius: root.style.controlRadius

        ColumnLayout {
            id: sectionLayout
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Label {
                text: section.title
                color: root.style.titleColor
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.style.headerBorderColor
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: 10
            }
        }
    }

    component FieldLabel: Label {
        color: root.style.labelColor
        font.pixelSize: 14
        Layout.alignment: Qt.AlignVCenter
        Layout.preferredWidth: 90
    }

    component HintLabel: Label {
        color: root.style.labelColor
        opacity: 0.76
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        Layout.alignment: Qt.AlignVCenter
        Layout.fillWidth: true
    }
}
