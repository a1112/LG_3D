import QtQuick 2.15

import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "../Base"
DropShadowRec{
    id:root
    property alias source: image.source
    property string tipText: ""
    ToolTip.visible: tipText!=="" && itemD.hovered
    ToolTip.text: tipText
    color:"#00000000"

    signal clicked

    ItemDelegate{
        id:itemD
        anchors.fill: parent
        onClicked: {
            root.clicked()
        }
    }

    Item{
        anchors.fill: parent
        Image{
            id:image
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit

        }
    }


}
