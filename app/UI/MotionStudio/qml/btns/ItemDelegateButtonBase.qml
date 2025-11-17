import QtQuick 2.15
import QtQuick.Controls 2.15
import "../Base"
ItemDelegate {
    height: parent.height
    width: height
    property string tipText: ""
    ToolTip.visible: tipText!=="" && hovered
    ToolTip.text: tipText
    property alias source: efi.source
    Item{
        height: parent.height*0.66
        width: height
        anchors.centerIn: parent
        EffectImage{
            id:efi
            height: parent.height
            width: height
        }
    }
}
