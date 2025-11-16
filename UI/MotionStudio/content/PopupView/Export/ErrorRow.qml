import QtQuick

import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"

RowLayout{
    id:root
    Layout.fillWidth: true
    property string errorStr:""
    spacing: 10
    Item{
        Layout.fillWidth: true
        implicitHeight: 1
    }
    BaseLabel{
        text:"数据导出错误："
    }
    BaseLabel{
        text: root.errorStr
        color:Material.color(Material.Red)
    }
    Item{
        Layout.fillWidth: true
        implicitHeight: 1
    }
}
