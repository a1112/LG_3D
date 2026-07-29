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
    x: left.width + adaptive.headerSideGap
    y: Math.max(adaptive.headerSideGap, Math.min(leftCore.hoverPoint.y, leftCore.hoverPoint.y - height - adaptive.headerSideGap))
    width: adaptive.boundedWidth(620, 460, 760)
    height: col.height + adaptive.mainSpacing * 3
    property int body_width: width - adaptive.mainSpacing * 2
    property CoilModel coilModel:leftCore.hovedCoilModel

    // onClosed:{
    //     leftCore.isHoved = false
    //     leftCore.isHoved = true
    // }

    Label{    // title
        text:qsTr("数据摘要")
        anchors.left: parent.left
        color:Material.color(Material.Orange)
    }
    Column{
        id:col
        width:parent.width
        spacing:0
        TitleLabel{
            Layout.fillWidth:true
            text:root.coilModel ? root.coilModel.coilNo || "" : ""
            color:Material.color(Material.Blue)
            Layout.alignment:Qt.AlignHCenter
            anchors.horizontalCenter:parent.horizontalCenter
            font.pointSize: adaptive.fontMetric(20, 16, 24)
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
            height: adaptive.scaleMetric(100, 80, 130)
            coilModel: root.coilModel
        }
        AlarmInfo{
            width:parent.width
            Layout.fillWidth:true
        }
        // 塔形数据表格（显示所有数据）
        TaperShapeTable{
            width:parent.width
            Layout.fillWidth:true
            height: adaptive.scaleMetric(120, 95, 155)
            coilModel: root.coilModel
        }
        // TextArea{
        //     text:leftCore.leftMsg
        // }
        DefectInfo{
            width:parent.width
            Layout.fillWidth:true
            coilModel: root.coilModel
            respectFilter: false
            thumbnailSize: adaptive.scaleMetric(96, 72, 120)
        }

    }







}
