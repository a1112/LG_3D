import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
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
                    currentIndex: coreSetting.useRustImageServer ? 1 : 0
                    Layout.preferredWidth: 140
                    onActivated: coreSetting.useRustImageServer = currentIndex === 1
                }
                HintLabel {
                    text: coreSetting.useRustImageServer
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
                    checked: coreSetting.useRustTestServer
                    onToggled: coreSetting.useRustTestServer = checked
                }
                HintLabel {
                    text: coreSetting.useRustTestServer
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
                    value: coreSetting.defaultAreaTileCount
                    Layout.preferredWidth: 120
                    onValueChanged: coreSetting.defaultAreaTileCount = value
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
                    checked: coreSetting.enable1024CacheMode
                    onCheckedChanged: coreSetting.enable1024CacheMode = checked
                }

                CheckBox {
                    id: errorOverlayCheckBox
                    text: qsTr("显示叠加图层（塔形报警 Error 图层）")
                    checked: coreSetting.showErrorOverlay
                    onCheckedChanged: coreSetting.showErrorOverlay = checked
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
        color: coreStyle.panelElevatedColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: coreStyle.controlRadius

        ColumnLayout {
            id: sectionLayout
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Label {
                text: section.title
                color: coreStyle.titleColor
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: coreStyle.headerBorderColor
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: 10
            }
        }
    }

    component FieldLabel: Label {
        color: coreStyle.labelColor
        font.pixelSize: 14
        Layout.alignment: Qt.AlignVCenter
        Layout.preferredWidth: 90
    }

    component HintLabel: Label {
        color: coreStyle.labelColor
        opacity: 0.76
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        Layout.alignment: Qt.AlignVCenter
        Layout.fillWidth: true
    }
}
