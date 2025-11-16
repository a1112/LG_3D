import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
Rectangle{
    id:rt
    property string timeStr: ""
//    property string t_color :coreModels.getListColor(steelNo)//"#9900FF00"
    width: root.width
    height: 30
    color: coreStyle.leftInfoStyle.historyListbackColor//"#052641"
    signal clicked(int index)
    ItemDelegate{
        anchors.fill: parent
        ToolTip.visible: hovered
        ToolTip.text: "板号"+steelID+" 板坯号"+coilID+" 钢种："+steelType+" 长："+steelLength+"m 宽："+steelWidth+"m 厚："+steelThick+"mm"
        onClicked:{
            rt.clicked(index)
        }
    }
    Row{
        id:rowItem
        spacing: 0
        anchors.fill: parent
        HistoryTextItem{
            width: idWidth
            text:steelID
            textColor:t_color
        }
        HistoryTextItem{
            text:steelNo
            textColor:t_color
            width: steelWidth_
        }
        HistoryTextItem{
            text:coilID
            textColor:t_color
            width: coilIDWidth_
        }

        HistoryTextItem{
            text:steelType
            textColor:t_color
            width: steelTypeWidth
        }
        HistoryTextItem{
            text:       steelLength+"x"+steelWidth+"x"+steelThick
            textColor:t_color
            width: steelLength_
        }
        HistoryTextItem{
            width: timeWidth
            text:detectTime
            textColor:t_color
        }
    }
}
