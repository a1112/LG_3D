import QtQuick
import QtQuick.Controls

// 统计 判级别数据
Column {
    id: root

    required property var statsController

    Row{
        spacing:2
        BaseLabel{
            text: root.statsController.userErrCoilCount
            color:"red"
            ToolTip.text:"返修"
        }
        BaseLabel{
            text: root.statsController.userUnowCoilCount
            color:"yellow"
            ToolTip.text:"未标注"

        }
        BaseLabel{
            text: root.statsController.userOkCoilCount
            color:"green"
            ToolTip.text:"通过"
        }
        Item{
            width:5
            height:1
        }
    }
}
