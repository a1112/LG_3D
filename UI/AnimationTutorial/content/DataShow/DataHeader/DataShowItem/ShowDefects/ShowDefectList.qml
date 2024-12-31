import QtQuick

import QtQuick.Controls
ListView {
    id:root
    clip: true
    orientation:ListView.Horizontal
    spacing: 5
    ScrollBar.vertical:ScrollBar{}
    delegate:CropDefectShow{


            height:root.height
            width:height
    }

}
