import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
/*


*/
import "BaseSetting"
import "OtherSetting"
import "D3Setting"
import "GeneralSetting"
import "AlarmSetting"
Popup {
    anchors.centerIn: parent
    width: 1000
    height: 650
    Material.elevation:12
    ColumnLayout{
    anchors.fill: parent
        TitleRow{
            Layout.alignment: Qt.AlignHCenter
            text:"设置"
            font.pointSize:30
        }
        TabBar{
            id:tabBar
            Layout.fillWidth: true

            TabButton{
                text:qsTr("常规设置")
            }
            TabButton{
                text:qsTr("报警设置")
            }
            TabButton{
                text:qsTr("3D渲染设置")
            }
            TabButton{
                text:qsTr("其他")
            }
        }

            StackLayout{

                Layout.fillHeight: true
                Layout.fillWidth: true
                currentIndex: tabBar.currentIndex
                GeneralSetting{
                }

                AlarmSetting{
                }

                D3Setting{
                }

                OtherSetting{
                }

            }

    }
}
