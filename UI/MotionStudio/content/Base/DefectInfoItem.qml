import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Labels"
RowLayout{
    Rectangle{
        width: height
        height:0.12*dpi
        color:control.getColorById(defectID)
    }
TitleLabel{
    color:"#fff"
    text: control.getNameById(defectID)+" 数量: "+count
    Layout.alignment: Qt.AlignHCenter
}
}
