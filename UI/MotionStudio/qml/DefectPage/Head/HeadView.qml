import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Base"
Item{
    id:root
    Image {
        id:image
        width: parent.width
        fillMode: Image.PreserveAspectFit
        source: "../../images/head.png"
        }
    USTB{
        x: root.width*0.08
        scale: 0.7
    }
    TitleText{
        anchors.centerIn: parent
    }
    TimeText{
        y:10
        x: root.width-root.width*0.05 - width
        scale: 0.7
    }
}
