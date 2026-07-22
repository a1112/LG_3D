import QtQuick 2.15
import QtQuick.Layouts
import QtQuick.Controls.Material

ItemDelegate {
    width: parent.width
    height: 60
    spacing: 40
    property int item_state: -2
    Timer{
        interval: 500
        running: true
        repeat: true
        onTriggered: {
            item_state=getState_(name)
        }
    }
    Frame{
        anchors.fill: parent
    }
    RowLayout{
        anchors.fill: parent
        Item{
            height: parent.height
            width: height
            Image {
                width: parent.width
                height: parent.height
                fillMode: Image.PreserveAspectFit
                source: "image://icon/"+exe
            }
        }

        Column {
            spacing: 5
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            Row{Label {
                    text:"名称："
                    font.bold: true
                    font.pointSize: 15
                }
                Label {
                    color: stateDict[item_state].color
                    text:name
                    font.bold: true
                    font.pointSize: 15
                }
                Label {
                    text:" 运行参数 "+args
                    font.bold: true
                    font.pointSize: 12
                }
            }
            Label {
                text:"路径： "+  exe
                font.pointSize: 11
            }
        }
        Column{
            spacing: 5
            Label {
                text:"延时启动： "+delay+ " s"
                color: "#eee"
                font.pointSize: 12
            }

            Row{
                spacing: 0
                Label {
                    text:"状态："
                    font.pointSize: 13
                }
                Label {
                    text: stateDict[item_state].text
                    font.pointSize: 13
                    font.bold: true
                    color: stateDict[item_state].color
                }
            }
        }
        Column{
            Row{
                spacing: 5
                CheckDelegate{
                    height: 25
                    text: "启动监控"
                    checked: monitorAble
                    onCheckedChanged: {
                        changeValue(index,"monitorAble",checked)
                    }
                }
                Label{
                    text: index
                }
            }
            Row{
                height: 35
                Button{
                    height: 35
                    text: "停止"
                    enabled: item_state==1
                    onClicked: {
                        stopExe(exe)
                    }
                }
                Button{
                    height: 35
                    enabled: item_state==0
                    text: "启动"
                    onClicked: {
                        startExe(exe)
                    }
                }
                Button{
                    height: 35
                    enabled: item_state!=-1
                    text: "重启"
                    Material.background: Material.Teal
                    onClicked: {
                        restartExe(name)
                    }
                }
            }
        }
    }
    Menu{
        id:menu
        MenuItem{
            text: "打开文件夹"
            onClicked: {
                Qt.openUrlExternally("file:///"+monitor.dirName(exe))
            }
        }
        MenuItem{
            text: "修改"
            onClicked: {
                dialogPop.editExe(index)
            }
        }
        MenuItem{
            text: "停止"
            enabled: item_state==1
            onClicked: {stopExe(exe)}
        }
        MenuItem{
            text: "启动"
            enabled: item_state==0
            onClicked: {startExe(name)}
        }
        MenuItem{
            text: "重启"
            enabled: item_state!=-1
            onClicked: {restartExe(name)}
        }
        MenuItem{
            text: "删除"
            onClicked: {
                removeItem(index)
            }
        }
    }
    MouseArea{
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: {
            menu.popup()
        }
    }

}

