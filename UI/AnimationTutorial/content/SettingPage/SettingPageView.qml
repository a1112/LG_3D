import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
/*


*/
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
                text:"常规设置"
            }
            TabButton{
                text:"报警设置"
            }
            TabButton{
                text:"3D渲染设置"
            }
            TabButton{
                text:"其他"
            }
        }
        Item{
            Layout.fillHeight: true
            Layout.fillWidth: true
            StackLayout{

            }
        }
    }
}
