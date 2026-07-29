pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GroupBox {
    id: root

    required property var apiClient
    required property var settings
    required property var style
    required property string surfaceKey

    readonly property bool isSurfaceS: surfaceKey === "S"
    readonly property string clipMode:
        isSurfaceS ? settings.clipModeS : settings.clipModeL
    readonly property int fixedValue:
        isSurfaceS ? settings.clipFixedValueS : settings.clipFixedValueL
    property bool busy: false
    property string statusText: ""
    property bool lastActionSucceeded: true

    title: qsTr("%1端").arg(surfaceKey)
    Layout.fillWidth: true
    Layout.fillHeight: true

    function setMode(mode) {
        if (root.isSurfaceS) {
            root.settings.clipModeS = mode
        } else {
            root.settings.clipModeL = mode
        }
    }

    function dynamicValue(key) {
        if (root.isSurfaceS) {
            if (key === "a")
                return root.settings.clipDynamicAS
            if (key === "b")
                return root.settings.clipDynamicBS
            return root.settings.clipDynamicCS
        }
        if (key === "a")
            return root.settings.clipDynamicAL
        if (key === "b")
            return root.settings.clipDynamicBL
        return root.settings.clipDynamicCL
    }

    function setDynamicValue(key, value) {
        if (root.isSurfaceS) {
            if (key === "a")
                root.settings.clipDynamicAS = value
            else if (key === "b")
                root.settings.clipDynamicBS = value
            else
                root.settings.clipDynamicCS = value
            return
        }
        if (key === "a")
            root.settings.clipDynamicAL = value
        else if (key === "b")
            root.settings.clipDynamicBL = value
        else
            root.settings.clipDynamicCL = value
    }

    function setFixedValue(value) {
        if (root.isSurfaceS)
            root.settings.clipFixedValueS = value
        else
            root.settings.clipFixedValueL = value
    }

    function applyConfig() {
        if (root.busy)
            return
        root.busy = true
        root.statusText = qsTr("正在应用...")
        root.apiClient.setAreaClipConfig(
                    root.surfaceKey,
                    {
                        mode: root.clipMode,
                        fixed: root.fixedValue,
                        a: root.dynamicValue("a"),
                        b: root.dynamicValue("b"),
                        c: root.dynamicValue("c")
                    },
                    function() {
                        root.busy = false
                        root.lastActionSucceeded = true
                        root.statusText = qsTr("配置已应用")
                    },
                    function(error) {
                        root.busy = false
                        root.lastActionSucceeded = false
                        root.statusText =
                            qsTr("应用失败: %1").arg(String(error))
                    })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Label { text: qsTr("裁剪模式") }

            RadioButton {
                text: qsTr("固定")
                checked: root.clipMode === "fixed"
                onClicked: root.setMode("fixed")
            }

            RadioButton {
                text: qsTr("动态")
                checked: root.clipMode === "dynamic"
                onClicked: root.setMode("dynamic")
            }
        }

        RowLayout {
            enabled: root.clipMode === "fixed"

            Label {
                text: qsTr("固定裁剪值")
                Layout.preferredWidth: 118
            }

            SpinBox {
                from: 0
                to: 10000
                value: root.fixedValue
                onValueModified: root.setFixedValue(value)
            }
        }

        Repeater {
            model: [
                {key: "c", label: qsTr("基础距离 (c)")},
                {key: "a", label: qsTr("一次方程 a")},
                {key: "b", label: qsTr("一次方程 b")}
            ]

            RowLayout {
                id: dynamicRow
                required property var modelData
                enabled: root.clipMode === "dynamic"

                Label {
                    text: dynamicRow.modelData.label
                    Layout.preferredWidth: 118
                }

                TextField {
                    id: dynamicInput
                    implicitWidth: 130
                    text: root.dynamicValue(
                              dynamicRow.modelData.key).toString()
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    validator: DoubleValidator {
                        bottom: -100000
                        top: 100000
                        decimals: 3
                    }
                    onEditingFinished: {
                        let parsed = Number(dynamicInput.text)
                        if (isFinite(parsed)) {
                            root.setDynamicValue(
                                        dynamicRow.modelData.key, parsed)
                        } else {
                            dynamicInput.text =
                                root.dynamicValue(
                                    dynamicRow.modelData.key).toString()
                        }
                    }
                }
            }
        }

        Label {
            text: qsTr("公式: (x - c) × a + b")
            color: root.style.secondaryTextColor
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: root.statusText
                color: root.lastActionSucceeded
                       ? root.style.statusSuccessColor
                       : root.style.statusErrorColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Button {
                text: root.busy
                      ? qsTr("应用中...")
                      : qsTr("应用 %1端").arg(root.surfaceKey)
                enabled: !root.busy
                onClicked: root.applyConfig()
            }
        }
    }
}
