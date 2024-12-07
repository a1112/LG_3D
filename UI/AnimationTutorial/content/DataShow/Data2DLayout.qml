import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DataShowRoot"
import "DataShowItem"
import "Foot"
import "MaxMinValue"
ColumnLayout{
    anchors.fill:parent
    SplitView{
        Layout.fillWidth: true
        Layout.fillHeight: true

        orientation: Qt.Vertical

        Loader{
            SplitView.fillWidth: true
            SplitView.preferredHeight: 333
            asynchronous: true
            sourceComponent:RowLayout{
                Layout.fillWidth: true
                DataShowItemSelectView{
                    Layout.fillHeight: true
                }

                StackLayout{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: dataShowCore.topDataManage.currentShowModel

                    DataShowItemDefects{  // 缺陷显示
                    }

                    DataShowItemInfos{
                    }

                    DataShowItemCharts{  //  charts
                    }
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
