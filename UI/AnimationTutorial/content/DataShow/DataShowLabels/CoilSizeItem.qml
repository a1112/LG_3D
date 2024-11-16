import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtGraphs
Column {
    id:root
Layout.fillWidth: true
property int mm_x: + (dataShowCore.sourceWidth*surfaceData.scan3dScaleX).toFixed(1)
property int mm_y: + (dataShowCore.sourceHeight*surfaceData.scan3dScaleY).toFixed(1)

RowLayout{
    width: parent.width
    spacing: 10
    Label{
        text: "实际外径:"
    }
    Label{
        text: dataShowCore.currentCoilModel.coilDia
    }
}

RowLayout{
    width: parent.width
    spacing: 10
    Label{
        text: "外X: "+ root.mm_x
    }
    Label{
        text: (root.mm_x/dataShowCore.currentCoilModel.coilDia).toFixed(2)
    }
}
RowLayout{
    width: parent.width
        spacing: 10
    Label{
        text: "外Y: " +root.mm_y
    }
    Label{
        text: (root.mm_y/dataShowCore.currentCoilModel.coilDia).toFixed(2)
    }
}

RowLayout{
    width: parent.width
    spacing: 10
    Label{
        text: "外径 X/Y:"
    }
    Label{
        text: (root.mm_x/root.mm_y).toFixed(2)
    }
}
}
