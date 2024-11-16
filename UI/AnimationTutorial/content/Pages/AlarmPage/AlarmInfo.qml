import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
// import "../../Base"
import "../../Comp/Card"
import "AlarmItemCoil"
import "AlarmItemTaperShape"

CardBase{
    max_height: 95+bodyV.height
    id:root
    width: parent.width-8
    height: isShow? max_height : 35
    title: "报警"

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
                Layout.fillWidth: true
                cellWidth: gridView.width / 3
                cellHeight: 25
                height: 50
                model: coreModel.alarmModel
                delegate: SelectItemDelegate {
                    width: gridView.cellWidth
                    height: gridView.cellHeight
                    titleText: key
                    level_:level
                    onChecked_Changed:{
                        coreModel.alarmVis[key] = checked_
                        var temp_alarmGlobVis
                        temp_alarmGlobVis = coreModel.alarmVis
                        coreModel.alarmVis = {}
                        coreModel.alarmVis = temp_alarmGlobVis
                    }
                }
            }
            Column{
                id:bodyV
                width: parent.width
                 Layout.fillWidth: true
                AlarmItemFlatRoll{
                    visible:coreModel.alarmVis["扁卷"]
                    width: parent.width
                }
                AlarmItemTaperShape{
                    visible:coreModel.alarmVis["塔形"]
                    width: parent.width
                }
                Item{
                width:10
                height:10
                }

            }
        }
    }
}
