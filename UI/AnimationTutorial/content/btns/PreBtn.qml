import QtQuick 2.15
import QtQuick.Controls 2.15
import "../Labels"
import "../Base"
 BtnBase{
        ColorImageButton {
            id: name
//            fillMode: Image.PreserveAspectFit
            source: coreStyle.getIcon("arrow-pre")

        }
        EffectLabel{
            text: qsTr("上一卷")
        }
    }
