import QtQuick
import Qt5Compat.GraphicalEffects
import "../../Base"
Item {
        anchors.fill: parent
    Image {
        width: parent.width
        height: parent.height
        // fillMode: Image.PreserveAspectFit
        id: image
        asynchronous: true
        source:dataAreaShowCore.source
        onStatusChanged: {
            if (status === Image.Ready) {
                dataAreaShowCore.sourceWidth = image.sourceSize.width
                dataAreaShowCore.sourceHeight = image.sourceSize.height
            }
        }
        Component.onCompleted: {
            dataAreaShowCore.imageItem = this
        }
    }
    // Image {
    //     cache: true
    //     id: image2
    //     asynchronous: true
    //     source: dataAreaShowCore.source
    //     sourceSize.width:canvas.width
    //     sourceSize.height:canvas.height
    // }
    // GammaAdjust {
    //          anchors.fill: image
    //          source: image2
    //          gamma: dataShowCore.adjustConfig.image_gamma
    //          enabled:visible
    //          visible: dataShowCore.adjustConfig.image_gamma_enable
    //      }
}
