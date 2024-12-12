import QtQuick
import QtQuick.Controls
Item {
    id:root
    anchors.fill: parent
    property var defects : []
    property var t:{
       "secondaryCoilId": 2191,
       "defectClass": 3,
       "defectStatus": 0,
       "defectX": 3436,
       "defectW": 685,
       "defectData": "",
       "surface": "L",
       "Id": 13,
       "defectName": "粘连",
       "defectTime": {
         "year": 2024,
         "month": 8,
         "weekday": 6,
         "day": 25,
         "hour": 18,
         "minute": 28,
         "second": 34
       },
       "defectY": 4367,
       "defectH": 385
     }
    Repeater{
        model: dataShowCore.defectModel
        Rectangle{
            x: defectX*dataShowCore.canvasScale
            y: defectY*dataShowCore.canvasScale
            width: defectW*dataShowCore.canvasScale
            height: defectH*dataShowCore.canvasScale
            border.color: "red"
            border.width: 1
            opacity:0.7
            color: "transparent"
            visible: coreModel.defectDictAll[defectName]??false
        Label{
            text: defectName
            font.pixelSize: 15
            anchors.left: parent.right
        }
        }
    }

}
