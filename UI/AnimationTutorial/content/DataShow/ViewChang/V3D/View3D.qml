import QtQuick
import "../../View3D"
Item {
    id:root
    Item{
        anchors.fill:parent
        visible:!surfaceData.is3DrootView && dataShowCore.controls.thumbnail_view_3d_enable
        Loader{
            anchors.fill:parent
            asynchronous:true
            active:parent.visible
            Thumbnail3D{
                width:parent.width
                height:parent.height
                x:50
            }
        }
        MouseArea{
            anchors.fill:parent
            onClicked:{
                surfaceData.rootViewto3D()

            }

        }
    }
}
