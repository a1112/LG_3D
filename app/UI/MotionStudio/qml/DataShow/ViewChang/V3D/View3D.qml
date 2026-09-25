import QtQuick
import "../../View3D"
Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var view3DController

    Item{
        anchors.fill:parent
        visible: !root.surfaceData.is3DrootView
                 && root.dataShowCore.controls.thumbnail_view_3d_enable
        Loader{
            anchors.fill:parent
            asynchronous:true
            active:parent.visible
            Thumbnail3D{
                surfaceData: root.surfaceData
                view3DController: root.view3DController
                width:parent.width
                height:parent.height
                x:50
            }
        }
        MouseArea{
            anchors.fill:parent
            onClicked:{
                root.surfaceData.rootViewto3D()
            }

        }
    }
}
