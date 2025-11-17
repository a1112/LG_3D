import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
 ItemDelegate{
    RowLayout{
        anchors.fill: parent
        Label{
            text: timeString
            color: "green"
        }
        Label{
            text: type
        }
        Label{
            textFormat: Text.RichText
            Layout.fillWidth: true
            text:'<a href="'+url+'">'+url+'</a>'
        }
    }
    onClicked: {
        Qt.openUrlExternally(url)
    }
}
