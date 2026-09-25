import QtQuick

Row{
    id: root

    required property var hoverController
    required property var modelStore
    required property var style

    height: 150
    spacing: 3
    ImageItem{
        hasImage: root.hoverController.hovelCoilData
                  && root.hoverController.hovelCoilData.Status_S >= 0
        image_source: root.modelStore.surfaceS.getSource(
                          root.hoverController.hovedCoilId, "AREA", true)
        key: "AREA-S"
        style: root.style
    }
    ImageItem{
        hasImage: root.hoverController.hovelCoilData
                  && root.hoverController.hovelCoilData.Status_L >= 0
        image_source: root.modelStore.surfaceL.getSource(
                          root.hoverController.hovedCoilId, "AREA", true)
        key: "AREA-L"
        style: root.style
    }
}
