import QtQuick
import QtQuick.Controls
import "../../Model/server"

Item {
    id: root

    required property int index
    required property var model
    required property var style
    required property var menuController

    property DefectItemModel defectItem: DefectItemModel {}
    readonly property bool hovered: hoverHandler.hovered

    function syncModel() {
        defectItem.init(model)
    }

    onIndexChanged: syncModel()
    GridView.onReused: syncModel()
    Component.onCompleted: syncModel()

    scale: hovered ? 1.035 : 1
    z: hovered ? 2 : 0

    Behavior on scale {
        NumberAnimation { duration: 120 }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 6
        radius: root.style.controlRadius
        color: root.style.panelElevatedColor
        border.width: root.hovered ? 2 : 1
        border.color: root.hovered ? root.style.accentColor : root.style.headerBorderColor

        Image {
            id: defectImage
            anchors.fill: parent
            anchors.margins: 4
            source: root.defectItem.defect_url
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: false
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: defectCaption.implicitHeight + 12
            color: root.style.headerBackgroundColor
            opacity: 0.94

            Row {
                id: defectCaption
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                Label {
                    text: root.defectItem.defectName || qsTr("未知缺陷")
                    color: root.defectItem.defectColor
                    font.bold: true
                }
                Label {
                    text: root.defectItem.surface + " · ID " + root.defectItem.coilId
                    color: root.style.labelColor
                    font.pixelSize: 11
                }
            }
        }

        BusyIndicator {
            anchors.centerIn: parent
            running: defectImage.status === Image.Loading
            visible: running
            width: 30
            height: 30
        }
    }

    ToolTip.visible: hovered
    ToolTip.delay: 350
    ToolTip.timeout: 5000
    ToolTip.text: qsTr("缺陷：") + defectItem.defectName
                  + "\n" + qsTr("卷材 ID：") + defectItem.coilId
                  + "\n" + qsTr("表面：") + defectItem.surface
                  + "\n" + qsTr("等级：") + defectItem.defectLevel
                  + "\n" + qsTr("位置：") + defectItem.defectX + ", " + defectItem.defectY
                  + "\n" + qsTr("尺寸：") + defectItem.defectW + " × " + defectItem.defectH

    HoverHandler {
        id: hoverHandler
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            root.menuController.defectItem = root.defectItem
            root.menuController.popup()
        }
    }
}
