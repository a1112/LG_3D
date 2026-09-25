pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Base"
PopupBase {
    id: root
    required property var adaptiveMetrics
    required property var apiClient
    required property var style

    width: root.adaptiveMetrics.boundedWidth(620, 460, 820)
    height: root.adaptiveMetrics.boundedHeight(600, 420, 760)
    ColumnLayout{
        anchors.fill: parent
        TitleLabel{
            text: "API 调用记录"
        }
        ListView{
            id: apiListView
            Layout.fillHeight: true
            Layout.fillWidth: true
            ScrollBar.vertical: ScrollBar{}
            delegate: ApiListItem{
                width: apiListView.width
                height: root.adaptiveMetrics.scaleMetric(34, 30, 44)
                style: root.style
            }
            model: root.apiClient.urlListModel

            Label {
                anchors.centerIn: parent
                visible: apiListView.count === 0
                text: qsTr("暂无 API 调用记录")
                color: root.style.secondaryTextColor
            }

        }
    }
}
