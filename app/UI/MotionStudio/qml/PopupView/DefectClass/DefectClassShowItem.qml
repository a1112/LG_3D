import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Model/server"
ItemDelegate{
    id:root

    // 直接使用 model 数据，而不是通过 defectClassItem
    property string defectName: model.name || ""
    property int defectLevel: model.level || 0
    property bool defectShow: model.show !== undefined ? model.show : true
    property string defectColor: model.color || "#FFFFFF"

    function setColor(color_){
        set_defect_dict_property(index, "color", color_)
    }

    function setLevel(level_){
        set_defect_dict_property(index, "level", level_)
    }

    function setShow(show_){
        set_defect_dict_property(index, "show", show_)
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
                text: defectName
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
                currentIndex:defectLevel
                model:["0", "1", "2", "3", "4", "5"]
                onActivated: {
                    setLevel(currentIndex)
                }
            }
        }
        Row{
            Layout.preferredWidth:100

            CheckDelegate{
                text: qsTr("屏蔽: ")
                height:20
                checked:!defectShow
                onToggled: {
                    setShow(!checked)
                }
            }
        }
        Item{
            Layout.fillWidth:true
            height:1
        }


        Label{
            text: defectColor
            font.pointSize:15
            color:defectColor
        }
        Rectangle{
            height:20
            width:height
            color:defectColor
            ItemDelegate{
                anchors.fill:parent
                onClicked:{
                    dialogs.selectColor(setColor)
                }
            }
        }
        Item{
            width:10
            height:1
        }
    }
}
