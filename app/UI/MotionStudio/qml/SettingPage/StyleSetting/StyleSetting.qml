pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var style
    clip: true

    readonly property var themeKeys: ["dark", "light", "blue"]
    readonly property var displayStyleKeys: ["standard", "compact", "comfortable"]

    ColumnLayout {
        width: root.availableWidth
        spacing: 14
        anchors.margins: 20

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
        }

        Section {
            title: qsTr("主题调试")

            GridLayout {
                columns: 3
                columnSpacing: 12
                rowSpacing: 12
                Layout.fillWidth: true

                Repeater {
                    model: root.themeKeys

                    ThemeTile {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                    }
                }
            }
        }

        Section {
            title: qsTr("显示风格")

            GridLayout {
                columns: 3
                columnSpacing: 12
                rowSpacing: 12
                Layout.fillWidth: true

                Repeater {
                    model: root.displayStyleKeys

                    DisplayStyleTile {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 104
                    }
                }
            }
        }

        Section {
            title: qsTr("当前令牌")

            GridLayout {
                columns: 2
                columnSpacing: 18
                rowSpacing: 12
                Layout.fillWidth: true

                TokenPreview {
                    title: qsTr("应用背景")
                    value: root.style.appBackgroundColor
                    colorValue: root.style.appBackgroundColor
                }
                TokenPreview {
                    title: qsTr("面板背景")
                    value: root.style.panelBackgroundColor
                    colorValue: root.style.panelBackgroundColor
                }
                TokenPreview {
                    title: qsTr("标题高亮")
                    value: root.style.titleColor
                    colorValue: root.style.titleColor
                }
                TokenPreview {
                    title: qsTr("选中状态")
                    value: root.style.selectionColor
                    colorValue: root.style.selectionColor
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 78
                color: root.style.panelBackgroundColor
                border.color: root.style.headerBorderColor
                border.width: 1
                radius: root.style.controlRadius

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: 96
                        Layout.fillHeight: true
                        color: root.style.headerBackgroundColor
                        border.color: root.style.titleColor
                        border.width: 1
                        radius: root.style.controlRadius
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: root.style.themes[root.style.themeName].name
                                  + " / "
                                  + root.style.displayStyles[
                                      root.style.displayStyleName].name
                            color: root.style.titleColor
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: qsTr("顶部高度 %1，窗口按钮宽度 %2，圆角 %3")
                                  .arg(root.style.topHeight)
                                  .arg(root.style.windowButtonWidth)
                                  .arg(root.style.controlRadius)
                            color: root.style.labelColor
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
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
                spacing: 12
            }
        }
    }

    component ThemeTile: Button {
        id: themeTile
        required property string modelData
        readonly property string themeKey: modelData
        readonly property var themeInfo: root.style.themes[themeKey]
        readonly property bool selected: root.style.themeName === themeKey

        checkable: true
        checked: selected
        text: themeInfo.name
        padding: 0

        background: Rectangle {
            color: themeTile.selected
                   ? root.style.selectionColor : root.style.panelBackgroundColor
            border.color: themeTile.selected
                          ? root.style.titleColor : root.style.headerBorderColor
            border.width: themeTile.selected ? 2 : 1
            radius: root.style.controlRadius
        }

        contentItem: ColumnLayout {
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.topMargin: 10
                spacing: 8

                Label {
                    text: themeTile.themeInfo.name
                    color: root.style.textColor
                    font.pixelSize: 14
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Label {
                    text: themeTile.selected ? qsTr("当前") : qsTr("切换")
                    color: themeTile.selected
                           ? root.style.titleColor : root.style.labelColor
                    font.pixelSize: 12
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                spacing: 7

                Swatch { swatchColor: themeTile.themeInfo.backgroundColor }
                Swatch { swatchColor: themeTile.themeInfo.panelColor || themeTile.themeInfo.itemBackColor || themeTile.themeInfo.backgroundColor }
                Swatch { swatchColor: themeTile.themeInfo.gridLineColor }
                Swatch { swatchColor: themeTile.themeInfo.selectionColor || themeTile.themeInfo.gridLineColor }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.preferredHeight: 26
                color: themeTile.themeInfo.headerColor || themeTile.themeInfo.backgroundColor
                border.color: themeTile.selected
                              ? root.style.titleColor
                              : root.style.headerBorderColor
                border.width: 1
                radius: root.style.controlRadius

                Label {
                    anchors.centerIn: parent
                    text: themeTile.themeKey
                    color: themeTile.themeInfo.textColor
                    font.pixelSize: 12
                }
            }

            Item {
                Layout.fillHeight: true
            }
        }

        onClicked: root.style.applyTheme(themeTile.themeKey)
        ToolTip.visible: hovered
        ToolTip.text: qsTr("切换到 %1").arg(themeInfo.name)
    }

    component DisplayStyleTile: Button {
        id: styleTile
        required property string modelData
        readonly property string styleKey: modelData
        readonly property var styleInfo:
            root.style.displayStyles[styleKey]
        readonly property bool selected:
            root.style.displayStyleName === styleKey

        checkable: true
        checked: selected
        text: styleInfo.name
        padding: 0

        background: Rectangle {
            color: styleTile.selected
                   ? root.style.selectionColor : root.style.panelBackgroundColor
            border.color: styleTile.selected
                          ? root.style.titleColor : root.style.headerBorderColor
            border.width: styleTile.selected ? 2 : 1
            radius: root.style.controlRadius
        }

        contentItem: ColumnLayout {
            spacing: 8

            Label {
                text: styleTile.styleInfo.name
                color: root.style.textColor
                font.pixelSize: 15
                font.bold: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.topMargin: 10
                Layout.fillWidth: true
            }

            GridLayout {
                columns: 2
                columnSpacing: 10
                rowSpacing: 4
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12

                MetricLabel { text: qsTr("顶栏") }
                MetricValue { text: styleTile.styleInfo.topHeight + " px" }
                MetricLabel { text: qsTr("按钮") }
                MetricValue { text: styleTile.styleInfo.windowButtonWidth + " px" }
                MetricLabel { text: qsTr("标题") }
                MetricValue { text: styleTile.styleInfo.titleSize + " px" }
            }

            Item {
                Layout.fillHeight: true
            }
        }

        onClicked: root.style.applyDisplayStyle(styleTile.styleKey)
        ToolTip.visible: hovered
        ToolTip.text: qsTr("切换到 %1显示").arg(styleInfo.name)
    }

    component Swatch: Rectangle {
        property color swatchColor: root.style.panelBackgroundColor
        Layout.preferredWidth: 38
        Layout.preferredHeight: 18
        color: swatchColor
        border.color: root.style.headerBorderColor
        border.width: 1
        radius: 2
    }

    component TokenPreview: Rectangle {
        id: tokenPreview
        property string title: ""
        property string value: ""
        property color colorValue: root.style.panelBackgroundColor

        Layout.fillWidth: true
        Layout.preferredHeight: 48
        color: root.style.panelBackgroundColor
        border.color: root.style.headerBorderColor
        border.width: 1
        radius: root.style.controlRadius

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            Rectangle {
                Layout.preferredWidth: 34
                Layout.preferredHeight: 24
                color: tokenPreview.colorValue
                border.color: root.style.headerBorderColor
                border.width: 1
                radius: 2
            }

            Label {
                text: tokenPreview.title
                color: root.style.labelColor
                font.pixelSize: 13
                Layout.preferredWidth: 84
            }

            Label {
                text: tokenPreview.value
                color: root.style.textColor
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
    }

    component MetricLabel: Label {
        color: root.style.labelColor
        font.pixelSize: 12
    }

    component MetricValue: Label {
        color: root.style.textColor
        font.pixelSize: 12
        font.bold: true
    }
}
