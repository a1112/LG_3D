import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
ListView {
    id:roort
    clip: true
    orientation:ListView.Horizontal
    spacing: 5
    model:dataShowCore.defectModel
    ScrollBar.vertical:ScrollBar{}
    delegate:CropDefectShow{
            height:roort.height
    }

}
