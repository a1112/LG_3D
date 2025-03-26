import QtQuick

import QtQuick.Controls
ListView {
    id:root
    clip: true
    orientation:ListView.Horizontal
    spacing: 5
    ScrollBar.vertical:ScrollBar{}
    delegate: CropDefectShow{
        visible:dataShowCore.defect_show(defectName)
        Behavior on width{NumberAnimation{duration:300}}
        Behavior on height{NumberAnimation{duration:300}}
        height:  visible?root.height:1
        width:   visible?height:1

    }

}
