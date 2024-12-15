import QtQuick
import Qt5Compat.GraphicalEffects
import "../../Base"
Item {
        anchors.fill: parent
        BackSvg{
            anchors.fill: parent
        }
    Image {
        cache: true
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        id: image
        asynchronous: true
        source:surfaceData.source
        onStatusChanged: {
            if (status === Image.Ready) {
                dataShowCore.sourceWidth = image.sourceSize.width
                dataShowCore.sourceHeight = image.sourceSize.height
            }
        }
        Component.onCompleted: {
            dataShowCore.imageItem=this

        }
    }
    Image {
        cache: true
        id: image2
        asynchronous: true
        source: surfaceData.source
        sourceSize.width:canvas.width
        sourceSize.height:canvas.height
    }
    GammaAdjust {
             anchors.fill: image
             source: image2
             gamma: dataShowCore.adjustConfig.image_gamma
             enabled:visible
             visible: dataShowCore.adjustConfig.image_gamma_enable
         }

    Image{
        id:image_show
        cache: true
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: surfaceData.error_source
        visible: surfaceData.error_visible && dataShowCore.adjustConfig.image_gamma_enable
        enabled:visible
        opacity: surfaceData.tower_warning_show_opacity/100
    }

}
