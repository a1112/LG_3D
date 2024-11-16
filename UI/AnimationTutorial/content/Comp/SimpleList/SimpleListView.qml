import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls
import AnimationTutorial
import "../../Base"

ColumnLayout {
    id:root
    property alias currentIndex: list.currentIndex
    property int idWidth: root.width*0.2
    property int steelWidth_: root.width*0.2
    property int timeWidth: root.width*0.3
    property int timeSizeWidth: root.width*0.3
    property alias model: list.model
    property ListModel historyModel: ContCore.historyModel
    property ListModel historyTitleModel: ContCore.historyTitleModel
    Rectangle{
        id:lh
        Layout.fillWidth: true
        height: 30
        gradient: Gradient {
            GradientStop {
                position: 0.0;
                color:"#085FB2"
            }
            GradientStop {
                position: 1.0;
                color:"#00498C"
            }
        }
        SplitViewBase{
            anchors.fill: parent
            Repeater{
                model: historyTitleModel
                HistoryHeadItem{
                text: title
                SplitView.preferredWidth:wid*root.width
                onWidthChanged: {
                    wid=width/root.width
                }
                SplitView.fillWidth: fw
                }
            }
        }
    }
    Item{
         Layout.fillWidth: true
         Layout.fillHeight: true
        ListView {
            anchors.fill: parent
            visible: list.height
            model: historyModel
            width: parent.width
            verticalLayoutDirection:ListView.BottomToTop
            clip: true
            id:list
            highlightMoveDuration:500
            highlight : Item{
                z:999
                Rectangle{
                    anchors.fill: parent
                    color: "#00000000"
                    border.width: 1
                    border.color: "red"
                }
            }
            delegate: ListItemDelegate{
                        onClicked: {
                            list.currentIndex=index
                            core.historyBaseName=fileBaseName
                        }
            }
        }
    }

}
