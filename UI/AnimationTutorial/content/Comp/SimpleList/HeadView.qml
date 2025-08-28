import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import "../../Base"
import "../../Labels"
import "../../btns"
PaneBase  {
    id:view
    Material.elevation: 5
    MouseArea {
        cursorShape: Qt.SizeAllCursor
        id: dragArea
        anchors.fill: parent
        drag.target: root
    }
    RowLayout{
        anchors.fill: parent
        Item{// 填充
            width: 5
            height: 1
        }
        LabelFootInfoKey{
            text: coreState.currentSteelNo
            color: Material.color(Material.Blue)
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Button{
            visible: coreModels.listViewType!=coreModels.realViewType
            text: "退出查询"
            Material.background: Material.Blue
            onClicked: {
            coreModels.listViewType=coreModels.realViewType
            }
        }
        Button{
            text: "看头"
            onClicked: {
                imageViewCore.flickA.contentY=0
                imageViewCore.flickB.contentY=0
            }
        }
        Button{
            text: "看尾"
            onClicked: {
                imageViewCore.flickA.contentY=imageViewCore.flickA.contentHeight-imageViewCore.flickA.height
                imageViewCore.flickB.contentY=imageViewCore.flickB.contentHeight-imageViewCore.flickB.height
            }
        }

        LabelButton{
            height: parent.height
            width: height
            ToolTip.text:"上一卷"
            labelText:"↢"
            onClicked: control.changeToPreSteel()
            enabled: coreState.hasPreSteel
        }
        LabelButton{
            height: parent.height
            width: height
            ToolTip.text:"下一卷"
            labelText:"↣"
            onClicked: control.changeToNextSteel()
            enabled: coreState.hasNextSteel
        }
        FlushButton{
            height: parent.height
            width: height
            tipText: qsTr("刷新")
            onClicked: {
                //刷新列表
                control.initMainListByNum(100)
            }
        }
        LabelButton{
            height: parent.height
            width: height
            labelColor:imageViewCore.currentListViewModel==imageViewCore.showListViewModel?
                    Material.color(Material.Blue):Material.color(Material.Green)
            labelRotation: imageViewCore.currentListViewModel==imageViewCore.showListViewModel?0:-90
            labelText: "▼"
            ToolTip.text:"列表"
            onClicked: {
                imageViewCore.changeListViewModel()
            }
        }
        Item{
            width: 5
            height: 1
        }


    }
}
