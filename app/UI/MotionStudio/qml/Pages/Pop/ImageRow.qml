import QtQuick

Row{
    height: 150
    spacing: 3
    Repeater{
        model: leftCore.preSourceModelS
        ImageItem{
            hasImage: leftCore.hovelCoilData && leftCore.hovelCoilData.Status_S>=0
            image_source: model.image_source
            key: model.key
        }
    }
    Repeater{
        model: leftCore.preSourceModelL
        ImageItem{
            hasImage: leftCore.hovelCoilData && leftCore.hovelCoilData.Status_L>=0
            image_source: model.image_source
            key: model.key
        }
    }
}
