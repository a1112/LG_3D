import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../Api"

/**
 * 标记缺陷导出对话框
 * 用于导出手动标注的缺陷图像
 */
Dialog {
    id: root
    title: "导出标记缺陷"
    modal: true
    width: 500
    height: 400

    // 属性
    property int coilId: 0
    property string surfaceKey: "S"
    property var defectsList: []

    // 信号
    signal exportCompleted(int exportedCount, int total)

    FolderDialog {
        id: folderDialog
        title: "选择导出目录"
        acceptLabel: "选择"
        rejectLabel: "取消"

        onAccepted: {
            exportPathInput.text = selectedFolder
        }
    }

    ColumnLayout {
        spacing: 15
        anchors.fill: parent

        // 导出范围选择
        GroupBox {
            title: "导出范围"
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 10
                anchors.fill: parent

                RadioButton {
                    id: allDefectsRadio
                    text: "导出所有缺陷（包括自动检测和手动标注）"
                    checked: true
                }

                RadioButton {
                    id: manualOnlyRadio
                    text: "仅导出手动标注的缺陷"
                }

                RadioButton {
                    id: selectedOnlyRadio
                    text: "导出选中的缺陷 (" + selectedCountLabel.text + " 个)"
                    enabled: selectedCount > 0
                }

                Label {
                    id: selectedCountLabel
                    text: "0"
                    visible: false
                }
            }
        }

        // 导出路径
        GroupBox {
            title: "导出路径"
            Layout.fillWidth: true

            RowLayout {
                spacing: 10
                anchors.fill: parent

                TextField {
                    id: exportPathInput
                    Layout.fillWidth: true
                    placeholderText: "选择导出目录..."
                    readOnly: true
                }

                Button {
                    text: "浏览..."
                    onClicked: folderDialog.open()
                }
            }
        }

        // 导出选项
        GroupBox {
            title: "导出选项"
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 10
                anchors.fill: parent

                CheckBox {
                    id: groupByCategoryCheck
                    text: "按缺陷类别分类到子文件夹"
                    checked: true
                }

                CheckBox {
                    id: includeInfoCheck
                    text: "生成缺陷清单 Excel 文件"
                    checked: true
                }

                CheckBox {
                    id: highQualityCheck
                    text: "导出高质量图像（原图）"
                    checked: false
                }
            }
        }

        // 按钮区域
        RowLayout {
            spacing: 10
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight

            Button {
                text: "取消"
                onClicked: root.close()
            }

            Button {
                text: "导出"
                highlighted: true
                enabled: exportPathInput.text.length > 0
                onClicked: {
                    startExport()
                }
            }
        }
    }

    // 进度对话框
    Dialog {
        id: progressDialog
        title: "正在导出..."
        modal: true
        closePolicy: Dialog.NoAutoClose
        anchors.centerIn: parent

        Column {
            spacing: 15

            ProgressBar {
                id: progressBar
                width: 300
                indeterminate: true
            }

            Label {
                id: progressLabel
                text: "正在准备导出..."
            }
        }

        buttons: Button {
            text: "后台运行"
            onClicked: progressDialog.close()
        }
    }

    // 开始导出
    function startExport() {
        progressDialog.open()

        // 准备导出数据
        let exportData = {
            defects: getDefectsToExport(),
            folder_path: exportPathInput.text,
            group_by_category: groupByCategoryCheck.checked,
            include_info: includeInfoCheck.checked,
            high_quality: highQualityCheck.checked
        }

        api.exportManualDefects(exportData,
            function(result) {
                progressDialog.close()
                console.log("导出成功:", result)
                exportCompleted(result.exported || 0, result.total || 0)

                // 显示结果对话框
                showResultDialog(result)
            },
            function(error) {
                progressDialog.close()
                console.error("导出失败:", error)
                showErrorDialog(error)
            }
        )
    }

    // 获取要导出的缺陷列表
    function getDefectsToExport() {
        if (allDefectsRadio.checked) {
            // 返回所有缺陷
            return defectsList
        } else if (manualOnlyRadio.checked) {
            // 仅返回手动标注的缺陷
            return defectsList.filter(function(d) {
                return d.type === "manual"
            })
        } else {
            // 返回选中的缺陷
            return getSelectedDefects()
        }
    }

    // 获取选中的缺陷
    function getSelectedDefects() {
        // 由外部设置选中状态
        return defectsList.filter(function(d) {
            return d.selected === true
        })
    }

    // 显示结果对话框
    function showResultDialog(result) {
        resultDialog.title = "导出完成"
        resultMessage.text = "成功导出 " + (result.exported || 0) + " 个缺陷图像\n" +
                            "共 " + (result.total || 0) + " 个缺陷\n" +
                            "分类: " + (result.categories || 0) + " 个"
        resultDialog.open()
    }

    // 显示错误对话框
    function showErrorDialog(error) {
        resultDialog.title = "导出失败"
        resultMessage.text = "导出过程中发生错误:\n" + JSON.stringify(error)
        resultDialog.open()
    }

    // 结果对话框
    Dialog {
        id: resultDialog
        title: "导出完成"
        modal: true
        anchors.centerIn: parent

        Label {
            id: resultMessage
            text: ""
        }

        buttons: Button {
            text: "确定"
            highlighted: true
            onClicked: resultDialog.close()
        }
    }

    // 设置选中缺陷数量
    function setSelectedCount(count) {
        selectedCountLabel.text = count.toString()
    }

    property int selectedCount: 0

    // 打开对话框并设置缺陷列表
    function openWithDefects(coilId, surfaceKey, defects) {
        root.coilId = coilId
        root.surfaceKey = surfaceKey
        root.defectsList = defects || []

        // 计算手动标注缺陷数量
        let manualCount = 0
        for (let i = 0; i < defects.length; i++) {
            if (defects[i].type === "manual") {
                manualCount++
            }
        }

        manualOnlyRadio.text = "仅导出手动标注的缺陷 (" + manualCount + " 个)"

        open()
    }
}
