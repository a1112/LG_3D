import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../Header"
import "../"
Item {
    Layout.fillWidth: true
    Layout.fillHeight:true

    DataShowItemHead{
        id:dsh
    }
    StackLayout{
        id:dsr
        anchors.fill: parent
        SplitView.fillWidth: true
        SplitView.fillHeight: true
        currentIndex:root.surfaceData.rootViewIndex
        DataShowRootView{   // 2D  data
            Layout.fillWidth: true
            Layout.fillHeight:true
        }
        Data3DLayout{
            Layout.fillWidth: true
            Layout.fillHeight:true
        }
    }

    ColumnLayout{
        anchors.fill:parent
        LayoutItemProxy{
            Layout.fillWidth: true
            target:dsh
            implicitHeight:27
            height: 27
        }
        LayoutItemProxy{
            Layout.fillWidth: true
            Layout.fillHeight:true
            target:dsr
        }

    }
    RowLayout{
        visible:false
        anchors.fill:parent
        LayoutItemProxy{
        Layout.fillHeight:true
        target:dsh
        width:27
        }
        LayoutItemProxy{
            Layout.fillWidth: true
            Layout.fillHeight:true
            target:dsr
        }
    }
}
