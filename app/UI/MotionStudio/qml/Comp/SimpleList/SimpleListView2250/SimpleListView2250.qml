import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls
import "../../../Base"
import "../"
Item {
    id:root
    property alias currentIndex: list.currentIndex
    width: 800
    property int idWidth: root.width*0.1
    property int steelWidth_: root.width*0.2
    property int coilIDWidth_: root.width*0.2

    property int timeWidth: root.width*0.2
    property int  steelTypeWidth: root.width*0.2
    property real steelLength_: root.width*0.15
    height: col.height

    Column{
        id:col
        width: parent.width
        spacing: 0
        HeadView{
            id:hv
            width: parent.width
            height: 45
        }
        Rectangle{
            id:lh
            visible: list.height
            z:1
            width: parent.width
            height: 30
            gradient: Gradient {
                GradientStop { position: 0.0;
                    color: coreStyle.leftInfoStyle.historyListHeadGradientColor1//"#085FB2"
                }
                GradientStop { position: 1.0;
                    color:  coreStyle.leftInfoStyle.historyListHeadGradientColor2//"#00498C"
                }
            }
            SplitViewBase{
                anchors.fill: parent
                HistoryHeadItem{
                    onWidthChanged: idWidth=width
                    SplitView.preferredWidth:idWidth
                    text: "ID"
                }
                HistoryHeadItem{
                    SplitView.preferredWidth:steelWidth_
                    text: "板号"
                    onWidthChanged:{
                        steelWidth_=width
                    }
                }
                HistoryHeadItem{
                    SplitView.preferredWidth:coilIDWidth_
                    text: "板坯号"
                    onWidthChanged:{
                        coilIDWidth_=width
                    }
                }
                HistoryHeadItem{
                    SplitView.fillWidth: true
                    SplitView.preferredWidth:steelTypeWidth
                    text: "钢种"
                    onWidthChanged:steelTypeWidth=width
                }
                HistoryHeadItem{
                    SplitView.fillWidth: false
                    SplitView.preferredWidth:steelLength_
                    text: "规格"
                    onWidthChanged:{
                        steelLength_=width
                    }
                }
                HistoryHeadItem{
                    SplitView.fillWidth: true
                    text: "日期"
                    SplitView.preferredWidth:timeWidth
                    onWidthChanged: timeWidth=width
                }
            }

            MouseArea{
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                onClicked: {
                    mn.popup()
                }
            }
            Menu{
                id:mn
                Repeater{
                    model: 5
                    MenuItem{
                        text: "test"
                    }
                }

            }
        }
        ListView {
            visible: list.height
            width: parent.width
            currentIndex: coreState.currentSteelIndex
            onCurrentIndexChanged: {
                if (coreState.currentSteelIndex === coreModels.mainListModel.count - 1) {
                    // 刷新时保持视图停留在列表顶部，而不是跳转到底部
                    list.positionViewAtBeginning()
                }
            }

            height: imageViewCore.currentListViewModel==imageViewCore.showListViewModel?
                        Math.min(contentHeight,2.6*dpi):0
            Behavior on height {NumberAnimation{duration: 500}}
            verticalLayoutDirection:ListView.BottomToTop
            clip: true
            id:list
            model:coreModels.mainListModel
            highlightMoveDuration:500
            ScrollBar.vertical: ScrollBar{}
            highlight : Item{
                z:99999
                Rectangle{
                    anchors.fill: parent
                    color: "#00000000"
                    border.width: 1
                    border.color: "red"
                }
            }
            delegate: ListItemDelegate2250{
                onClicked: {
                    coreState.currentSteelIndex=index
                    coreState.flushAuto()
                }
            }
        }
    }
    MouseArea{
        hoverEnabled: true
        onContainsMouseChanged: {
            console.log(imageViewCore.listHovered)
            if (containsMouse){
                imageViewCore.listHovered=true
            }
            else{
                imageViewCore.listHovered=false
            }

        }
    }
}
