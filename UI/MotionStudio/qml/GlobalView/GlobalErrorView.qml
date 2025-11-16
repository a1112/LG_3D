import QtQuick

import QtQuick.Controls.Material

import "../animation"
Row {
    height:30
    spacing:10
    visible:coreModel.coreGlobalError.hasError
    Item{
        height:parent.height
        width:height
        AnimErrorImage{
                fillMode:Image.PreserveAspectFit
            anchors.fill:parent
            source:"../icons/warning_1.png"
        }
        anchors.verticalCenter:parent.verticalCenter
    }
    AnimLabel{
         anchors.verticalCenter:parent.verticalCenter
        font.family: "Microsoft YaHei"
        font.pixelSize: 18
        font.bold: true
        color: Material.color(Material.Yellow)
        text: coreModel.coreGlobalError.errorCode
    }
    AnimLabel{
         anchors.verticalCenter:parent.verticalCenter
        font.family: "Microsoft YaHei"
        font.pixelSize: 18
        font.bold: true
        color: Material.color(Material.Red)
        text: coreModel.coreGlobalError.errorStr
    }



}
