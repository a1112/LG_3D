import QtQuick
import "../../Core/Surface"

Item {
    id: root

    required property SurfaceData surfaceData
    required property var settings

    property AdjustConfig adjustConfig: AdjustConfig {
        surfaceData: root.surfaceData
    }
    property TopDataManage topDataManage: TopDataManage {
        settings: root.settings
    }
    property DefectManage defectManage: DefectManage {}
}
