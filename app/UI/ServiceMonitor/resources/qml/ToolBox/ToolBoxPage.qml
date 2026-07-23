import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import Qt.labs.folderlistmodel
Item {
    id:root
    anchors.fill: parent
    clip: true
    property string filePath: currentFilePath
    onFilePathChanged: {
        console.log("currentFilePathChanged ",currentFilePath)
    }

    FolderListModel{
        id: folderModel_
        folder: "file:///"+filePath
        showDirs: false
        showFiles: true
    }

    Flickable{
        anchors.fill: parent
        contentWidth: root.width
        contentHeight: flow.height
        ScrollBar.vertical:ScrollBar{}
        Flow {
            id:flow
            spacing: 10
            width: root.width
            Repeater {
                model:folderModel_

                    ListModel{
                                ListElement{
                                    title: "Python 3.11.7"
                                    icon: "python"
                                    url:"https://www.python.org/downloads/release/python-3116"
                                    exe_path:"I:\\tools\\python-3.11.6-amd64.exe"
                                }
                                    }

                delegate: ToolBoxPageItem {
                    MouseArea{
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: {
                            menu.popup()
                        }
                    }
                }
            }
        }
    }
}
