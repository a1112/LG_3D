import QtQuick

Row{
    height: 150
    spacing: 3
    Repeater{
        model: leftCore.preSourceModelS
        ImageItem{
            hasImage: leftCore.hovelCoilData.Status_S>=0
        }
    }
    Repeater{
        model: leftCore.preSourceModelL
        ImageItem{
            hasImage: leftCore.hovelCoilData.Status_L>=0
        }
    }
}
