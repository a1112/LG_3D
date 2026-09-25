pragma ComponentBehavior: Bound

import QtQuick

Row {
    id: root

    required property var hoverController
    required property var style

    height: 150
    spacing: 3
    Repeater{
        model: root.hoverController.preSourceModelS
        ImageItem{
            hasImage: root.hoverController.hovelCoilData
                      && root.hoverController.hovelCoilData.Status_S >= 0
            style: root.style
        }
    }
    Repeater{
        model: root.hoverController.preSourceModelL
        ImageItem{
            hasImage: root.hoverController.hovelCoilData
                      && root.hoverController.hovelCoilData.Status_L >= 0
            style: root.style
        }
    }
}
