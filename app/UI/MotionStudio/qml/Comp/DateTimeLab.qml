import QtQuick 2.15
import QtQuick.Controls.Material 2.15

//时间 日期
Row {
    spacing: 2
    anchors.margins: 5
    property DateTime date: NowDate{}
    property color labelColor: Material.color(Material.Purple)
    TimeNumberLab{
        text: date.fullYear
    }
    LabelFootInfoKey{
        color: labelColor
        text: qsTr("年")
        font.pointSize: 15
        anchors.verticalCenter:  parent.verticalCenter
    }
    TimeNumberLab{
        text: date.month

    }
    LabelFootInfoKey{
         color: labelColor
        text: qsTr("月")
        font.pointSize: 15
        anchors.verticalCenter: parent.verticalCenter
    }
    TimeNumberLab{
        text: date.day
    }
    LabelFootInfoKey{
 color: labelColor
        text: qsTr("日")
        font.pointSize: 15
        anchors.verticalCenter: parent.verticalCenter
    }
    Item{
        width: 15
        height: 1
    }
    TimeNumberLab{

        text: date.hours
    }
    Item{
        width: 10
        height: 1
        anchors.verticalCenter: parent.verticalCenter
        LabelFootInfoKey{
            anchors.centerIn: parent
            id:seq_
             color: labelColor
             text: ":"
            Timer{
                running: false
                interval: 1000
                repeat: true
                onTriggered:seq_.visible=!seq_.visible
            }
        }
    }
    TimeNumberLab{
        text: date.minutes
    }
    //LabelFootInfoKey{
    //text: qsTr(" : ")
    //anchors.verticalCenter: parent.verticalCenter
    //}
    //TimeNumberLab{
    //text: date.second
    //}
}
