import QtQuick 2.15
import QtQuick.Controls
import "../../../animation"
ItemDelegate {
width: parent.width
height:30
property alias text_: lab.text
Row{
        anchors.centerIn:parent
        spacing:10
        Image{
            source:"../../../icons/alarmLight.png"
            width:height
            height:lab.height
            fillMode:Image.PreserveAspectFit
        }

AnimLabel{
    id:lab
    color:"red"
    font.bold:true
    font.pointSize: 16
    font.family: "Microsoft YaHei"
}

}

}
