import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
ListView {
    id:roort
    clip: true
    orientation:ListView.Horizontal
    model:dataShowCore.defectModel
    ScrollBar.vertical:ScrollBar{}
    delegate:CropDefectShow{
            height:roort.height
    }

}
