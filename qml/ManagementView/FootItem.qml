import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    height: 30
    RowLayout {
        anchors.fill: parent
        Row{
            Layout.fillHeight: true
            ButtonBase {
                text: "全部关闭"
                onClicked: {
                    stopAll()
                }
            }
            ButtonBase {
                text: "全部开启"
                onClicked: {
                    startAll()
                }
            }
            ButtonBase {
                text: "一键重启"
                Material.background: Material.Teal
                onClicked: {
                    restartAll()
                }
            }
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        Row{
            height: parent.height
            ButtonBase {
                text: "重新加载"
                onClicked: {
                    initMonitor()
                }
            }
            ButtonBase {
                text: "保存"
                enabled: monitor.configHasChanged
                Material.background: Material.Blue
                onClicked: {
                    monitor.saveConfig()
                }
            }

            ItemDelegate{
                text: "服务: <link>"+"http://0.0.0.0:8011"+"</link>"
                height: parent.height
                onClicked: {
                    Qt.openUrlExternally("http://127.0.0.1:8011/docs")
                }
            }

            ItemDelegate{
                text: "LOG"
                height: parent.height
                onClicked: {
                    let path = monitor.getLogPath()
                    Qt.openUrlExternally("file:///"+path)
                }
            }
            ItemDelegate{
                text: "CONFIG"
                height: parent.height
                onClicked: {
                    let path = monitor.getConfigPath()
                    Qt.openUrlExternally("file:///"+path)
                }
            }
        }
    }

}
