import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    height: 50
    Pane{
        Material.elevation: 6
        anchors.fill: parent
    }

    RowLayout{
        anchors.verticalCenter: parent.verticalCenter
        ComboBox{
            model: ["3D平均深度"]
            implicitHeight: 40
            implicitWidth: 200
        }
        CoilTextInput{
            title:qsTr("起始")
            value:graphsCore.stratCoilId

        }
        CoilTextInput{
            title:qsTr("结束")
            value:graphsCore.endCoilId
        }
    }
}
