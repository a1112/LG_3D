import QtQuick
import QtQuick.Controls
MenuItem {
    id: root

    required property var model
    required property int index
    required property var defect
    required property var defectClassController

    readonly property string defectName: root.model.name || ""
    readonly property int defectLevel: root.model.level || 0
    readonly property bool defectShow:
        root.model.show !== undefined ? root.model.show : true

    text: root.defectName
    checkable: true
    checked: root.defectShow
    Rectangle{
        anchors.top:parent.top
        height:1
        width:parent.width
        color: root.defectClassController.getColorByLevel(root.defectLevel)
        opacity:0.7
    }
    Rectangle{
        width:10
        anchors.right:parent.right
        height:parent.height
        visible: root.defectName === root.defect.config_defect_name
        color: root.defectClassController.getColorByName(root.defectName)
    }

    onClicked:{
        root.defect.setCheckDefectName(root.defectName)
    }

}
