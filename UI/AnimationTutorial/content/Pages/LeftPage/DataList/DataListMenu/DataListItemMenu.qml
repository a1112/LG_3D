import QtQuick
import QtQuick.Controls
import "../../../../Model"
import "../../../../Controls/Menu"
Menu{
    id:lefeListMemu
    property CoilModel coilModel
    MenuItem{
        text: "复制卷号"
        onClicked:{
            cpp.clipboard.setText(coilModel.coilNo)
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
                coreModel.surfaceS.openSaveFolderById(coilModel.coilId)
            }

        }
        MenuItem{
            text: "打开 L端 保存位置"
            onClicked: {
                coreModel.surfaceL.openSaveFolderById(coilModel.coilId)
            }
        }
        MenuSeparator{}
        Menu{
            title: qsTr("复制保存位置")
            MenuItem{
                text: qsTr("S端")
                onClicked: {
                     cpp.clipboard.setText(tool.url_to_str(coreModel.surfaceS.getBaseUrl(coilModel.coilId)+""))
                }
            }
            MenuItem{
                text: qsTr("L端")
                onClicked: {
                    cpp.clipboard.setText(tool.url_to_str(coreModel.surfaceL.getBaseUrl(coilModel.coilId)+""))
                }
            }
        }


    }
    Menu{
        title: "复制..."
        MenuItem{
            text: "卷号"
            onClicked:{
                cpp.clipboard.setText(coilModel.coilNo)
        }
        }

        MenuItem{
            text: "流水号"
            onClicked:{
                cpp.clipboard.setText(coilModel.coilId)
            }
        }

        MenuItem{
            text: "时间"
            onClicked:{
                cpp.clipboard.setText(coilModel.coilCreateTime.str)
            }

        }


        // MenuItem{
        //     text: "打开 S端 保存位置"
        //     onClicked: {
        //         Qt.openUrlExternally(coreModel.surfaceS.getBaseUrl(Id))
        //     }

        // }
        // MenuItem{
        //     text: "打开 L端 保存位置"
        //     onClicked: {
        //         Qt.openUrlExternally(coreModel.surfaceL.getBaseUrl(Id))
        //     }
        // }

    }

    Menu{
        title:qsTr("判断")

        SelectMenuItem{

                text: qsTr("返修")
                selectdColor:Material.color(Material.Red)
                selectd:coilModel.coilCheck.status == 2

        }
        SelectMenuItem{
                text: qsTr("未确认")
                selectdColor:Material.color(Material.Yellow)
                selectd:coilModel.coilCheck.status == 0
        }
        SelectMenuItem{
                    text: qsTr("通过")
                    selectdColor:Material.color(Material.Green)
                    selectd:coilModel.coilCheck.status == 1
        }
    }

    Menu{
        title:qsTr("工具")
        Menu{
                title:qsTr("分割小图")
                MenuItem{
                    text: qsTr("S端")
                    onClicked:{
                        api.clipMaxImage(coilModel.coilId,coreModel.surfaceS.key)
                        coreModel.surfaceS.openSaveFolderById(coilModel.coilId)
                    }
                }
                MenuItem{
                    text: qsTr("L端")
                    onClicked:{
                     api.clipMaxImage(coilModel.coilId,coreModel.surfaceL.key)
                        coreModel.surfaceL.openSaveFolderById(coilModel.coilId)
                    }
                }
        }
        MenuItem{
            text: "重新检测该卷"
        }
        MenuItem{
            text: "查看原始返回数据"
            onClicked:{
                Qt.openUrlExternally(api.getSearchByCoilIdUrl(coilModel.coilId))
            }
        }
    }

}
