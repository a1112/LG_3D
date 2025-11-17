import QtQuick 2.15
import "../Labels"
DefecShowItemItem {

LabelFootInfoKey{
    visible:true
    anchors.top: parent.bottom
    text: "标注："+control.getNameById(defectID)
    color:Qt.lighter(control.getColorById(defectID))//Material.color(Material.Red)
}
}
