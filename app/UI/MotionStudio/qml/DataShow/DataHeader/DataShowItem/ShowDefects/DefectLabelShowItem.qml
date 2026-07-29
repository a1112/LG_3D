import QtQuick
import QtQuick.Controls.Material
CheckDelegate {
    id:root

    required property var model
    required property int index
    required property var controller
    required property var defectClassController

    readonly property string defectName: root.model.name || ""
    readonly property bool defectShow:
        root.model.show !== undefined ? root.model.show : true
    readonly property color defectColor: root.model.color || "#FFFFFF"
    readonly property int defectNum:
        root.controller.getNumByDefectName(root.defectName)

    visible: root.defectShow || root.controller.defectManage.un_defect_show
    width:visible?implicitWidth:0
    Behavior on width {NumberAnimation{duration:200}}
    checked: root.defectClassController.defectDictAll[root.defectName] ?? false
    text: root.defectName
    font.bold:true
    Material.foreground: root.defectColor
    onClicked:{
        if (root.defectClassController.defectDictAll[root.defectName] !== checked){
                root.defectClassController.defectDictAll[root.defectName] = checked
                root.defectClassController.flushDefectDictAll()
            }
        }

    DefectNumLabel{
                    defect_num:root.defectNum
                    anchors.bottom:parent.top
                    anchors.horizontalCenter:parent.horizontalCenter

    }
    Rectangle{
        width:1
        height:parent.height
        anchors.right:parent.right
        color: root.defectShow ? Material.color(Material.Orange)
                               : Material.color(Material.Green)
    }
}


