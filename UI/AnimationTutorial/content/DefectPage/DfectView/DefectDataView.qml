import QtQuick
import QtQuick.Controls
import Qt.labs.qmlmodels
//
Item {
    id:root
    clip: true
    Flickable{
        anchors.fill: parent
        contentWidth: root.width
        contentHeight: flow.implicitHeight + 20
        ScrollBar.vertical: ScrollBar{}
        Flow{
            width: parent.width
            // flow:Flow.TopToBottom
            id:flow
            spacing: 2
            Repeater{
                model: defectCoreModel.defectsModel
                DefectItemShow{}
            }

        }
    }
}
