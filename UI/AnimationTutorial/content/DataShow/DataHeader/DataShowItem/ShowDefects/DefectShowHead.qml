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
            implicitHeight:root.height
            Layout.fillWidth: true
        }
        ShowTools{
            implicitHeight:root.height

        }
    }
}
