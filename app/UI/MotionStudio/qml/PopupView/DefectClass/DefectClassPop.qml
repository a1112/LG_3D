
pragma ComponentBehavior: Bound

import "../Base"
import "../../Labels"
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
PopupBase {
    id:root

    required property var adaptiveMetrics
    required property var globalContext
    required property var apiClient
    required property var dialogManager

    readonly property var defectClassController:
        root.globalContext.defectClassProperty

    width: root.adaptiveMetrics.boundedWidth(500, 380, 640)
    height: root.adaptiveMetrics.boundedHeight(500, 380, 680)

    Item{
        width:root.width
        height: root.height - root.adaptiveMetrics.headerSideGap
        ColumnLayout{
            anchors.fill:parent
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text:qsTr("缺陷列表")
                color:Material.color(Material.Blue)
            }
            Item{
                id:list
                Layout.fillWidth:true
                Layout.fillHeight:true
                clip:true
                ListView{
                    anchors.fill:parent
                    model: root.defectClassController.defectDictModel
                    delegate:DefectClassShowItem{
                        defectClassController: root.defectClassController
                        dialogManager: root.dialogManager
                        width:list.width
                        height: root.adaptiveMetrics.headerTabHeight
                    }
                }
            }
            RowLayout{
                Layout.fillWidth:true
                implicitHeight: root.adaptiveMetrics.headerTabHeight
                spacing: root.adaptiveMetrics.headerSideGap
                Item{
                    Layout.fillWidth:true
                    implicitHeight: root.adaptiveMetrics.headerTabHeight
                }
                Button{
                    text:qsTr("保存 ")
                    onClicked:{
                        let data = root.defectClassController.defectDictData
                        root.apiClient.setDefecctClassConfig(data)
                    }
                }
            }
        }
    }
}
