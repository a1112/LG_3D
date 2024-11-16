import QtQuick 2.15
import QtQuick.Controls.Material
Item {
    width: row.width
    height: 25

    Pane{
        anchors.fill: parent
        Material.elevation: 5
        opacity:hh.hovered? 1 : 0.9
    }
    Frame{
    anchors.fill: parent
        }
    HoverHandler{
        id:hh
    }
    Row{

        id:row
        spacing: 2
        ItemDelegate{
            text: ["网格 ▼","高低 ▼"][dataShowCore.chartShowType]
            font.family: "Material Icons"
            height: 25
            onClicked:{
                menu_type.popup()
            }
            Rectangle{
                border.color:Material.color(Material.Blue)
                border.width: 1
                color: "transparent"
                anchors.fill: parent
            }
        }

        ItemDelegate{
            height: 25
            text: "网格: "+(coreCharts.tickSizeZ).toFixed(1)+ " mm"
        }

        ItemDelegate{
            height: 25
            text: "偏移: "+(coreCharts.offsetZ).toFixed(1)+ " mm"
        }
        ItemDelegate{
            height: 25
            text: "重置"
            onClicked: {
                coreCharts.reset()
            }
        }
    }
    Menu{
        id:menu_type
        MenuItem{
            text: "网格类型"
            font.bold: dataShowCore.chartShowType == 0
            onClicked:{
                dataShowCore.chartShowType = 0
            }
        }
        MenuItem{
            text: "高低值"
            font.bold: dataShowCore.chartShowType ==1
            onClicked:{
                dataShowCore.chartShowType = 1
            }
        }
    }
}
