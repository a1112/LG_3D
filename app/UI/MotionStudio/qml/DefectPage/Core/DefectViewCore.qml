import QtQuick
// 主要的 缺陷 Core
import "../../Model/server"
Item {
    id: root

    required property var appController
    required property var apiClient
    required property var modelStore
    required property var globalContext
    required property var toolService

    property DefectClassItemModel globalDefectClassItemModel: DefectClassItemModel {}

    property DefectCoreModel defectCoreModel: DefectCoreModel {
        modelStore: root.modelStore
        globalContext: root.globalContext
        toolService: root.toolService
        classItemConverter: root.globalDefectClassItemModel
        filterController: root.filterCore
    }

    property FilterCore filterCore: FilterCore {
        defectModel: root.defectCoreModel
        globalContext: root.globalContext
        toolService: root.toolService
    }

    property ControlCore controlCore: ControlCore {
        appController: root.appController
        apiClient: root.apiClient
        defectModel: root.defectCoreModel
    }
}
