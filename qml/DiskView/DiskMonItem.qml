import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Column{
        width: parent.width
        property ListModel delModel: ListModel{
        }
        function initDelModel(){
            delModel.clear()
            let delData = monitor.getDiskMonitorData(mountpoint)
            for (let i = 0; i < delData.length; i++) {
                delModel.append(delData[i])
            }
        }

Repeater {
    width: parent.width
    model: delModel
    delegate:DiskMonItemItem{}

}
Component.onCompleted: {
    initDelModel()
}

}
