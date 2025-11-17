import QtQuick.Controls
import QtQuick
import QtQuick.Layouts
ColumnLayout {
    anchors.fill:parent
    DefectShowHead{}
    Item{
        Layout.fillWidth : true
        Layout.fillHeight : true
        Label{
            visible : dataShowCore_.show_num
            font.bold : true
            anchors.centerIn : parent
            text:qsTr("无缺陷报警！")
            font.pointSize : 28
            color : "green"
        }

        ShowDefectList{
            anchors.fill:parent
            model:dataShowCore.defectModel
        }
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
