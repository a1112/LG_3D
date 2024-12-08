import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Model"
Popup {
    width: col.width+20
    height: col.height+30
    visible: leftCore.isHoved

    property CoilModel coilModel:leftCore.hovedCoilModel

    onClosed:{
        if (leftCore.isHoved)
            open()
    }
    x: left.width+20
    y:Math.max(20,Math.min(leftCore.hoverPoint.y,leftCore.hoverPoint.y-height-20))

    Label{
        text:"数据摘要"
        anchors.left: parent.Left
        color:Material.color(Material.Orange)
    }

    Column{
        id:col
        spacing:10

        TitleLabel{
            text:coilModel.coilNo
            color:Material.color(Material.Blue)
            anchors.horizontalCenter:parent.horizontalCenter
            font.pointSize: 20
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
    CoilInfo{
        width:  col.width
        height: 100
    }
    TextArea{
        text:leftCore.leftMsg

    }
    }

    }
