import QtQuick 2.15
Item{
    width: row.width
    height: row.height
    property color bgColor: "#0F0"
    property color showColor: "#9991A3"
    property string show_text: ""
    property alias textColor: lab.color
    property real recWidth:  0.18*dpi
    property bool checked: true
    property bool mouseEnabled: true
Row{
    id:row
    Rectangle {
        color: checked?bgColor:showColor
        width: recWidth
        height:width
        Rectangle{
            width: parent.width*0.7
            height: width
            anchors.centerIn: parent
            color: checked?showColor:bgColor
        }
    }
    LabelBase{
        id:lab
        text:show_text
    }
}
MouseArea{
    enabled:mouseEnabled
    cursorShape: Qt.PointingHandCursor
    anchors.fill: parent
    onClicked: {
        checked=!checked
    }
}
}
