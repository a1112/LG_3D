import QtQuick

import QtQuick.Controls
ListView {
    id:root
    clip: true
    orientation:ListView.Horizontal
    spacing: 5
    model:dataShowCore.defectModel
    ScrollBar.vertical:ScrollBar{}
    delegate:CropDefectShow{


            height:root.height
            width:height
    }

}
