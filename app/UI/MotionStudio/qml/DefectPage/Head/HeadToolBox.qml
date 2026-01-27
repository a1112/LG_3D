import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs

Item{
    id:root
    height: 45
    Layout.fillWidth: true
    Pane{
        anchors.fill: parent
        Material.elevation: 6
    }
    RowLayout{
        anchors.fill: parent
        spacing: 10

            TabBar{

                Repeater{
                    id: list_view
                    model: ListModel{
                        ListElement{
                            label:"缺陷列表"
                        }
                    }
                    TabButton{
                        text: label
                        font.bold: true
                        onClicked: {
                            core.globalViewIndex = index
                        }
                    }
                }
            }


        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        TitleText{
            font.pixelSize: 20
            text: qsTr("缺陷数据分析")
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        CheckDelegate{
            text: qsTr("显示报警类别")
             implicitHeight: root.height-5

        }
        Button{
            icon.source: coreStyle.getIcon("uploading")
            text: qsTr("导出")
            implicitHeight: root.height-5
            enabled: surfaceData.serverIsLocal && defectViewCore.defectCoreModel.defectsModelAll.count > 0
            onClicked: {
                exportFolderDialog.open()
            }
        }

        Button{
            icon.source: coreStyle.getIcon("Flush_Dark")
            text: qsTr("刷新")
            implicitHeight: root.height-5
        }
        Item{
            width: 5
            Layout.fillHeight: true
        }

    }

    // 导出文件夹选择对话框
    FolderDialog {
        id: exportFolderDialog
        title: qsTr("选择导出文件夹")
        currentFolder: StandardPaths.standardLocations(StandardPaths.PicturesLocation)[0]
        onAccepted: {
            let folderPath = tool.url_to_str(selectedFolder)
            exportDefects(folderPath)
        }
    }

    // 导出缺陷函数 - 导出当前显示的所有缺陷
    function exportDefects(folderPath) {
        // 收集当前显示的所有缺陷数据
        let defectsList = []
        let defectsModel = defectViewCore.defectCoreModel.defectsModelAll

        console.log("defectsModelAll count:", defectsModel.count)

        for (let i = 0; i < defectsModel.count; i++) {
            let defect = defectsModel.get(i)
            if (defect) {
                // 确保字段名与后端 CoilDefect 模型一致
                defectsList.push({
                    "secondaryCoilId": defect.secondaryCoilId || defect.Id || 0,
                    "surface": defect.surface || "S",
                    "defectName": defect.defectName || "Unknown",
                    "defectX": defect.defectX || 0,
                    "defectY": defect.defectY || 0,
                    "defectW": defect.defectW || 100,
                    "defectH": defect.defectH || 100
                })
            }
        }

        if (defectsList.length === 0) {
            console.log("没有可导出的缺陷数据")
            return
        }

        console.log("开始导出缺陷，共", defectsList.length, "个")

        // 调用导出 API
        api.ajax.post(
            api.apiConfig.serverUrlDaaBase + "/export_defects",
            {
                folder_path: folderPath,
                defects: defectsList
            },
            function(resp) {
                let result = typeof resp === "string" ? JSON.parse(resp) : resp
                console.log("导出成功:", result.message)
            },
            function(err) {
                console.log("导出失败:", err)
            }
        )
    }

}
