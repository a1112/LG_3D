import QtQuick
import QtQuick.Controls

Row {

    Label{
        text: "" + parseInt(surfaceData.medianZInt)
        color: "pink"
        font.bold: true
    }
    Label{
        text: "  " + parseInt(surfaceData.medianZ)
        color: "green"
        font.bold: true
    }

}
