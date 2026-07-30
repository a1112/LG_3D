pragma ComponentBehavior: Bound
import QtQuick 2.15
Item {
    id: watermarkContainer
    required property var style
    width: parent.width
    height: parent.height
    readonly property real watermarkWidth: 320
    readonly property real watermarkHeight: 240
    readonly property int columnCount: Math.max(1, Math.ceil(width / watermarkWidth))
    readonly property int rowCount: Math.max(1, Math.ceil(height / watermarkHeight))

    Repeater {
        model: watermarkContainer.columnCount * watermarkContainer.rowCount
        Image {
            required property int index
            width: watermarkContainer.watermarkWidth
            height: watermarkContainer.watermarkHeight
            source: watermarkContainer.style.isDark
                    ? watermarkContainer.style.getIcon("USTB_Dark")
                    : watermarkContainer.style.getIcon("USTB_Light")
            fillMode: Image.PreserveAspectFit
            opacity: 0.14
            rotation: -35
            x: (index % watermarkContainer.columnCount) * watermarkContainer.watermarkWidth
            y: Math.floor(index / watermarkContainer.columnCount) * watermarkContainer.watermarkHeight
        }
    }
}
