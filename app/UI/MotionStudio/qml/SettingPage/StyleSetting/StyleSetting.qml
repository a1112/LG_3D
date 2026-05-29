import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
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
                        themeKey: modelData
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
                        styleKey: modelData
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
                    value: coreStyle.appBackgroundColor
                    colorValue: coreStyle.appBackgroundColor
                }
                TokenPreview {
                    title: qsTr("面板背景")
                    value: coreStyle.panelBackgroundColor
                    colorValue: coreStyle.panelBackgroundColor
                }
                TokenPreview {
                    title: qsTr("标题高亮")
                    value: coreStyle.titleColor
                    colorValue: coreStyle.titleColor
                }
                TokenPreview {
                    title: qsTr("选中状态")
                    value: coreStyle.selectionColor
                    colorValue: coreStyle.selectionColor
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 78
                color: coreStyle.panelBackgroundColor
                border.color: coreStyle.headerBorderColor
                border.width: 1
                radius: coreStyle.controlRadius

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: 96
                        Layout.fillHeight: true
                        color: coreStyle.headerBackgroundColor
                        border.color: coreStyle.titleColor
                        border.width: 1
                        radius: coreStyle.controlRadius
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: coreStyle.themes[coreStyle.themeName].name + " / " + coreStyle.displayStyles[coreStyle.displayStyleName].name
                            color: coreStyle.titleColor
                            font.pixelSize: 16
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        Label {
                            text: qsTr("顶部高度 %1，窗口按钮宽度 %2，圆角 %3")
                                  .arg(coreStyle.topHeight)
                                  .arg(coreStyle.windowButtonWidth)
                                  .arg(coreStyle.controlRadius)
                            color: coreStyle.labelColor
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
                spacing: 12
            }
        }
    }

    component ThemeTile: Button {
        id: themeTile
        property string themeKey: ""
        readonly property var themeInfo: coreStyle.themes[themeKey]
        readonly property bool selected: coreStyle.themeName === themeKey

        checkable: true
        checked: selected
        text: themeInfo.name
        padding: 0

        background: Rectangle {
            color: themeTile.selected ? coreStyle.selectionColor : coreStyle.panelBackgroundColor
            border.color: themeTile.selected ? coreStyle.titleColor : coreStyle.headerBorderColor
            border.width: themeTile.selected ? 2 : 1
            radius: coreStyle.controlRadius
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
                    color: coreStyle.textColor
                    font.pixelSize: 14
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Label {
                    text: themeTile.selected ? qsTr("当前") : qsTr("切换")
                    color: themeTile.selected ? coreStyle.titleColor : coreStyle.labelColor
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
                border.color: themeTile.selected ? coreStyle.titleColor : coreStyle.headerBorderColor
                border.width: 1
                radius: coreStyle.controlRadius

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

        onClicked: coreStyle.applyTheme(themeKey)
        ToolTip.visible: hovered
        ToolTip.text: qsTr("切换到 %1").arg(themeInfo.name)
    }

    component DisplayStyleTile: Button {
        id: styleTile
        property string styleKey: ""
        readonly property var styleInfo: coreStyle.displayStyles[styleKey]
        readonly property bool selected: coreStyle.displayStyleName === styleKey

        checkable: true
        checked: selected
        text: styleInfo.name
        padding: 0

        background: Rectangle {
            color: styleTile.selected ? coreStyle.selectionColor : coreStyle.panelBackgroundColor
            border.color: styleTile.selected ? coreStyle.titleColor : coreStyle.headerBorderColor
            border.width: styleTile.selected ? 2 : 1
            radius: coreStyle.controlRadius
        }

        contentItem: ColumnLayout {
            spacing: 8

            Label {
                text: styleTile.styleInfo.name
                color: coreStyle.textColor
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

        onClicked: coreStyle.applyDisplayStyle(styleKey)
        ToolTip.visible: hovered
        ToolTip.text: qsTr("切换到 %1显示").arg(styleInfo.name)
    }

    component Swatch: Rectangle {
        property color swatchColor: coreStyle.panelBackgroundColor
        Layout.preferredWidth: 38
        Layout.preferredHeight: 18
        color: swatchColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: 2
    }

    component TokenPreview: Rectangle {
        property string title: ""
        property string value: ""
        property color colorValue: coreStyle.panelBackgroundColor

        Layout.fillWidth: true
        Layout.preferredHeight: 48
        color: coreStyle.panelBackgroundColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: coreStyle.controlRadius

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            Rectangle {
                Layout.preferredWidth: 34
                Layout.preferredHeight: 24
                color: colorValue
                border.color: coreStyle.headerBorderColor
                border.width: 1
                radius: 2
            }

            Label {
                text: title
                color: coreStyle.labelColor
                font.pixelSize: 13
                Layout.preferredWidth: 84
            }

            Label {
                text: value
                color: coreStyle.textColor
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
    }

    component MetricLabel: Label {
        color: coreStyle.labelColor
        font.pixelSize: 12
    }

    component MetricValue: Label {
        color: coreStyle.textColor
        font.pixelSize: 12
        font.bold: true
    }
}
