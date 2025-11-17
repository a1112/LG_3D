import QtQuick
import QtQuick.Controls

ItemDelegateBase {

    property alias iconText:  lb.text
    Label{
        id:lb
    anchors.centerIn: parent
    font.bold: true
    font.family: "黑体"
    scale: 2

    }

}
