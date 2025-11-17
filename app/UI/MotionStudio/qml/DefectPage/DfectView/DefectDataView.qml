import QtQuick
import QtQuick.Controls
import Qt.labs.qmlmodels
//
Item {
    id:root
    clip: true

        GridView {
            anchors.fill: parent
            id : grid
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

