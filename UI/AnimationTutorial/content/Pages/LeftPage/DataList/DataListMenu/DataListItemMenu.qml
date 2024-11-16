import QtQuick
import QtQuick.Controls
Menu{
    id:lefeListMemu
    MenuItem{
        text: "复制卷号"
        onClicked:{
            cpp.clipboard.setText(CoilNo)
        }
    }

    MenuItem{
        text: "标注"
    }
    Menu{
        title: "打开..."
        MenuItem{
            text: "打开 S端 保存位置"
            onClicked: {
                Qt.openUrlExternally(coreModel.surfaceS.getBaseUrl(Id))
            }

        }
        MenuItem{
            text: "打开 L端 保存位置"
            onClicked: {
                Qt.openUrlExternally(coreModel.surfaceL.getBaseUrl(Id))
                // Qt.openUrlExternally(coreModel.surfaceL.getBaseUrl(Id))
            }
        }
        MenuSeparator{}
        Menu{
            title: "复制保存位置"
            MenuItem{
                text: "S端"
                onClicked: {
                     cpp.clipboard.setText((coreModel.surfaceS.getBaseUrl(Id)+"").substring(8))
                }
            }
            MenuItem{
                text: "L端"
                onClicked: {
                    cpp.clipboard.setText((coreModel.surfaceL.getBaseUrl(Id)+"").substring(8))
                }
            }
        }


    }
    Menu{
        title: "复制..."
        MenuItem{
            text: "卷号"
            onClicked:{
                cpp.clipboard.setText(CoilNo)
        }
        }

        MenuItem{
            text: "流水号"
            onClicked:{
                cpp.clipboard.setText(Id)
            }
        }

        MenuItem{
            text: "时间"
            onClicked:{
                cpp.clipboard.setText(Qt.formatDateTime(new Date(CreateTime.year,CreateTime.month-1,CreateTime.day,CreateTime.hour,CreateTime.minute,CreateTime.second), "yyyy-MM-dd hh:mm:ss"))

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
    MenuItem{
        text: "查看原始返回数据"
        onClicked:{
            Qt.openUrlExternally(api.getSearchByCoilIdUrl(Id))
        }
    }
    MenuItem{
        text: "重新检测该卷"
    }
}
