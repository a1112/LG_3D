import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate{
    width: 150
    height: 25


     RowLayout{
         anchors.fill: parent
         Label{
             text:key+":"

         }
         Label{
            horizontalAlignment: Text.AlignHCenter
             Layout.fillWidth: true
             background: Rectangle{
                 color: "black"

                 border.width: 1

             }
             text:value
             font.pixelSize: 16
             font.family: "Arial"
             font.bold:true

         }
     }
}
