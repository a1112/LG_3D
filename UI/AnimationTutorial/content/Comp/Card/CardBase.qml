import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../animation"
Item {
    id:root
    property alias title: title_id.text
    property alias content_head_tool: title_row.children
    property alias content_body: content_row.children
    property bool isShow: true
    property bool showError:false
    height: isShow? max_height : 35
    SplitView.preferredHeight:isShow?max_height:35


    onIsShowChanged:{
        content_body.visible=isShow
    }
    property int max_height: 120
    // height:columnLayout.height
    Pane{
        width: parent.width
        height: parent.height-5
        Material.elevation: 6
    }
    Rectangle{
        opacity:0.5
        color:"transparent"
        anchors.fill: parent
        border.color: showError?app.coreStyle.cardBorderErrorColor:app.coreStyle.cardBorderColor
        border.width: 1
    }
    ItemDelegate{
        anchors.fill: parent
    }

    ColumnLayout{
        id:columnLayout
        width: parent.width
        Item{
            Layout.alignment: Qt.AlignHCenter
            implicitHeight :title_row.height
            Layout.fillWidth: true
        Row{
            id:title_row
            anchors.horizontalCenter: parent.horizontalCenter
            Layout.alignment: Qt.AlignHCenter
            AnimErrorLabel{
                id:title_id
                text: ""
                running: root.showError
                baseColor: app.coreStyle.titleColor
                font.pixelSize: 22
                font.bold:true
            }
            Item{
                width:20
                height:10
            }
        }
            ItemDelegate{
                height:parent.height
                width:height
                Label{
                    visible:auth.isAdmin
                    font.pointSize:18
                    text: "►"
                    color:root.showError?app.coreStyle.cardBorderErrorColor:app.coreStyle.labelColor
                    rotation: root.isShow?90:0
                    anchors.centerIn: parent
                }
                onClicked:{
                    root.isShow=!root.isShow
                }
            }


        }
        ColumnLayout{
        id:content_row
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: root.isShow
        }
    }
}
