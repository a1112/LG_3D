import QtQuick 2.15
import QtQuick.Controls
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
        recColor:selectedColor
    }
}
