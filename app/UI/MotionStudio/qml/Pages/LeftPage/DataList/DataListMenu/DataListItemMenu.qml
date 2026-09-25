import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../../Model"
import "../../../../Controls/Menu"
Menu{
    id: root
    required property var apiClient
    required property var modelStore
    required property var clipboardService
    required property var toolService
    required property var popupManager
    property CoilModel coilModel

    function copyText(value) {
        root.clipboardService.setText(value === undefined || value === null
                                      ? "" : String(value))
    }

    function selectedCoilId() {
        return root.coilModel ? root.coilModel.coilId : 0
    }

    MenuItem{
        text: "复制卷号"
        onClicked:{
            root.copyText(root.coilModel ? root.coilModel.coilNo : "")
        }
    }

    // MenuItem{
    //     text: "标注"
    // }
    Menu{
        title: "打开..."
        MenuItem{
            text: "打开 S端 保存位置"
            onClicked: {
                root.modelStore.surfaceS.openSaveFolderById(root.selectedCoilId())
            }

        }
        MenuItem{
            text: "打开 L端 保存位置"
            onClicked: {
                root.modelStore.surfaceL.openSaveFolderById(root.selectedCoilId())
            }
        }
        MenuSeparator{}
        Menu{
            title: qsTr("复制保存位置")
            MenuItem{
                text: qsTr("S端")
                onClicked: {
                    root.copyText(root.toolService.url_to_str(
                                      root.modelStore.surfaceS.getBaseUrl(root.selectedCoilId()) + ""))
                }
            }
            MenuItem{
                text: qsTr("L端")
                onClicked: {
                    root.copyText(root.toolService.url_to_str(
                                      root.modelStore.surfaceL.getBaseUrl(root.selectedCoilId()) + ""))
                }
            }
        }


    }
    Menu{
        title: "复制..."
        MenuItem{
            text: "卷号"
            onClicked:{
                root.copyText(root.coilModel ? root.coilModel.coilNo : "")
        }
        }

        MenuItem{
            text: "流水号"
            onClicked:{
                root.copyText(root.selectedCoilId())
            }
        }

        MenuItem{
            text: "时间"
            onClicked:{
                root.copyText(root.coilModel && root.coilModel.coilCreateTime
                              ? root.coilModel.coilCreateTime.str : "")
            }

        }
    }

    Menu{
        title:qsTr("判断")

        SelectMenuItem{

                text: qsTr("返修")
                selectdColor:Material.color(Material.Red)
                selectd:root.coilModel && root.coilModel.coilCheck
                         && root.coilModel.coilCheck.status === 2

        }
        SelectMenuItem{
                text: qsTr("未确认")
                selectdColor:Material.color(Material.Yellow)
                selectd:root.coilModel && root.coilModel.coilCheck
                         && root.coilModel.coilCheck.status === 0
        }
        SelectMenuItem{
                    text: qsTr("通过")
                    selectdColor:Material.color(Material.Green)
                selectd:root.coilModel && root.coilModel.coilCheck
                         && root.coilModel.coilCheck.status === 1
        }
    }

    Menu{
        title:qsTr("工具")
        Menu{
                title:qsTr("分割小图")
                MenuItem{
                    text: qsTr("S端")
                    onClicked:{
                        root.apiClient.clipMaxImage(root.selectedCoilId(),
                                                    root.modelStore.surfaceS.key)
                        root.modelStore.surfaceS.openSaveFolderById(root.selectedCoilId())
                    }
                }
                MenuItem{
                    text: qsTr("L端")
                    onClicked:{
                        root.apiClient.clipMaxImage(root.selectedCoilId(),
                                                    root.modelStore.surfaceL.key)
                        root.modelStore.surfaceL.openSaveFolderById(root.selectedCoilId())
                    }
                }
        }
        MenuItem{
            text: qsTr("重新拼接AREA图像")
            onClicked: {
                root.apiClient.rejoinArea(root.selectedCoilId())
            }
        }
        MenuItem{
            text: "重新检测该卷"
            onClicked: {
                // 打开重新识别窗口，仅针对当前卷
                const coilId = root.selectedCoilId()
                root.popupManager.popupReDetectionView(coilId, coilId)
            }
        }
        MenuItem{
            text: "全部重新识别"
            onClicked: {
                // 打开重新识别窗口，对当前列表所有卷
                root.popupManager.popupReDetectionView()
            }
        }
        MenuItem{
            text: "查看原始返回数据"
            onClicked:{
                Qt.openUrlExternally(
                            root.apiClient.getSearchByCoilIdUrl(root.selectedCoilId()))
            }
        }
    }

}
