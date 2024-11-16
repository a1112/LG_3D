import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "../Labels"
Rectangle{
    property int offsetX: 0
    property int offsetY: 0
    opacity: 0.9
    color: "#00000000"
    border.width: 2
    border.color: control.getColorById(defectID)
    x:boxX*currentImageScale+offsetX
    y:boxY*currentImageScale+offsetY
    width:boxW*currentImageScale
    height:boxH*currentImageScale
    LabelFootInfoKey{
        anchors.bottom: parent.top
        text: control.getNameById(defectID)
        color:Qt.lighter(control.getColorById(defectID))//Material.color(Material.Red)
    }

}
