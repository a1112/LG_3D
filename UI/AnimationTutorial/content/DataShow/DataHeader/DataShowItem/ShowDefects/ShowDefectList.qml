import QtQuick
import QtQuick.Controls
ListView {
    id:roort
    orientation:ListView.Horizontal
    model:dataShowCore.defectModel
    ScrollBar.vertical:
    ScrollBar{}
    delegate:
        CropDefectShow{
            height:roort.height
    }

}
