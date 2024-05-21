import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
Item {
    id:root
    Pane{
        anchors.fill: parent
        Material.elevation: 2

    }
    RowLayout {
        spacing: 0
        anchors.fill: parent
        Item{
            height: parent.height
            width: height
        Image{
            width: parent.width
            height: parent.height
            fillMode: Image.PreserveAspectFit
            source: "image://icon/"+DisplayName
            asynchronous : true
        }
        }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout{
                anchors.fill: parent
                ColumnLayout{
                    Label{
                        font.pixelSize: comtText.font.pixelSize+2
                        font.bold: true
                        text: DisplayName
                    }
                    Label{
                        id:comtText
                        text: "出品公司: "+Publisher
                    }

                }
                Item{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
                Item{
                    height: 34
                    width: 100
                    anchors.verticalCenter: parent.verticalCenter
            Button{
                height: 34
                text: "卸载"

                Material.background: Material.Blue
                onClicked: {
                    core.system(UninstallString)
                }
            }
                }
            }
        }
    }


}
