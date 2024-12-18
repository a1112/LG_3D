import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "Foot"
import "MaxMinValue"
import "DataHeader"
ColumnLayout{
    anchors.fill:parent
    SplitView{
        Layout.fillWidth: true
        Layout.fillHeight: true
        orientation: Qt.Vertical

        DataHeaderView{
            SplitView.fillWidth: true
            SplitView.preferredHeight: 260
        }

        DataShowRootLayout{     // <----------
        // SplitView.fillWidth: true
        // SplitView.fillHeight:true

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
