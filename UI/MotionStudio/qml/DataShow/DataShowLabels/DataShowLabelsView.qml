import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DefectClassFlow"
Item {
    visible: dataShowCore.viewDefectListView


    ColumnLayout{
        anchors.fill: parent
        spacing:5
        HeadItem{
        }

        // BdConfigItem{
        //     //标定值显示
        // }
        // }
        // CoilCetItem{}
        // CoilSizeItem{}
        Column{
            Layout.fillWidth: true
        Page__Adjust{
            width: parent.width

        }
        Page__Defects{
            width: parent.width
        }
        }


        W_bj{}

        CoilMourceItem{
            visible: dataShowCore.imageShowHovered
        }

        PedalView{
            visible: dataShowCore.imageShowHovered
        }

        XYZ_List{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        // CoilSizeItem{
        // }
        // CoilCetItem{
        // }
        DefectClassFlow{
        }

    }
}

