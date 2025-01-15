import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
Item {
    id:root
    height:25
    Layout.fillWidth: true

    Pane{
        anchors.fill:parent
        Material.elevation:5
    }
    RowLayout{
        anchors.fill:parent
        ShowDefectNamesRow{
            model: dataShowCore.defecClassListModel // global.defectClassProperty.defectDictModel // dataShowCore.currentDefectDictModel
            Layout.fillWidth: true
            Layout.fillHeight:true
        }
        ShowTools{
           Layout.fillHeight:true
        }
    }
}
