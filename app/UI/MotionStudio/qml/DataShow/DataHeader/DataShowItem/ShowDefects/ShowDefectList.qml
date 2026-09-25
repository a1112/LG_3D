pragma ComponentBehavior: Bound

import QtQuick

import QtQuick.Controls
ListView {
    id:root

    required property var controller
    required property var areaController
    required property var surfaceData
    required property var style
    required property var apiClient
    required property var defectClassController

    clip: true
    orientation:ListView.Horizontal
    spacing: 5
    ScrollBar.vertical:ScrollBar{}
    delegate: CropDefectShow{
        controller: root.controller
        areaController: root.areaController
        surfaceData: root.surfaceData
        style: root.style
        apiClient: root.apiClient
        defectClassController: root.defectClassController
        visible: root.controller.defect_show(defect.config_defect_name)
                 && !(defect.isArea
                      && !root.controller.defectManage.area_defect_show)
        Behavior on width{NumberAnimation{duration:300}}
        Behavior on height{NumberAnimation{duration:300}}
        height:  visible? root.height:1
        width:   visible?height:1
    }

}
