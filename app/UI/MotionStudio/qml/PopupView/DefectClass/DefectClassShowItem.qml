import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Model/server"
ItemDelegate{
    id:root


    function setColor(color_){
        set_defect_dict_property(index,"color",color_)
        // defectClassItem.defectColor = color_

    }

    property DefectClassItemModel defectClassItem: DefectClassItemModel{}

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
                text: defectClassItem.defectName
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
                currentIndex:defectClassItem.defectLevel
                model:6
            }
        }
        Row{
            Layout.preferredWidth:100

            CheckDelegate{
                text: qsTr("屏蔽: ")
                height:20
                checked:!defectClassItem.defectShow
            }
        }
        Item{
            Layout.fillWidth:true
            height:1
        }


        Label{
            text: defectClassItem.defectColor
            font.pointSize:15
            color:defectClassItem.defectColor
        }
        Rectangle{
            height:20
            width:height
            color:defectClassItem.defectColor
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
