import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../Base"

PopupBase {
    id: root
    anchors.centerIn: parent
    width: 800
    height: 500

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 8

        Label {
            text: qsTr("系统信息")
            font.pixelSize: 22
            font.bold: true
            color: Material.color(Material.Blue)
            Layout.alignment: Qt.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Material.color(Material.Grey)
        }

        ColumnLayout{
            id:infoC
            Layout.fillWidth: true
            GroupBox {
                title: qsTr("图像保存路径")
                Layout.fillWidth: true
                contentHeight:c1.height
                ColumnLayout {
                    id:c1
                    Layout.fillWidth: true
                    anchors.margins: 3
                    spacing: 4

                    Label {
                        text: qsTr("原始图像 S 端: ") + (app.coreInfo.originalImageFolderS || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("原始图像 L 端: ") + (app.coreInfo.originalImageFolderL || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("保存图像 S 端: ") + (app.coreInfo.saveImageFolderS || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("保存图像 L 端: ") + (app.coreInfo.saveImageFolderL || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                }
            }

        }

        // 保存路径




        // 运行环境
        GroupBox {
            title: qsTr("运行环境")
            Layout.fillWidth: true

            GridLayout {
                columns: 2
                anchors.fill: parent
                anchors.margins: 8
                rowSpacing: 4
                columnSpacing: 16

                Label { text: qsTr("Python 版本:") }
                Label { text: app.coreInfo.pythonVersion || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("服务版本:") }
                Label { text: app.coreInfo.serverVersion || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("缓存方式:") }
                Label { text: app.coreInfo.cacheMode || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("CPU 型号:") }
                Label { text: app.coreInfo.cpuModel || qsTr("未知"); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }

                Label { text: qsTr("GPU 型号:") }
                Label {
                    text: app.coreInfo.gpuModels || qsTr("未知")
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }

                Label { text: qsTr("数据库:") }
                Label { text: app.coreInfo.databaseUrl || qsTr("未知"); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: qsTr("关闭")
                Layout.alignment: Qt.AlignRight
                onClicked: root.close()
            }
        }
    }
}
