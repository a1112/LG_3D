import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DataShowLabels"
import "DataShowLabels/DefectClassFlow"
import "DataShowLabels/Defect"
import "../Pages/AlarmPage"
import "../Pages/AlarmPage/AlarmItemSimple"
import "Core"
Item {
    visible: auth.isAdmin
    property var surfaceData
    property DataShowCore dataShowCore

    ColumnLayout{
        anchors.fill: parent
        spacing:5
        HeadItem{
        }
        Column{
            spacing:5
            Layout.fillWidth: true
            WarningLine{
                id:warningLine
                    visible:coreModel.toolDict["adjust"]
                    Layout.fillWidth: true
                    // 预警线
            }
            RenderSetting{
                id:renderSetting
                    visible:coreModel.toolDict["adjust"]
                Layout.fillWidth: true
                    // 渲染设置
            }
            AlarmInfo{
            }

            AlarmItemSimple{
                visible:true
                width: parent.width
            }
            Item{
                width: parent.width
                 Layout.fillWidth: true
            }
             }
    Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
    DefectClassFlow{
    }

    }
}

