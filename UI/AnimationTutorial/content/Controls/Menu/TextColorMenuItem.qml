import QtQuick
import QtQuick.Controls
import "../Rectange"
MenuItem{
    text:"前景色"
    property color selectedColor
    onTriggered:{
        colorDialog.selectedColor = selectedColor
        colorFunc=function(color){
            selectedColor=color
        }
        colorDialog.open()
    }
    ColorRec{
        anchors.right: parent.right
        height:parent.height
        recColor:selectedColor
    }
}
