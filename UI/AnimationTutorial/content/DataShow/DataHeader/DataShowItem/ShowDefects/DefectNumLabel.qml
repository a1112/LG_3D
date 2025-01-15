import QtQuick
import QtQuick.Controls
Label {
    //  显示缺陷数量
    property int defect_num:0

    text: "x "+defect_num
    font.bold:true
    font.family:"微软雅黑"
    font.pointSize:12
    color:"green"
}
