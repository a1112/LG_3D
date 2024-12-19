/*
塔形显示的单独形式
外圈  、 内圈显示
*/
import QtQuick

Item {
    anchors.fill: parent
    property real centreX
    property real centreY


        Repeater{
            model: dataShowCore.pointDbData
            delegate:PointItemPointShow{

            }
        }
}
