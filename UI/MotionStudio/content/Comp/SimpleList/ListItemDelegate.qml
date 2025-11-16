import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
Rectangle{
    id:rt
    property string timeStr: ""
    property var itemDatas: modelDatas
    width: root.width
    height: 30
    color: "#052641"
    signal clicked(int index)
    ItemDelegate{
        anchors.fill: parent
        onClicked:{
            rt.clicked(index)
        }
    }
    Row{
        id:rowItem
        spacing: 0
        anchors.fill: parent

        Repeater{
            model: historyTitleModel
            HistoryTextItem{
                width: wid*rt.width
                text:{return eval(key)}
                textColor:t_color
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // HistoryTextItem{
        //     width: idWidth
        //     text:index
        //     textColor:t_color
        //     anchors.verticalCenter: parent.verticalCenter
        // }
        // HistoryTextItem{
        //     text:(index/3).toFixed(0)
        //     textColor:Material.color(Material.Green)
        //     width: steelWidth_
        //     anchors.verticalCenter: parent.verticalCenter
        // }
        // HistoryTextItem{
        //     width: timeWidth
        //     text:fileBaseName
        //     textColor:t_color
        //     anchors.verticalCenter: parent.verticalCenter
        // }
    }
}
