import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
Item {
    id:root

    required property var controller
    required property var defectClassController

    height:25
    Layout.fillWidth: true

    Pane{
        anchors.fill:parent
        Material.elevation:5
    }

    RowLayout{
        anchors.fill:parent
        ShowDefectNamesRow{
            model: root.controller.defecClassListModel
            controller: root.controller
            defectClassController: root.defectClassController
            Layout.fillWidth: true
            Layout.fillHeight:true
        }
        ShowTools{
           Layout.fillHeight:true
           controller: root.controller
           defectClassController: root.defectClassController
        }
    }
}
