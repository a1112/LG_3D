import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Column{
        id: root
        width: parent.width
        property string diskMountpoint: ""
        property ListModel delModel: ListModel{
        }
        function initDelModel(){
            delModel.clear()
            let delData = monitor.getDiskMonitorData(root.diskMountpoint)
            for (let i = 0; i < delData.length; i++) {
                delModel.append(delData[i])
            }
        }

Repeater {
    width: parent.width
    model: delModel
    delegate:DiskMonItemItem{
        diskMountpoint: root.diskMountpoint
    }

}
Component.onCompleted: {
    initDelModel()
}

}
