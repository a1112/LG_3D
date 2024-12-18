import QtQuick
import QtQuick.Controls
Label{
    id:root
    property real z_value:0
    x:dataShowCore.toPx(label_point.x)-width/2
    y:dataShowCore.toPx(label_point.y)-height/2
    text:z_mm.toFixed(0)
    color:z_mm>50?"red":"yellow"
}
