import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Base"
import "../../Base"
RowLayout {
    property int mm_x: + (dataShowCore.sourceWidth*surfaceData.scan3dScaleX).toFixed(1)
    property int mm_y: + (dataShowCore.sourceHeight*surfaceData.scan3dScaleY).toFixed(1)
    property real flatRollValue: mm_x/mm_y
    property int level:1
    DropShadowRec{
        radius: 15
        width: 20
        height: 20
        color: {
            if (level==1){
                return Material.color(Material.Green)
            }
            if (level==2){
                return Material.color(Material.Yellow)
            }
            if (level==3){
                return Material.color(Material.Red)
            }
            return Material.color(Material.Grey)
        }
    }
    TitleLabel{
        text: "图像宽高比"
    }
    ValueLabel{
        id:lab
        text:flatRollValue.toFixed(2)
        Layout.fillWidth: true
        color: flatRollValue<0.9||flatRollValue>1.1?"red":"green"
    }
    Label{
    text: "w/h"
    color: "#747474"
    }

}
