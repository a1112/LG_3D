import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CardView/ChartView"
import "CardView/AlarmSetting"
import "DfectView"
import "Head"
import "../Base"
import "Alarm"
import "HistoryView"
ColumnLayout{
    SplitView.fillHeight: true
     SplitView.fillWidth: true

    HeadToolBox{
        Layout.fillWidth: true
    }

    DfectView{
    Layout.fillWidth: true
    Layout.fillHeight: true
}
}

