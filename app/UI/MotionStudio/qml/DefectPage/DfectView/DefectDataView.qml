pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: root

    required property var defectModel
    required property var style
    required property var menuController

    clip: true

    GridView {
        id: grid
        anchors.fill: parent
        clip: true
        model: root.defectModel.defectsModel
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
            style: root.style
            menuController: root.menuController
        }
    }
}
