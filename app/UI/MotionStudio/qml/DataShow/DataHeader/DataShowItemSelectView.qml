import QtQuick
import QtQuick.Controls.Material
Item{
    id: root

    required property var controller
    required property var style
    required property var apiClient

    implicitWidth: 30
    Pane {
        anchors.fill: parent
        Material.elevation:6
        Material.background: root.style.headerBackgroundColor
    }
    Rectangle{
        anchors.fill: parent
        color: root.style.headerBackgroundColor
    }
    Column{
        spacing: 10
        CheckRecItem{
            controller: root.controller
            style: root.style
            text: "缺陷信息".split("").join('\n')
            height:100
            currentShowModel: root.controller.topDataManage.defectShowModel
        }

        CheckRecItem{
            controller: root.controller
            style: root.style
            text: "数据信息".split("").join('\n')
            height:100
            currentShowModel: root.controller.topDataManage.dataInfoShowModel
        }
        CheckRecItem{
            controller: root.controller
            style: root.style
            text: "曲线信息".split("").join('\n')
            height:100
            currentShowModel: root.controller.topDataManage.lineShowModel

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
                Qt.openUrlExternally(root.apiClient.oldHeightDatUrl)

            }
        }
    }
}
