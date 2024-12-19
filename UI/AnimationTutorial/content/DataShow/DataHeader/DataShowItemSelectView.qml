import QtQuick
import QtQuick.Controls.Material
Item{
    implicitWidth: 30
    Pane {
        anchors.fill: parent
        Material.elevation:6
    }
    Rectangle{
        anchors.fill: parent
        color:"blue"
        opacity:0.1
    }
    Column{
        spacing: 10
        CheckRecItem{
            text: "缺陷".split("").join('\n')
            height:60
            currentShowModel:dataShowCore.topDataManage.defectShowModel
        }

        CheckRecItem{
            text: "数据".split("").join('\n')
            height:60
            currentShowModel:dataShowCore.topDataManage.dataInfoShowModel
        }
        CheckRecItem{
            text: "曲线".split("").join('\n')
            height:60
            currentShowModel:dataShowCore.topDataManage.lineShowModel

        }

    }

    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
            menu.popup()
        }
    }


    Menu{
        id:menu
        MenuItem{
            text:"曲线数据返回"
            onClicked:{
                Qt.openUrlExternally(api.oldHeightDatUrl)

            }
        }
    }
}
