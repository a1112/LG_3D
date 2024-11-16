import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
SelectRectangle{
// 区域选择的基础矩形
property real startX: 0
property real startY: 0
property real endX: 0
property real endY: 0
property real minX: Math.min(startX,endX)
property real maxX: Math.max(startX,endX)
property real minY:Math.min(startY,endY)
property real maxY: Math.max(startY,endY)
width: Math.abs( endX-startX)
x:Math.min(startX,endX)
height:Math.abs( endY-startY)
y:Math.min(startY,endY)
//property real absX: endX-startX
//property real absY: endY-startY
//function refreshX (){
//width= Math.abs( endX-startX)
//x=Math.min(startX,endX)
//}
//function refreshY (){
//    height= Math.abs( endY-startY)
//    y=Math.min(startY,endY)
//}
//onEndXChanged: refreshX()
//onEndYChanged: refreshY()
}

/*##^##
Designer {
    D{i:0;autoSize:true;height:480;width:640}
}
##^##*/
