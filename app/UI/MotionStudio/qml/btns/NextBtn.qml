import QtQuick 2.15
import QtQuick.Controls 2.15
import "../Labels"
import "../Base"
 BtnBase{
        EffectLabel{
            text: qsTr("下一卷")
        }
        ColorImageButton {
            id: name
            height: parent.height
            width: height
            source: coreStyle.getIcon("arrow-next")
            scale: hovered && cliac_enabled ?1.3:1
            Behavior on scale {
            NumberAnimation{
            duration: 300
            }
            }
        }
    }
