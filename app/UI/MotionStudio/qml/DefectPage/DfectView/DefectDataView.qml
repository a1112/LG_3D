import QtQuick
import QtQuick.Controls
import Qt.labs.qmlmodels
//
Item {
    id:root
    clip: true

    ScrollView {
        anchors.fill: parent
        clip: true

        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        ScrollBar.horizontal.policy: ScrollBar.AsNeeded

        GridView {
            id : grid
            width: parent.width
            height: parent.height
            // flow:Flow.TopToBottom
            cellHeight: 200
            cellWidth: 200
            model: defectCoreModel.defectsModel

            highlight: Rectangle { color: "lightsteelblue"; radius: 5 }

            delegate:Loader{
                height: 200
                width: height
                asynchronous: true
                sourceComponent: DefectItemShow{}
            }
        }
    }
}

