import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    Pane{
        Material.elevation: 6
        anchors.fill: parent
    }
    RowLayout{
        ComboBox{
            model: ["3D平均深度"]
        }
        CoilTextInput{}

        CoilTextInput{}

    }
}
