import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base/IconButtons"
//  基础的面向3D/ 3D 图像
Item {
    id:root
    property string card_id: ""

    ColumnLayout{
        anchors.fill: parent
        spacing: 2
        ToolBox{
            Layout.fillWidth: true
            height: 20
        }
    Rectangle{
        color: "#000"
         Layout.fillWidth: true
         Layout.fillHeight: true

    }

    }
}
