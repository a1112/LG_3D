import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    width:200
    height:200
    ColumnLayout{
    anchors.fill: parent
            Item{
                Layout.fillHeight: true
                Layout.fillWidth: true
                Image{
                    anchors.centerIn: parent
                width: parent.width
                height: parent.height
                asynchronous:true
                fillMode: Image.PreserveAspectFit
                source: api.defect_url(dataShowCore.coilId,dataShowCore.key,
                                       dataShowCore.currentViewKey,
                                       defectX,defectY,defectW,defectH
                                       )
                // sourceClipRect:

                    //Qt.rect(defectX,defectY,defectW,defectH)
            }
            }

            // x: defectX*dataShowCore.canvasScale
            // y: defectY*dataShowCore.canvasScale
            // width: defectW*dataShowCore.canvasScale
            // height: defectH*dataShowCore.canvasScale
            // visible: coreModel.defectDictAll[defectName]??false

    Label{
        Layout.alignment: Qt.AlignHCenter
        text: defectName
        font.pixelSize: 18

    }

    }
    }

