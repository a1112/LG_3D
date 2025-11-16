import QtQuick 2.15
import "../../Effects/Particles"
import "../../Effects"
Item {
    property int preX:0
    property int image_rotation:-45
        property int temp_image_rotation:-45
    id: watermarkContainer
    width: parent.width
    height: parent.height
    property real watermarkWidth: 260
    property real watermarkHeight: 300

    MouseArea{
        anchors.fill: parent
        onClicked:{
            animItem.item.trigger()
        }
        onPressed:{
            preX=mouseX
            temp_image_rotation=image_rotation
        }
        onPositionChanged:{
            image_rotation=(mouseX-preX)/2+temp_image_rotation
        }

    }
    Loader{
        id:animItem
        anchors.fill: parent
        asynchronous: true
        active:watermarkContainer.visible
        sourceComponent:
        Snowing{
    }
    }
    Repeater {
        model: Math.ceil(watermarkContainer.width / watermarkWidth) * Math.ceil(watermarkContainer.height / watermarkHeight)
        EffectsImage {
            id:efi
            source:coreStyle.isDark?"../../icons/USTB_Dark.png": "../../icons/USTB_Light.png"  // 替换为你的水印图片路径
            opacity:hovered?1:0.2
            rotation: image_rotation // 旋转角度
            x: (index % Math.ceil(watermarkContainer.width / watermarkWidth)) * watermarkWidth
            y: Math.floor(index / Math.ceil(watermarkContainer.width / watermarkWidth)) * watermarkHeight
            scale:hovered?1.2:1
            Behavior on scale{NumberAnimation { duration: 500 }}
            property int r_angle: 0
            MouseArea{
                anchors.fill: parent
                acceptedButtons:Qt.RightButton
                onClicked:r_angle+=180
            }
            Behavior on r_angle{NumberAnimation { duration: 800 }}
            transform: Rotation { origin.x: efi.width/2; origin.y: efi.height/2; axis { x: 0; y: 1; z: 0 } angle: r_angle}
        }
    }




}
