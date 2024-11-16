import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts
import "CardView/ChartView"
import "CardView/AlarmSetting"
import "DfectView"
import "Head"
import "../Base"
import "Alarm"
import "HistoryView"
ColumnLayout{
    width: 1920
    height: 1080

        SplitView{
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout{
                SplitView.fillHeight: true
                 SplitView.fillWidth: true

                HeadToolBox{
                    Layout.fillWidth: true
                }
                DfectView3D{
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            }
                ColumnLayout{
                    SplitView.preferredWidth: 300
                     SplitView.fillHeight: true

                    USTB{
                        Layout.fillWidth: true
                        source: "../images/USTB.png"
                    }

                    AlarmButtons{
                        Layout.fillWidth: true
                        implicitHeight: 150
                    }
                    Item{
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ListTabelView{}
                    }

                }
        }
    // }






}
