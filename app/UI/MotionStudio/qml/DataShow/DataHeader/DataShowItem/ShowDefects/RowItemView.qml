import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate{
    id: root

    required property string key
    required property var value

    width: 100
    height: 25
     RowLayout{
         anchors.fill: parent
         Item{
            width: 5
            height: 1
         }
         Label{
             text: root.key + ":"
         }
         Label{
            horizontalAlignment: Text.AlignHCenter
             Layout.fillWidth: true
             text: root.value
             font.pixelSize: 18
             font.family: "Arial"
             font.bold:true

         }
         Label{
             text:"mm"
             opacity: 0.7
         }
         Item{
            width: 3
            height: 1
         }
     }
}
