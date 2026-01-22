import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Model"
Menu {
    property  bool isHoved: leftCore.isHoved
    onIsHovedChanged: {
            if  (isHoved){
                 popup()

            }
    }
    visible: isHoved
    id:root
    x: left.width+20
    y:Math.max(20,Math.min(leftCore.hoverPoint.y,leftCore.hoverPoint.y-height-20))
    width:620 //col.width+20
    height:col.height+30
    property int body_width:width-20
    property CoilModel coilModel:leftCore.hovedCoilModel

    // onClosed:{
    //     leftCore.isHoved = false
    //     leftCore.isHoved = true
    // }

    Label{    // title
        text:qsTr("数据摘要")
        anchors.left: parent.Left
        color:Material.color(Material.Orange)
    }
    Column{
        id:col
        width:parent.width
        spacing:0
        TitleLabel{
            Layout.fillWidth:true
            text:coilModel.coilNo
            color:Material.color(Material.Blue)
            Layout.alignment:Qt.AlignHCenter
            anchors.horizontalCenter:parent.horizontalCenter
            font.pointSize: 20
        }
        ImageRow{
            width:parent.width
            Layout.fillWidth:true
        }
        AreaRow{
            width:parent.width
            Layout.fillWidth:true
        }
        CoilInfo{
            width:parent.width
            Layout.fillWidth:true
            height: 100
        }
        AlarmInfo{
            width:parent.width
            Layout.fillWidth:true
        }
        // 塔形数据表格（显示所有数据）
        TaperShapeTable{
            width:parent.width
            Layout.fillWidth:true
            height: 120
            coilModel: root.coilModel
        }
        // TextArea{
        //     text:leftCore.leftMsg
        // }
        DefectInfo{
            width:parent.width
            Layout.fillWidth:true
        }

    }







}
