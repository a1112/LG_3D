import QtQuick
import QtQuick.Controls
import "PopupView"
ApplicationWindow {
    x:50
    y:50
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
}
