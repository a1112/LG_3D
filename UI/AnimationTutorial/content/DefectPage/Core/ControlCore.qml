import QtQuick
//  控制按钮
Item {
    property int app_index:app_core.appIndex
    onApp_indexChanged: flush_defects()

    property ListModel  currentListModel:  defectCoreModel.currentListModel

    function flush_defects(){


    }
}
