import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../Base"

PopupBase {
    id: root

    required property var adaptiveMetrics
    required property var appInfo
    required property var style

    anchors.centerIn: parent
    width: root.adaptiveMetrics.boundedWidth(800, 560, 980)
    height: root.adaptiveMetrics.boundedHeight(500, 380, 680)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.adaptiveMetrics.scaleMetric(2, 2, 4)
        spacing: root.adaptiveMetrics.mainSpacing

        Label {
            text: qsTr("系统信息")
            font.pixelSize: root.adaptiveMetrics.fontMetric(22, 18, 28)
            font.bold: true
            color: root.style.titleColor
            Layout.alignment: Qt.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: root.style.headerBorderColor
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
                        text: qsTr("原始图像 S 端: ")
                              + (root.appInfo.originalImageFolderS || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("原始图像 L 端: ")
                              + (root.appInfo.originalImageFolderL || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("保存图像 S 端: ")
                              + (root.appInfo.saveImageFolderS || qsTr("未知"))
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                    Label {
                        text: qsTr("保存图像 L 端: ")
                              + (root.appInfo.saveImageFolderL || qsTr("未知"))
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
                Label { text: root.appInfo.pythonVersion || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("服务版本:") }
                Label { text: root.appInfo.serverVersion || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("缓存方式:") }
                Label { text: root.appInfo.cacheMode || qsTr("未知"); wrapMode: Text.NoWrap }

                Label { text: qsTr("CPU 型号:") }
                Label { text: root.appInfo.cpuModel || qsTr("未知"); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }

                Label { text: qsTr("GPU 型号:") }
                Label {
                    text: root.appInfo.gpuModels || qsTr("未知")
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }

                Label { text: qsTr("数据库:") }
                Label { text: root.appInfo.databaseUrl || qsTr("未知"); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
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
