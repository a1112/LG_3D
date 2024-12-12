import QtQuick
import QtQuick.Layouts
RowLayout {
    anchors.fill:parent
    ShowDefectList{
        Layout.fillWidth:true
        Layout.fillHeight:true

    }
    Rectangle{
        implicitWidth:1
        Layout.fillHeight:true
    }
    Item{
        Layout.fillHeight:true
        implicitWidth:220
        ShowDefectNames{
        }
    }
}
