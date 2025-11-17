import QtQuick
import "Exception"
Item {
    id:root

    function  dialogLine(){
        var component = Qt.createComponent("Exception/LineGraph.qml")
        var button = component.createObject(component)


    }


    Component.onCompleted:{
    dialogLine()
    }
}
