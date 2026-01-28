import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Api"

/**
 * 手动标注缺陷编辑对话框
 * 用于编辑或删除已标注的缺陷
 */
Dialog {
    id: root
    title: "编辑缺陷标注"
    modal: true
    width: 450
    height: 400

    // 属性
    property var defectData: null
    property int defectId: 0
    property string defectType: "manual"  // "auto" 或 "manual"

    // 信号
    signal defectUpdated(var defect)
    signal defectDeleted(int defectId)

    function openForDefect(defect) {
        defectData = defect
        defectId = defect.Id
        defectType = defect.type || "manual"

        // 填充表单
        defectNameCombo.currentIndex = -1
        for (let i = 0; i < defectNameCombo.count; i++) {
            if (defectNameCombo.textAt(i) === defect.defectName) {
                defectNameCombo.currentIndex = i
                break
            }
        }

        xInput.text = defect.defectX.toString()
        yInput.text = defect.defectY.toString()
        wInput.text = defect.defectW.toString()
        hInput.text = defect.defectH.toString()
        remarkInput.text = defect.remark || ""
        annotatorLabel.text = "标注人: " + (defect.annotator || "系统用户")

        // 只有手动标注的缺陷才能编辑和删除
        editGroup.enabled = (defectType === "manual")
        deleteButton.enabled = (defectType === "manual")

        open()
    }

    ColumnLayout {
        spacing: 15
        anchors.fill: parent

        // 缺陷类型警告
        Label {
            visible: root.defectType === "auto"
            text: "⚠ 此为自动检测缺陷，无法编辑"
            color: "#FF9800"
            font.bold: true
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
        }

        GroupBox {
            id: editGroup
            title: "缺陷信息"
            Layout.fillWidth: true

            GridLayout {
                columns: 2
                columnSpacing: 10
                rowSpacing: 10
                anchors.fill: parent

                // 缺陷类型
                Label { text: "缺陷类型:"; font.bold: true }
                ComboBox {
                    id: defectNameCombo
                    Layout.fillWidth: true
                    model: global ? global.defectClassProperty.getDefectNameList() : []
                }

                // X坐标
                Label { text: "X 坐标:"; font.bold: true }
                TextField {
                    id: xInput
                    validator: IntValidator { bottom: 0 }
                    Layout.fillWidth: true
                }

                // Y坐标
                Label { text: "Y 坐标:"; font.bold: true }
                TextField {
                    id: yInput
                    validator: IntValidator { bottom: 0 }
                    Layout.fillWidth: true
                }

                // 宽度
                Label { text: "宽度:"; font.bold: true }
                TextField {
                    id: wInput
                    validator: IntValidator { bottom: 1 }
                    Layout.fillWidth: true
                }

                // 高度
                Label { text: "高度:"; font.bold: true }
                TextField {
                    id: hInput
                    validator: IntValidator { bottom: 1 }
                    Layout.fillWidth: true
                }

                // 备注
                Label {
                    text: "备注:"
                    font.bold: true
                    Layout.columnSpan: 2
                }
                TextField {
                    id: remarkInput
                    Layout.fillWidth: true
                    Layout.columnSpan: 2
                    placeholderText: "输入备注信息..."
                }
            }
        }

        // 标注人信息（只读）
        GroupBox {
            title: "标注信息"
            Layout.fillWidth: true

            Row {
                spacing: 10
                Label {
                    id: annotatorLabel
                    text: "标注人: 系统用户"
                }
            }
        }

        // 按钮区域
        RowLayout {
            spacing: 10
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight

            Button {
                id: deleteButton
                text: "删除缺陷"
                highlighted: true
                Layout.alignment: Qt.AlignLeft

                background: Rectangle {
                    color: deleteButton.pressed ? "#D32F2F" : "#F44336"
                    radius: 4
                    opacity: deleteButton.enabled ? 1 : 0.5
                }
                contentItem: Text {
                    text: deleteButton.text
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    deleteConfirmDialog.open()
                }
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "取消"
                onClicked: root.close()
            }

            Button {
                text: "保存"
                highlighted: true
                enabled: root.defectType === "manual"
                onClicked: {
                    saveDefect()
                }
            }
        }
    }

    // 删除确认对话框
    Dialog {
        id: deleteConfirmDialog
        title: "确认删除"
        modal: true
        anchors.centerIn: parent

        Label {
            text: "确定要删除此缺陷标注吗？\n此操作无法撤销。"
        }

        buttons: Row {
            spacing: 10
            layoutDirection: Qt.RightToLeft

            Button {
                text: "取消"
                onClicked: deleteConfirmDialog.close()
            }

            Button {
                text: "删除"
                highlighted: true
                background: Rectangle {
                    color: pressed ? "#D32F2F" : "#F44336"
                    radius: 4
                }
                contentItem: Text {
                    text: "删除"
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    deleteDefect()
                    deleteConfirmDialog.close()
                    root.close()
                }
            }
        }
    }

    // 保存缺陷
    function saveDefect() {
        let updateData = {
            defectName: defectNameCombo.currentText || "未知缺陷",
            defectX: parseInt(xInput.text) || 0,
            defectY: parseInt(yInput.text) || 0,
            defectW: parseInt(wInput.text) || 100,
            defectH: parseInt(hInput.text) || 100,
            remark: remarkInput.text
        }

        api.updateManualDefect(defectId, updateData,
            function(result) {
                console.log("更新缺陷成功:", result)
                defectUpdated(result)
                root.close()
            },
            function(error) {
                console.error("更新缺陷失败:", error)
            }
        )
    }

    // 删除缺陷
    function deleteDefect() {
        api.deleteManualDefect(defectId,
            function(result) {
                console.log("删除缺陷成功:", result)
                defectDeleted(defectId)
            },
            function(error) {
                console.error("删除缺陷失败:", error)
            }
        )
    }
}
