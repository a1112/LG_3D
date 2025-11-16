import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Comp/Card"
import "../../Comp/Images"
import "AlarmItem"
CardBase{
    max_height: 65+bodyV.height
    id:root
    width: parent.width-8
    showError:coreModel.coreGlobalError.hasGlobalError
    title: "全局报警"

    content_head_tool:
        AnimAlarm2{
        running: coreModel.coreGlobalError.hasGlobalError
        visible:coreModel.coreGlobalError.hasGlobalError
            height:30
            width:30
        }

    content_body:
        Item{
        height: 30
        width: parent.width
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout{
            width: parent.width
            height: parent.height
            Layout.fillWidth: true
            Layout.fillHeight: true

            GridView {
                id: gridView
                anchors.fill: parent
                cellWidth: gridView.width / 3
                cellHeight: 25
                model: coreModel.alarmGlobModel
                delegate: SelectItemDelegate {
                    width: gridView.cellWidth
                    height: gridView.cellHeight
                    titleText: key
                    onChecked_Changed:{
                        coreModel.alarmGlobVis[key] = checked_
                        var temp_alarmGlobVis
                        temp_alarmGlobVis = coreModel.alarmGlobVis
                        coreModel.alarmGlobVis = {}
                        coreModel.alarmGlobVis = temp_alarmGlobVis

                    }

                }

            }

            Column{
                id:bodyV
                width: parent.width
                AlarmItemCameras{
                    visible:coreModel.alarmGlobVis["相机"]
                    width: visible?root.width:0
                    alarmLevel:coreModel.coreGlobalError.errorLevelDict["相机"]
                    height: 100
                }
                AlarmItemNet{
                    visible:coreModel.alarmGlobVis["网络"]
                    alarmLevel:coreModel.coreGlobalError.errorLevelDict["网络"]
                    width: visible?root.width:0
                    height: 120
                }
                AlarmHardware{
                    visible:coreModel.alarmGlobVis["硬件"]
                    alarmLevel:coreModel.coreGlobalError.errorLevelDict["硬件"]
                    width: visible?root.width:0
                    height: 100
                }
            }
        }
    }
}
