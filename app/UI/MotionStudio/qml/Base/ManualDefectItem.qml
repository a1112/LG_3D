import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../Model/server"
import "../../Dialogs"

/**
 * 手动标注缺陷显示项
 * 在图像上显示手动标注的缺陷框
 */
Rectangle {
    id: root

    // 缺陷数据
    property var defect: null

    // 视图缩放比例
    property real canvasScale: 1

    // 是否可以编辑
    property bool editable: true

    // 计算位置和尺寸
    x: defect ? defect.defectX * canvasScale : 0
    y: defect ? defect.defectY * canvasScale : 0
    width: defect ? defect.defectW * canvasScale : 0
    height: defect ? defect.defectH * canvasScale : 0

    color: "transparent"
    border.color: "#FF6B6B"  // 红色边框表示手动标注
    border.width: 2

    // 手动标注标识角标
    Rectangle {
        width: 24
        height: 24
        color: "#FF6B6B"
        radius: width / 2
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.topMargin: -12
        anchors.leftMargin: -12

        Label {
            anchors.centerIn: parent
            text: "注"
            color: "white"
            font.pixelSize: 12
            font.bold: true
        }
    }

    // 缺陷名称标签
    Label {
        visible: global ? global.defectClassProperty.defectDrawShowLasbel : false
        color: "#FF6B6B"
        text: defect ? defect.defectName : ""
        font.pixelSize: 14
        font.bold: true
        anchors.left: parent.right
        anchors.leftMargin: 5
        anchors.verticalCenter: parent.verticalCenter
        background: Rectangle {
            color: "#000000"
            opacity: 0.8
            radius: 3
        }
        padding: 4
    }

    // 鼠标区域
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true

        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton && editable) {
                contextMenu.popup()
            } else if (mouse.button === Qt.LeftButton) {
                // 左键点击可以定位到缺陷
                if (dataShowCore_) {
                    dataShowCore_.setDefectShowView(defect)
                }
            }
        }

        onDoubleClicked: {
            if (editable) {
                defectEditDialog.openForDefect(defect)
            }
        }
    }

    // 右键菜单
    Menu {
        id: contextMenu

        MenuItem {
            text: "查看详情"
            onTriggered: {
                if (dataShowCore_) {
                    dataShowCore_.setDefectShowView(defect)
                }
            }
        }

        MenuSeparator {}

        MenuItem {
            text: "编辑缺陷..."
            visible: editable
            onTriggered: {
                defectEditDialog.openForDefect(defect)
            }
        }

        MenuItem {
            text: "删除缺陷"
            visible: editable
            onTriggered: {
                deleteConfirmDialog.open()
            }
        }
    }

    // 缺陷编辑对话框
    ManualDefectEditDialog {
        id: defectEditDialog

        onDefectUpdated: function(updatedDefect) {
            // 触发刷新
            if (surfaceData) {
                surfaceData.refreshDefects()
            }
        }

        onDefectDeleted: function(deletedId) {
            // 触发刷新
            if (surfaceData) {
                surfaceData.refreshDefects()
            }
        }
    }

    // 删除确认对话框
    Dialog {
        id: deleteConfirmDialog
        title: "确认删除"
        modal: true
        anchors.centerIn: parent

        Label {
            text: "确定要删除此缺陷标注吗？"
        }

        buttons: Row {
            spacing: 10
            layoutDirection: Qt.RightToLeft

            Button {
                text: "取消"
                onClicked: deleteConfirmDialog.close()
            }

            Button {
                text: "删除"
                highlighted: true
                background: Rectangle {
                    color: pressed ? "#D32F2F" : "#F44336"
                    radius: 4
                }
                contentItem: Text {
                    text: "删除"
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    api.deleteManualDefect(defect.Id,
                        function(result) {
                            console.log("删除缺陷成功")
                            deleteConfirmDialog.close()
                            if (surfaceData) {
                                surfaceData.refreshDefects()
                            }
                        },
                        function(error) {
                            console.error("删除缺陷失败:", error)
                        }
                    )
                }
            }
        }
    }
}
