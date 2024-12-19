
import QtQuick.Layouts
ColumnLayout {
    anchors.fill:parent
    ShowDefectNamesRow{
        implicitHeight:30
        Layout.fillWidth: true
    }

    ShowDefectList{
        Layout.fillWidth:true
        Layout.fillHeight:true
    }
    // Rectangle{
    //     implicitWidth:1
    //     Layout.fillHeight:true
    // }
    // Item{
    //     Layout.fillHeight:true
    //     implicitWidth:220
    //     ShowDefectNames{
    //     }
    // }
}
