import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base/IconButtons"
import "../Core"
//  缺陷显示主要界面
Item {
    id:root
    property string card_id: ""
    property DefectCoreModel defectCoreModel:defectViewCore.defectCoreModel
    ColumnLayout{
        anchors.fill: parent
        spacing: 2
        ToolBox{
            Layout.fillWidth: true
            height: 20
        }

        DefectDataView{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
        DefectDataViewMenu{
        id:defectDataViewMenu
    }
}
