import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Model/server"
ItemDelegate{
    id:root

    required property var model
    required property int index
    required property var defectClassController
    required property var dialogManager

    readonly property string defectName: root.model.name || ""
    readonly property int defectLevel: root.model.level || 0
    readonly property bool defectShow:
        root.model.show !== undefined ? root.model.show : true
    readonly property string defectColor: root.model.color || "#FFFFFF"

    function setColor(color_){
        root.defectClassController.updateDefectClass(
                    root.defectName, "color", color_)
    }

    function setLevel(level_){
        root.defectClassController.updateDefectClass(
                    root.defectName, "level", level_)
    }

    function setShow(show_){
        root.defectClassController.updateDefectClass(
                    root.defectName, "show", show_)
    }

    Frame{
        anchors.fill:parent
    }

    RowLayout {
        anchors.fill:parent

        Row{
            Layout.preferredWidth:150
            Label{
                text: qsTr("名称:  ")
                font.pointSize:12
            }

            Label{
                text: root.defectName
                font.pointSize:12
                font.bold:true
            }
        }
        Row{
            Layout.preferredWidth:100
            Label{
                text: qsTr("等级: ")
                font.pointSize:12
                anchors.verticalCenter:parent.verticalCenter
            }
            ComboBox{
                height:30
                scale:0.9
                width:75
                currentIndex: root.defectLevel
                model:["0", "1", "2", "3", "4", "5"]
                onActivated: {
                    root.setLevel(currentIndex)
                }
            }
        }
        Row{
            Layout.preferredWidth:100

            CheckDelegate{
                text: qsTr("屏蔽: ")
                height:20
                checked: !root.defectShow
                onToggled: {
                    root.setShow(!checked)
                }
            }
        }
        Item{
            Layout.fillWidth:true
            height:1
        }


        Label{
            text: root.defectColor
            font.pointSize:15
            color: root.defectColor
        }
        Rectangle{
            height:20
            width:height
            color: root.defectColor
            ItemDelegate{
                anchors.fill:parent
                onClicked:{
                    root.dialogManager.selectColor(root.setColor)
                }
            }
        }
        Item{
            width:10
            height:1
        }
    }
}
