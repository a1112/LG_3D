import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "DataListMenu"
import "Core"
import "../../../Model"
import "../../../animation"
Item {


    visible:leftCore.fliterEnable? coilModel.checkDefectShow(leftCore.fliterDict) :true

    property  CoilModel coilModel: CoilModel{}
    Component.onCompleted:{
    coilModel.setCoil(model)
    }

    // property CoilState coilState: CoilState{}
    width: 300
    height: visible?25:0.001
    implicitHeight:height

    property string msg:"流水号："+coilModel.coilId+"\n"+"钢卷号："+coilModel.coilNo+"\n"+"钢卷类型："+
                        coilModel.coilType+"\n"+"状态："+coilModel.coilStatus_S+
                        " "+coilModel.coilStatus_L+"\n"+"外径："+coilModel.coilDia+" 宽度："+
                        coilModel.coilWidth+" 厚度："+coilModel.coilThickness+
                        "\n"+"时间："
                        +coilModel.coilTimeString
                      + listItemCoil.errorMsg

    property ListItemCoil listItemCoil:ListItemCoil{}
    Pane{
        Material.elevation: 7
        anchors.fill: parent
    }
    Rectangle {
        anchors.fill: parent
        color: "#32eeeeee"
        radius: 5
        visible: index%2==0
    }
    Rectangle {
        anchors.fill: parent
        color: "red"
        opacity: 0.3
        radius: 5
        visible: false//index%10==0
    }
    ItemDelegate{
        anchors.fill: parent
        onClicked: {
            core.setCoilIndex(index)
            coreModel.setKeepLatest(false)
        }
    }
    ColumnLayout {
        width: parent.width
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        RowLayout{
            Layout.fillWidth: true
            Rectangle{
                implicitWidth: 2
                implicitHeight: 1
            }
            ColumnLayout{
                spacing: 0
                Layout.fillWidth: true
                implicitHeight: 30
                RowLayout{
                    Label{
                        font.pointSize: 11
                        font.bold: true
                        text: " "+coilModel.coilId
                        color:listItemCoil.detectionStatuColor
                    }
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }
                    Label{
                        text:CoilNo
                        font.bold: true
                        font.pointSize: 12
                    }

                    StateWrapper{
                        // c_state:coilState
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }
                    Label{
                        font.pointSize: 11
                        text: coilModel.coilType
                    }
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }

                    StatusMsg{
                    }
                }
            }
            Item{
                implicitWidth: 5
                implicitHeight: 2
            }
        }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }


    Rectangle{
        width: 3
        height: parent.height
        anchors.bottom: parent.bottom
        color: index==core.coilIndex?"red":"#00000000"
    }
    MouseArea{
        acceptedButtons: Qt.RightButton
        anchors.fill: parent
        onClicked: {
            lefeListMemu.coilModel = coilModel
            lefeListMemu.popup()
        }
    }
    HoverHandler{
        id:hov
        onHoveredChanged: {
            if(hovered){
                leftCore.hovedIndex = index
                leftCore.leftMsg = msg
                leftCore.hovedCoilModel=coilModel
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#00000000"
        radius: 5
        visible: index == core.coilIndex
        border.color:index == core.coilIndex?"orange":"steelblue"
        border.width: index == core.coilIndex?2: 1
        opacity: index == core.coilIndex?0.8: 0.5
    }
    // AnimRec {
    //     visible:listItemCoil.grad>1
    //     anchors.fill:parent
    //     running:listItemCoil.grad>2
    //     runningOpacity:false
    //     radius: 0
    //     color:"#00000000"
    //     border.color: listItemCoil.level2Color(listItemCoil.grad)
    // }


    // ToolTip.visible: hov.hovered
    // ToolTip.text:
}
