
/*
    2D功能切换
*/
import QtQuick.Layouts
import "V2D"
import "V3D"
ColumnLayout {
    id:root
    width: 350
    // height: width/dataShowCore.aspectRatio
        View3D{
            width:root.width
            Layout.fillHeight:true
        }
        View2D{
            width:root.width
            height:width
        }


}
