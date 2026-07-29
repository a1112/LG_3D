import QtQuick
import QtQuick.Controls
Row {
    Label{
        text: "No:"
        color: coreStyle.secondaryTextColor
    }
    Label{
        text: dataShowCore.currentCoilModel.coilNo
    }
    Label{
        text: "钢种:"
        color: coreStyle.secondaryTextColor
    }
    Label{
        text: dataShowCore.currentCoilModel.coilType
    }

    Label{
        text: "外径:"
        color: coreStyle.secondaryTextColor
    }
    Label{
        text: dataShowCore.currentCoilModel.coilDia
    }

    Label{
        text: "厚:"
        color: coreStyle.secondaryTextColor
    }
    Label{
        text: dataShowCore.currentCoilModel.coilThickness
    }
    Label{
        text: "宽:"
        color: coreStyle.secondaryTextColor
    }
    Label{
        text: core.currentCoilModel.coilWidth
    }
}
