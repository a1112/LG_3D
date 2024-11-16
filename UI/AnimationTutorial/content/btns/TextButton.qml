import QtQuick 2.15
import QtQuick.Controls 2.15

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
