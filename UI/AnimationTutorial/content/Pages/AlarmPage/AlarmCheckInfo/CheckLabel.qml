import QtQuick
import QtQuick.Controls

// 统计 判级别数据
Column {
    Row{
        spacing:2
        BaseLabel{

            text:leftCore.userErrCoilCount
            color:"red"
            ToolTip.text:"返修"

        }
        BaseLabel{
            text:leftCore.userUnowCoilCount
            color:"yellow"
            ToolTip.text:"未标注"

        }
        BaseLabel{
            text:leftCore.userOkCoilCount
            color:"green"
            ToolTip.text:"通过"
        }
        Item{
            width:5
            height:1
        }
    }
}
