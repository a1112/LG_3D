import QtQuick

Row{
    height: 150
    spacing: 3
    ImageItem{
        hasImage: leftCore.hovelCoilData.Status_S >= 0
        image_source: coreModel.surfaceS.getSource(leftCore.hovedCoilId, "AREA", true)
        key: "AREA-S"
    }
    ImageItem{
        hasImage: leftCore.hovelCoilData.Status_L >= 0
        image_source: coreModel.surfaceL.getSource(leftCore.hovedCoilId, "AREA", true)
        key: "AREA-L"
    }
}
