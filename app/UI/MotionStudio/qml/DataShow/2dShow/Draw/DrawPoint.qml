import QtQuick
import QtQuick.Controls
import "PointShow"
Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var style
    required property var apiClient
    required property var innerEllipse

    anchors.fill:parent

    DbPointShow{
        dataShowCore: root.dataShowCore
        innerEllipse: root.innerEllipse
    }
    UserPointShow{
        dataShowCore: root.dataShowCore
        surfaceData: root.surfaceData
        style: root.style
        apiClient: root.apiClient
    }
}
