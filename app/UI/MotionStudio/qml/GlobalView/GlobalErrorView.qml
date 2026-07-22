import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root

    readonly property int alarmCode: coreModel.coreGlobalError.errorCode
    readonly property string alarmSummary: alarmCode === 3001
                                                ? qsTr("相机采集异常")
                                                : coreModel.coreGlobalError.errorStr
    readonly property string alarmText: qsTr("报警 %1 · %2")
                                        .arg(alarmCode)
                                        .arg(alarmSummary)
    readonly property string alarmDetail: qsTr("报警 %1 · %2")
                                          .arg(alarmCode)
                                          .arg(coreModel.coreGlobalError.errorStr)

    width: parent ? Math.min(implicitWidth, parent.width) : implicitWidth
    height: adaptive.headerTabHeight
    implicitWidth: adaptive.scaleMetric(420, 300, 560)
    visible: coreModel.coreGlobalError.hasError
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Qt.rgba(0.75, 0.18, 0.18, 0.16)
        border.color: Qt.rgba(1, 0.45, 0.35, 0.5)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: adaptive.scaleMetric(8, 6, 10)
        anchors.rightMargin: adaptive.scaleMetric(10, 8, 12)
        spacing: adaptive.scaleMetric(6, 4, 8)

        Image {
            Layout.preferredWidth: adaptive.scaleMetric(20, 16, 24)
            Layout.preferredHeight: Layout.preferredWidth
            fillMode: Image.PreserveAspectFit
            source: coreStyle.getIcon("warning_1")
        }

        Label {
            Layout.fillWidth: true
            verticalAlignment: Text.AlignVCenter
            font.family: "Microsoft YaHei"
            font.pixelSize: adaptive.fontMetric(15, 13, 18)
            font.bold: true
            color: Material.color(Material.Red)
            text: root.alarmText
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }

    HoverHandler {
        id: hoverHandler
    }

    ToolTip.visible: hoverHandler.hovered
    ToolTip.delay: 500
    ToolTip.text: root.alarmDetail
}
