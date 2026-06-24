import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import Qt.labs.folderlistmodel
Item {

    property string folder_source: "file:///I:/tools"
    property string currentFilePath: ""
    FolderDialog{
        id: folderDialog
        onAccepted: {
            folder_source = folderDialog.selectedFolder
        }
    }
    Menu{
        id: menu
        MenuItem{
            text: "打开安装包位置"
            onClicked: {
                Qt.openUrlExternally(currentFilePath)
            }
        }
        MenuItem{
            text: "删除"
        }
    }
    Menu{
        id: mainMenu
        MenuItem{
            text: "打开工具箱位置"
            onClicked: {
                Qt.openUrlExternally(folder_source)
            }
        }
        MenuItem{
            text: "更改工具箱位置"
            onClicked: {
                folderDialog.open()
            }
        }
    }

    SplitView{
        anchors.fill: parent
        Item{
            SplitView.fillHeight: true
            SplitView.preferredWidth: 120
            id: leftPane

            ColumnLayout{
                anchors.fill: parent
                Item{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                ListView{
                    id:list
                    anchors.fill: parent

                    model: FolderListModel{
                        folder : folder_source
                        showDirs: true
                        showFiles: false
                    }
                    highlight: Rectangle{
                        color: "#06967E"
                        radius: 5
                        width: parent.width-5
                        border.color: "lightblue"
                    }
                    delegate: ItemDelegate{
                        text: fileName
                        width:leftPane.width
                        font.bold: true
                        onClicked: {
                            list.currentIndex = index
                            currentFilePath=filePath
                        }
                    }
                }
                }
                ItemDelegate{
                    height: 25
                    Layout.fillWidth: true
                    text: folder_source.substring(8)
                    onClicked: {
                        folderDialog.open()
                    }
                }
            }

        }
        Item{
            SplitView.fillHeight: true
            SplitView.fillWidth: true
            id: rightPane
            MouseArea{
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                onClicked:{
                    mainMenu.popup()
                }
            }
            ToolBoxPage{
            }
        }
    }
}
