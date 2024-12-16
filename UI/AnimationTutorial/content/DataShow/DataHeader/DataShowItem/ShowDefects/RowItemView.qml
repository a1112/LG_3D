import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate{
    width: 100
    height: 25
     RowLayout{
         anchors.fill: parent
         Item{
            width: 5
            height: 1
         }
         Label{
             text:key+":"
         }
         Label{
            horizontalAlignment: Text.AlignHCenter
             Layout.fillWidth: true
             text:value
             font.pixelSize: 16
             font.family: "Arial"
             font.bold:true

         }
         Label{
             text:key+"mm"
             opacity: 0.7
         }
         Item{
            width: 3
            height: 1
         }
     }
}
