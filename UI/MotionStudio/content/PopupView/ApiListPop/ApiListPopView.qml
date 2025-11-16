import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Base"
PopupBase {
    width:500
    height:600
    ColumnLayout{
        width:500
        height:600
        TitleLabel{
            text: "API 调用记录"
        }
        ListView{
            Layout.fillHeight: true
            Layout.fillWidth: true
            ScrollBar.vertical: ScrollBar{}
            delegate: ApiListItem{
                width: parent.width
                height: 35
            }
            model: api.urlListModel

        }
    }
}
