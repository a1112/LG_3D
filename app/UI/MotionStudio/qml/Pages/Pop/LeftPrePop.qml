import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Model"
Menu {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var hoverController
    required property var modelStore
    required property var toolService
    required property var globalContext
    required property var apiClient

    property bool isHoved: root.hoverController.isHoved
    onIsHovedChanged: {
            if  (isHoved){
                 popup()

            }
    }
    visible: isHoved
    x: root.style.leftWidth + root.adaptiveMetrics.headerSideGap
    y: Math.max(
           root.adaptiveMetrics.headerSideGap,
           Math.min(
               root.hoverController.hoverPoint.y,
               root.hoverController.hoverPoint.y - height
               - root.adaptiveMetrics.headerSideGap))
    width: root.adaptiveMetrics.boundedWidth(620, 460, 760)
    height: col.height + root.adaptiveMetrics.mainSpacing * 3
    property int body_width:
        width - root.adaptiveMetrics.mainSpacing * 2
    property CoilModel coilModel: root.hoverController.hovedCoilModel

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
            font.pointSize: root.adaptiveMetrics.fontMetric(20, 16, 24)
        }
        ImageRow{
            width:parent.width
            Layout.fillWidth:true
            hoverController: root.hoverController
            style: root.style
        }
        AreaRow{
            width:parent.width
            Layout.fillWidth:true
            hoverController: root.hoverController
            modelStore: root.modelStore
            style: root.style
        }
        CoilInfo{
            width:parent.width
            Layout.fillWidth:true
            height: root.adaptiveMetrics.scaleMetric(100, 80, 130)
            coilModel: root.coilModel
        }
        AlarmInfo{
            width:parent.width
            Layout.fillWidth:true
            hoverController: root.hoverController
        }
        // 塔形数据表格（显示所有数据）
        TaperShapeTable{
            width:parent.width
            Layout.fillWidth:true
            height: root.adaptiveMetrics.scaleMetric(120, 95, 155)
            coilModel: root.coilModel
            style: root.style
        }
        // TextArea{
        //     text:leftCore.leftMsg
        // }
        DefectInfo{
            width:parent.width
            Layout.fillWidth:true
            coilModel: root.coilModel
            respectFilter: false
            thumbnailSize: root.adaptiveMetrics.scaleMetric(96, 72, 120)
            toolService: root.toolService
            filterController: root.hoverController
            globalContext: root.globalContext
            apiClient: root.apiClient
        }

    }







}
