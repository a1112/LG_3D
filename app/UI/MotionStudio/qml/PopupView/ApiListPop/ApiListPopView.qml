import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Base"
PopupBase {
    id: root
    width: adaptive.boundedWidth(500, 380, 640)
    height: adaptive.boundedHeight(600, 420, 760)
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
                height: adaptive.headerTabHeight
            }
            model: api.urlListModel

        }
    }
}
