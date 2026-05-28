import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "PopupView"
import "fonts"
ApplicationWindow {

    x:50
    y:50
    color: "#0B1117"
    flags: Qt.Window | Qt.FramelessWindowHint
   property PopManagement popManage

    Loader{
        anchors.fill:parent
        asynchronous:true
        sourceComponent:
        PopManagement{
            anchors.fill:parent
            // id:popManage

        }
        onLoaded:popManage = this.item
    }
    property LoadFont fonts :LoadFont{}
}
