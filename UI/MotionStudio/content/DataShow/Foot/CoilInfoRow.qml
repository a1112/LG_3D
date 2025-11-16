import QtQuick
import QtQuick.Controls
Row {
    Label{
        text: "No:"
        color: "#747474"
    }
    Label{
        text: dataShowCore.currentCoilModel.coilNo
    }
    Label{
        text: "钢种:"
        color: "#747474"
    }
    Label{
        text: dataShowCore.currentCoilModel.coilType
    }

    Label{
        text: "外径:"
        color: "#747474"
    }
    Label{
        text: dataShowCore.currentCoilModel.coilDia
    }

    Label{
        text: "厚:"
        color: "#747474"
    }
    Label{
        text: dataShowCore.currentCoilModel.coilThickness
    }
    Label{
        text: "宽:"
        color: "#747474"
    }
    Label{
        text: core.currentCoilModel.coilWidth
    }
}
