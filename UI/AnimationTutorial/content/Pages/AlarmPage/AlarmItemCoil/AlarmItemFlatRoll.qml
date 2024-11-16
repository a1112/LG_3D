import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Labels"
import "../AlarmSimple"
Item {
    id:root
    property string global_key: ""
    property bool showMore: false
    height: coll.height+5
    property ListModel cameraModel: ListModel{
    }
    Frame{
        anchors.fill: parent
    }
    Column{
        id:coll
        width:parent.width
        Label{
            x:root.width/2-width/2
            text:"扁卷检测"
            font.pointSize: 14
            font.bold: true
            color: Material.color(Material.Blue)
            font.family: "Microsoft YaHei"
        }

        RowLayout {
            visible:!showMore
            height: 30
            width:parent.width
            Layout.fillWidth: true
            KeyLabel {
                text: "内径测量"
                opacity: 0.8
                font.bold: true
            }
            ValueTextLabel{
                Layout.fillWidth: true
                text: coreAlarmInfo.coreFlatRoll.innerDiameter.toFixed(2)
            }
            KeyLabel {
                text: "mm"
                opacity: 0.8
                font.bold: true
            }

            Item{
                width: 10
                height: 1
            }
        }
        SecondaryDataView{
            width:parent.width
            visible:root.showMore
        }
        AlarmItemCoilItemView{
            width:parent.width
            visible:root.showMore && coreAlarmInfo.coreFlatRoll.s.hasData
            coreFlatRollItem:coreAlarmInfo.coreFlatRoll.s
        }
        SimpleErrView{
            visible:(!coreAlarmInfo.coreFlatRoll.s.hasData )&& root.showMore
            text_:"S 端 无数据"
        }
        AlarmItemCoilItemView{
            width:parent.width
            visible:root.showMore && coreAlarmInfo.coreFlatRoll.l.hasData
           coreFlatRollItem: coreAlarmInfo.coreFlatRoll.l
        }
            SimpleErrView{
                visible:(!coreAlarmInfo.coreFlatRoll.l.hasData) && root.showMore
                text_:"L 端 无数据"
            }
            Item{
                width:parent.width
                Layout.fillWidth: true
                height: 25
                ItemDelegate{
                    anchors.fill: parent
                    onClicked: {
                        showMore=!showMore
                    }
                    Label{
                        font.bold: true
                        anchors.centerIn: parent
                        text: showMore?"收起":"更多..."
                    }
                }

            }


        }

    }
