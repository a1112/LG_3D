import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "ProcessView"
import "ManagementView"
import "DiskView"
import "ToolBox"
import "core"
import "SoftViewPage"
import "DeployView"
Item {
    id:root
    anchors.fill: parent
    Material.accent: "#06967E"
    property Core core: Core{}
    property int tabWidth: 100

    ColumnLayout{
        anchors.fill: parent
        RowLayout{
            width: root.width
            TabBar {
                id: bar
                Material.elevation: 5
                TabButton {
                    width: 100
                    text: qsTr("后台管理")
                }
                TabButton {
                    width: tabWidth
                    text: qsTr("磁盘清理")
                }
                TabButton {
                    width: tabWidth
                    text: qsTr("任务管理器")
                }
                TabButton {
                    width: tabWidth
                    text: qsTr("软件管理")
                }
                TabButton {
                    width: tabWidth
                    text: qsTr("部署工具")
                }
                TabButton {
                    width: tabWidth
                    text: qsTr("工具箱")
                }
            }
            Item{
                width: root.width-bar.width-logo.width
                height: 1
            }
            Row{
                Layout.fillWidth: true
                height: bar.height
                Image {
                    id: logo
                    width: parent.width
                    height: parent.height
                    fillMode: Image.PreserveAspectFit
                    source: "icons/USTB.png"
                    MouseArea{
                        anchors.fill: parent
                        onClicked: {
                            isDark=!isDark
                        }
                    }
                }
            }
        }
        StackLayout{
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex
            Loader{
                asynchronous: true
                width: parent.width
                height: parent.height
                sourceComponent:
                    ManagementViewPage{
                }
            }
            Loader{
                asynchronous: true
                width: parent.width
                height: parent.height
                sourceComponent:
              DiskViewPage{
                }
            }
            ProcessViewPage{
                width: parent.width
                height: parent.height
            }
            Loader{
                asynchronous: true
                width: parent.width
                height: parent.height
                sourceComponent:
                    SoftView{
                }
            }
            Loader{
                asynchronous: true
                width: parent.width
                height: parent.height
                sourceComponent:
                DeployViewPage{}
            }
            Loader{
                asynchronous: true
                width: parent.width
                height: parent.height
                sourceComponent:
                    ToolBoxView{
                }
            }
        }
    }

}
