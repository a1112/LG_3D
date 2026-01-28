import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../Api"

/**
 * 手动缺陷标注工具
 * 用于在图像上手动添加缺陷标注
 */
Rectangle {
    id: root
    color: "#10000000"
    visible: false

    // 属性
    property bool isActive: false
    property int coilId: 0
    property string surfaceKey: "S"
    property var flickable: null
    property var dataShowCore: null

    // 信号
    signal defectAdded(var defect)
    signal defectCancelled()

    // 绘制状态
    property bool isDrawing: false
    property real startX: 0
    property real startY: 0
    property real currentX: 0
    property real currentY: 0

    // 选择的矩形框（图像坐标）
    property rect selectedRect: Qt.rect(0, 0, 0, 0)

    // 绘制的矩形框
    Rectangle {
        id: drawRect
        visible: root.isDrawing
        color: "#40FF0000"
        border.color: "#FF0000"
        border.width: 2
        x: Math.min(root.startX, root.currentX)
        y: Math.min(root.startY, root.currentY)
        width: Math.abs(root.currentX - root.startX)
        height: Math.abs(root.currentY - root.startY)

        // 显示尺寸标签
        Label {
            anchors.bottom: parent.top
            anchors.left: parent.left
            background: Rectangle { color: "#CC000000"; radius: 3 }
            color: "white"
            padding: 4
            text: {
                let w = Math.round(Math.abs(root.currentX - root.startX) / (dataShowCore ? dataShowCore.canvasScale : 1))
                let h = Math.round(Math.abs(root.currentY - root.startY) / (dataShowCore ? dataShowCore.canvasScale : 1))
                return w + " x " + h
            }
        }
    }

    // 鼠标区域
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.isActive
        cursorShape: Qt.CrossCursor

        onPressed: function(mouse) {
            root.isDrawing = true
            root.startX = mouse.x
            root.startY = mouse.y
            root.currentX = mouse.x
            root.currentY = mouse.y
        }

        onPositionChanged: function(mouse) {
            if (root.isDrawing) {
                root.currentX = mouse.x
                root.currentY = mouse.y
            }
        }

        onReleased: function(mouse) {
            if (root.isDrawing) {
                root.isDrawing = false

                // 计算图像坐标
                let scaleX = dataShowCore ? dataShowCore.canvasScale : 1
                let scaleY = dataShowCore ? dataShowCore.canvasScale : 1
                let contentX = flickable ? flickable.contentX : 0
                let contentY = flickable ? flickable.contentY : 0

                let imgX = Math.round((Math.min(root.startX, root.currentX) + contentX) / scaleX)
                let imgY = Math.round((Math.min(root.startY, root.currentY) + contentY) / scaleY)
                let imgW = Math.round(Math.abs(root.currentX - root.startX) / scaleX)
                let imgH = Math.round(Math.abs(root.currentY - root.startY) / scaleY)

                // 忽略太小的框
                if (imgW < 10 || imgH < 10) {
                    return
                }

                root.selectedRect = Qt.rect(imgX, imgY, imgW, imgH)

                // 打开缺陷类型选择对话框
                defectTypeDialog.open()
            }
        }
    }

    // 缺陷类型选择对话框
    Dialog {
        id: defectTypeDialog
        title: "添加缺陷标注"
        modal: true
        anchors.centerIn: parent
        width: 400
        height: 350

        property var selectedDefectName: ""

        Column {
            spacing: 15
            anchors.fill: parent

            // 位置信息
            GroupBox {
                title: "缺陷位置"
                width: parent.width

                Row {
                    spacing: 20
                    Label { text: "X:"; font.bold: true }
                    Label { text: root.selectedRect.x.toString() }
                    Label { text: "Y:"; font.bold: true }
                    Label { text: root.selectedRect.y.toString() }
                    Label { text: "宽:"; font.bold: true }
                    Label { text: root.selectedRect.width.toString() }
                    Label { text: "高:"; font.bold: true }
                    Label { text: root.selectedRect.height.toString() }
                }
            }

            // 缺陷类型选择
            GroupBox {
                title: "缺陷类型"
                width: parent.width

                ComboBox {
                    id: defectTypeCombo
                    width: parent.width
                    model: global ? global.defectClassProperty.getDefectNameList() : []

                    onCurrentIndexChanged: {
                        if (currentIndex >= 0) {
                            defectTypeDialog.selectedDefectName = currentText
                        }
                    }
                }
            }

            // 备注输入
            GroupBox {
                title: "备注（可选）"
                width: parent.width

                TextField {
                    id: remarkInput
                    width: parent.width
                    placeholderText: "输入备注信息..."
                }
            }

            // 按钮区域
            Row {
                spacing: 10
                layoutDirection: Qt.RightToLeft

                Button {
                    text: "取消"
                    onClicked: {
                        remarkInput.text = ""
                        defectTypeDialog.close()
                    }
                }

                Button {
                    text: "确定"
                    highlighted: true
                    onClicked: {
                        addDefect()
                        remarkInput.text = ""
                        defectTypeDialog.close()
                    }
                }
            }
        }
    }

    // 添加缺陷
    function addDefect() {
        let defectData = {
            secondaryCoilId: root.coilId,
            surface: root.surfaceKey,
            defectName: defectTypeDialog.selectedDefectName || "未知缺陷",
            defectX: root.selectedRect.x,
            defectY: root.selectedRect.y,
            defectW: root.selectedRect.width,
            defectH: root.selectedRect.height,
            remark: remarkInput.text,
            annotator: "系统用户"
        }

        api.addManualDefect(defectData,
            function(result) {
                console.log("添加缺陷成功:", result)
                defectAdded(result)
            },
            function(error) {
                console.error("添加缺陷失败:", error)
            }
        )
    }

    // 激活标注工具
    function activate() {
        root.isActive = true
        root.visible = true
    }

    // 停用标注工具
    function deactivate() {
        root.isActive = false
        root.isDrawing = false
        root.visible = false
    }

    // 取消当前绘制
    function cancelDrawing() {
        root.isDrawing = false
    }
}
