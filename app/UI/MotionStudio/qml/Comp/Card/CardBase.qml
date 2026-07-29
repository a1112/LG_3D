import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../animation"
Item {
    id:root

    required property var cardStyle
    required property var cardAuthManager

    property alias title: title_id.text
    property bool title_vis: title_id.visible
    property alias content_head_tool: title_row.children
    property alias content_body: content_row.children
    property bool isShow: true
    property bool showError:false
    height: isShow? max_height : 35
    SplitView.preferredHeight: isShow?max_height:35
    property int max_height: 120
    // height:columnLayout.height
    Pane{
        width: parent.width
        height: parent.height-5
        Material.elevation: 6
        Material.background: root.cardStyle.panelElevatedColor
    }
    Rectangle{
        anchors.fill: parent
        color: root.cardStyle.panelElevatedColor
        border.color: root.showError ? root.cardStyle.cardBorderErrorColor
                                     : root.cardStyle.cardBorderColor
        border.width: 1
    }
    ItemDelegate{
        id: cardDelegate
        anchors.fill: parent
        background: Rectangle {
            color: cardDelegate.hovered ? root.cardStyle.buttonHoverColor
                                        : root.cardStyle.panelElevatedColor
        }
    }

    ColumnLayout{
        id:columnLayout
        width: parent.width
        spacing: 5
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
                baseColor: root.cardStyle.titleColor
                font: Qt.font({
                    family: "Microsoft YaHei",
                    pixelSize: 22,
                    bold: true
                })
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
                    visible: root.cardAuthManager.isAdmin
                    font.pointSize:18
                    text: "►"
                    color: root.showError ? root.cardStyle.cardBorderErrorColor
                                          : root.cardStyle.labelColor
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
