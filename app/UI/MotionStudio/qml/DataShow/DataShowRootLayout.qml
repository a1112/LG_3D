import QtQuick
import QtQuick.Layouts

import "Header"

Item {

    DataShowItemHead{
        id:dsh
    }

    DataShowRootView{   // show
        Layout.fillWidth: true
        Layout.fillHeight: true
        id:dsr
    }

    ColumnLayout{
        anchors.fill:parent

        LayoutItemProxy{
            Layout.fillWidth: true
            target:dsh
            height: adaptive.scaleMetric(27, 24, 36)
        }

        LayoutItemProxy{
            Layout.fillWidth: true
            Layout.fillHeight:true
            target:dsr
        }
    }

}
