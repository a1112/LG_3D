import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    ColumnLayout{
    height:parent.height


        Rectangle{
            width:100
            height:100
            // x: defectX*dataShowCore.canvasScale
            // y: defectY*dataShowCore.canvasScale
            // width: defectW*dataShowCore.canvasScale
            // height: defectH*dataShowCore.canvasScale
            border.color: "red"
            border.width: 1
            opacity:0.7
            color: "transparent"
            visible: coreModel.defectDictAll[defectName]??false
        Label{
            text: defectName
            font.pixelSize: 15
            anchors.centerIn:parent
        }
        }

    }
}
