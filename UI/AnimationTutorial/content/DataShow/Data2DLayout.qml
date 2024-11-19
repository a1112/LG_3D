import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Header"
import "DataShowRoot"
import "Foot"
import "ShowCharts"
import "MaxMinValue"
ColumnLayout{
    anchors.fill:parent
    SplitView{
        Layout.fillWidth: true
        Layout.fillHeight: true

        orientation: Qt.Vertical

        Loader{
            // active: surfaceData.is2DrootView && dataShowCore.telescopedJointView
            SplitView.fillWidth: true
            SplitView.preferredHeight: 240
            asynchronous: true
            // visible: dataShowCore.telescopedJointView && dataShowCore.chartShowType==0
            sourceComponent:RowLayout{
                Layout.fillWidth: true
                DataShowItemSelectView{
                    Layout.fillHeight: true
                }
                DataShowItemCharts{  //  charts
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
        }
        DataShowRootLayout{
            SplitView.fillWidth: true
            SplitView.fillHeight: true
        }
        ShowViewListView{
            visible: dataShowCore.viewRendererListView
            implicitHeight: 100
            SplitView.fillWidth: true
        }
        MaxMinValueShow{
            id:showViewListView
            visible: dataShowCore.viewRendererMaxMinValue
            implicitHeight: 40
            SplitView.fillWidth: true
        }
    }
    DataShowItemFoot{
        Layout.fillWidth: true
    }
}
