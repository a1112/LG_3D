import QtQuick

Rectangle{
    id:root
    property real z_value:0
    x:dataShowCore.toPx(p_x)-width/2
    y:dataShowCore.toPx(p_y)-height/2
    width: 4
    height: 4
    radius: width/2
    color:"#00000000"
    border.width: 2
    border.color: "red"

}

