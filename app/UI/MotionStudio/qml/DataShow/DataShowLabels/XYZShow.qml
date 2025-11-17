import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../btns"
import "Base"
Item{
    id: rowLayout
    Layout.fillWidth: true
    height: 60
    property var title: "标定值"
    property var x_mm: 0.0
    property var y_mm: 0.0
    property var z_mm: 0.0
    property alias text_color: lab.color
    property bool mm_label_visible: true
    property bool closeVis: false

    signal closeClicked()

    Pane{
    width:parent.width
    height: 60
    Material.elevation: 4
    }


    RowLayout{

    width: parent.width
    height: 45
    ItemDelegate {
        implicitHeight:rowLayout.height-5
        implicitWidth: 50
        Label{
        anchors.centerIn: parent
        text: rowLayout.title
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
                spacing: 5

        RowLabelShow{
            text:x_mm
        }
        RowLabelShow{
            text:y_mm
        }
        RowLabelShow{
            id:lab
            text: z_mm
            color: parseInt(z_mm)<surfaceData.tower_warning_threshold_down || parseInt(z_mm)>surfaceData.tower_warning_threshold_up?"red":"green" //三角测距
        }
    }
}

    ItemDelegate{
        visible:closeVis
        CloseBtn{
            enabled:false
            width: 20
            height: 20
        }
        width: 20
        height: 20
        onClicked:{
            rowLayout.closeClicked()
        }
    }
}
