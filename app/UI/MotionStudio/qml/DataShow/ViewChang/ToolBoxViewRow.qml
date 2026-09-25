import QtQuick

Row {
    id: root
    required property var surfaceData
    required property var controller
    readonly property bool meshExits: root.surfaceData.meshExits
    height: 25
    CheckDelegateBase{
        text:"塔形标注"
        font.bold:true
        height:parent.height
        checked: root.controller.controls.taper_shape_annotation_enable
        onCheckedChanged: root.controller.controls.taper_shape_annotation_enable = checked
    }


    CheckDelegateBase{
        text:"3D预览"
        font.bold:true
        height:parent.height
        enabled: root.meshExits
        checked: root.controller.controls.thumbnail_view_3d_enable
        onCheckedChanged: root.controller.controls.thumbnail_view_3d_enable = checked
    }

    CheckDelegateBase{
        text:"2D预览"
        font.bold:true
        height:parent.height
        checked: root.controller.controls.thumbnail_view_2d_enable
        onCheckedChanged: root.controller.controls.thumbnail_view_2d_enable = checked
    }

}
