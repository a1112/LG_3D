import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
Popup {
    width: col.width+20
    height: col.height+30
    visible: leftCore.isHoved
    onClosed:{
        if (leftCore.isHoved)
            open()
    }
    x: left.width+20
    y:Math.max(20,Math.min(leftCore.hoverPoint.y,leftCore.hoverPoint.y-height-20))



    Column{
        id:col
        spacing:10

        TitleLabel{
            text: "数据简要"
            color:Material.color(Material.Blue)
            anchors.horizontalCenter:parent.horizontalCenter
        }

        Row{
        height: 150
        spacing: 3
        id:row
        Repeater{
            model: leftCore.preSourceModelS
            ImageItem{
                hasImage: leftCore.hovelCoilData.Status_S>=0

            }
        }
        Repeater{
            model: leftCore.preSourceModelL
            ImageItem{
                hasImage: leftCore.hovelCoilData.Status_L>=0
            }
        }
    }


    TextArea{
        text:leftCore.leftMsg

    }
    }

    }
