import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts
import LG3D
import QtQuick3D 6.3
import Quick3DAssets._1_矫直线
Item {
    id:root
    height: 45
    width: 1000
    RowLayout{
        anchors.fill: parent
        height:parent.height-5
        spacing: 10
        Row{
        CheckDelegate{
         text: "平移"
         height: root.height
         checked: ContCore.currentType===ContCore.ContType.MoveType
         onCheckedChanged: {
            if (checked){
            ContCore.currentType=ContCore.ContType.MoveType
            }
         }
        }
        CheckDelegate{
            text: "旋转"
            height: root.height
            checked: ContCore.currentType===ContCore.ContType.RatateType
            onCheckedChanged: {
               if (checked){
               ContCore.currentType=ContCore.ContType.RatateType
               }
            }
        }
        CheckDelegate{
            text: "测量"
            height: root.height
        }
        Button{
            text: "重置"
            height: root.height
            onClicked: {
                ContCore.resetPoint()
            }
        }
        Slider{
            width: 200
            height: parent.height
            from: 0
            to:2000
            Component.onCompleted: ContCore.slider=this
        }

        }

        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Label{
            text: "3D钢卷检测"
            font.bold: true
            font.pointSize: 18
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        // TabToolItem{


        // }
        // TabToolItem{

        // }
    }

    Item {
        id: __materialLibrary__
    }
}
