import QtQuick
import QtQuick.Controls

Item {
    id: root
    clip: true

    GridView {
        id: grid
        anchors.fill: parent
        clip: true
        model: defectCoreModel.defectsModel
        readonly property int columnCount: Math.max(1, Math.floor(width / 190))
        cellWidth: width / columnCount
        cellHeight: 190
        reuseItems: true
        cacheBuffer: cellHeight * 2
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        delegate: DefectItemShow {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight
        }
    }
}
