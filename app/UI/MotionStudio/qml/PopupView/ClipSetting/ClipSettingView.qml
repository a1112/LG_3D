import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Base"

ApplicationWindow {
    id: root
    width: 720
    height: 560
    visible: false
    title: qsTr("裁剪设置")

    function openDialog() {
        visible = true
        raise()
        requestActivate()
    }

    function applySurfaceConfig(surfaceKey, mode, fixedValue, aValue, bValue, cValue) {
        api.setAreaClipConfig(
            surfaceKey,
            {
                mode: mode,
                fixed: fixedValue,
                a: aValue,
                b: bValue,
                c: cValue
            }
        )
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

            GroupBox {
                title: qsTr("S端")
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    RowLayout {
                        Label { text: qsTr("裁剪模式") }
                        RadioButton {
                            text: qsTr("固定")
                            checked: coreSetting.clipModeS === "fixed"
                            onClicked: coreSetting.clipModeS = "fixed"
                        }
                        RadioButton {
                            text: qsTr("动态")
                            checked: coreSetting.clipModeS === "dynamic"
                            onClicked: coreSetting.clipModeS = "dynamic"
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeS === "fixed"
                        Label { text: qsTr("固定裁剪值") }
                        SpinBox {
                            from: 0
                            to: 10000
                            value: coreSetting.clipFixedValueS
                            onValueChanged: coreSetting.clipFixedValueS = value
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeS === "dynamic"
                        Label { text: qsTr("基础距离(c)") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicCS.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicCS = v
                                } else {
                                    text = coreSetting.clipDynamicCS.toString()
                                }
                            }
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeS === "dynamic"
                        Label { text: qsTr("一次方程 a") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicAS.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicAS = v
                                } else {
                                    text = coreSetting.clipDynamicAS.toString()
                                }
                            }
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeS === "dynamic"
                        Label { text: qsTr("一次方程 b") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicBS.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicBS = v
                                } else {
                                    text = coreSetting.clipDynamicBS.toString()
                                }
                            }
                        }
                    }

                    Label {
                        text: qsTr("公式: (x-c)*a+b")
                        color: coreStyle.textColor
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        Button {
                            text: qsTr("应用 S端")
                            onClicked: applySurfaceConfig(
                                           "S",
                                           coreSetting.clipModeS,
                                           coreSetting.clipFixedValueS,
                                           coreSetting.clipDynamicAS,
                                           coreSetting.clipDynamicBS,
                                           coreSetting.clipDynamicCS
                                       )
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("L端")
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    RowLayout {
                        Label { text: qsTr("裁剪模式") }
                        RadioButton {
                            text: qsTr("固定")
                            checked: coreSetting.clipModeL === "fixed"
                            onClicked: coreSetting.clipModeL = "fixed"
                        }
                        RadioButton {
                            text: qsTr("动态")
                            checked: coreSetting.clipModeL === "dynamic"
                            onClicked: coreSetting.clipModeL = "dynamic"
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeL === "fixed"
                        Label { text: qsTr("固定裁剪值") }
                        SpinBox {
                            from: 0
                            to: 10000
                            value: coreSetting.clipFixedValueL
                            onValueChanged: coreSetting.clipFixedValueL = value
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeL === "dynamic"
                        Label { text: qsTr("基础距离(c)") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicCL.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicCL = v
                                } else {
                                    text = coreSetting.clipDynamicCL.toString()
                                }
                            }
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeL === "dynamic"
                        Label { text: qsTr("一次方程 a") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicAL.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicAL = v
                                } else {
                                    text = coreSetting.clipDynamicAL.toString()
                                }
                            }
                        }
                    }

                    RowLayout {
                        enabled: coreSetting.clipModeL === "dynamic"
                        Label { text: qsTr("一次方程 b") }
                        TextField {
                            implicitWidth: 110
                            text: coreSetting.clipDynamicBL.toString()
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            validator: DoubleValidator { bottom: -100000; top: 100000; decimals: 3 }
                            onEditingFinished: {
                                var v = parseFloat(text)
                                if (!isNaN(v)) {
                                    coreSetting.clipDynamicBL = v
                                } else {
                                    text = coreSetting.clipDynamicBL.toString()
                                }
                            }
                        }
                    }

                    Label {
                        text: qsTr("公式: (x-c)*a+b")
                        color: coreStyle.textColor
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignRight
                        Button {
                            text: qsTr("应用 L端")
                            onClicked: applySurfaceConfig(
                                           "L",
                                           coreSetting.clipModeL,
                                           coreSetting.clipFixedValueL,
                                           coreSetting.clipDynamicAL,
                                           coreSetting.clipDynamicBL,
                                           coreSetting.clipDynamicCL
                                       )
                        }
                    }
                }
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
