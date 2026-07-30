import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../Core"
//  缺陷显示主要界面
Item {
    id:root

    required property var defectController
    required property var style
    required property var modelStore
    required property var settings
    required property var appController
    required property var apiClient
    required property var coreController
    required property var globalContext

    property string card_id: ""
    readonly property DefectCoreModel defectCoreModel: root.defectController.defectCoreModel

    ColumnLayout{
        anchors.fill: parent
        spacing: 2
        ToolBox{
            Layout.fillWidth: true
            height: 20
            defectModel: root.defectCoreModel
        }
        DefectDataView{
            Layout.fillWidth: true
            Layout.fillHeight: true
            defectModel: root.defectCoreModel
            style: root.style
            menuController: defectDataViewMenu
            globalContext: root.globalContext
            apiClient: root.apiClient
        }
    }
    DefectDataViewMenu{
        id:defectDataViewMenu
        modelStore: root.modelStore
        settings: root.settings
        appController: root.appController
        apiClient: root.apiClient
        coreController: root.coreController
    }
}
