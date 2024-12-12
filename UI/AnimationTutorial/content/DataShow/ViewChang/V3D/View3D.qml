import QtQuick
import "../../View3D"
Item {
    id:root
    Item{
        anchors.fill:parent
        visible:!surfaceData.is3DrootView
        Loader{
            anchors.fill:parent
            asynchronous:true
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
