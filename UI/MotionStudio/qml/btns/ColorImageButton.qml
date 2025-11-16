import QtQuick 2.14
import QtQuick.Layouts 1.14
import QtQuick.Controls 2.14
import QtQuick.Controls.Material 2.14
import Qt5Compat.GraphicalEffects
import "../Base"
Item{
    id:root
    height: parent.height
    width: height
    property bool selected: false
    property string selectColor:""
    property alias source: efi.source
    Item{
        height: parent.height*0.9
        width: height
        anchors.centerIn: parent
        Image{
            visible: !root.selectColor
            id:efi
            height: parent.height
            width: height
            fillMode: Image.PreserveAspectFit
        }
        ColorOverlay {
            visible: root.selectColor
            width: efi.width
            height: efi.height
            anchors.centerIn: parent
            source: efi
            color:root.selectColor?root.selectColor:"#29FFEF"
            layer.enabled: true
            layer.effect:DropShadowBase{}
        }
    }
}
