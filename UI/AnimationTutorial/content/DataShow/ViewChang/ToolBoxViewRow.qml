import QtQuick

Row {
height:25
CheckDelegateBase{
    text:"塔形标注"
    font.bold:true
    height:parent.height
    checked:dataShowCore.controls.taper_shape_annotation_enable
    onCheckedChanged:dataShowCore.controls.taper_shape_annotation_enable = checked
}


CheckDelegateBase{
    text:"3D预览"
    font.bold:true
    height:parent.height
    checked:dataShowCore.controls.thumbnail_view_3d_enable
    onCheckedChanged:dataShowCore.controls.thumbnail_view_3d_enable = checked
}

CheckDelegateBase{
    text:"2D预览"
    font.bold:true
    height:parent.height
    checked:dataShowCore.controls.thumbnail_view_2d_enable
    onCheckedChanged: dataShowCore.controls.thumbnail_view_2d_enable = checked
}

}
