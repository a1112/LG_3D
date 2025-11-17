import QtQuick
import QtQuick.Controls
Rectangle{
    clip: true
    color: "#00000000"
    height: parent.height
    property alias textColor: lab.color
    property alias text: lab.text
               Label
                {
                    id:lab
                   anchors.centerIn: parent
                    color:"#fff"
                    text: qsTr("钢板号")
                    font.pixelSize: 18
                }
}
