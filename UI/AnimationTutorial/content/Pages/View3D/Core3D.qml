import QtQuick

Item {

    property real objectOffsetY: 0
    property real objectOffsetX: 0
    property real objectOffsetZ: 0

    property real startOffsetX: 0
    property real startOffsetY: 0
    property real startOffsetZ: 0

    property real cameraOffsetY: 0
    property real cameraOffsetX: 0
    property real cameraOffsetZ: 450

    property real mouseStartX: 0
    property real mouseStartY: 0

    property real tempOfseetX: 0
    property real tempOfseetY: 0
    property real tempOfseetZ: 0

    function setMouseStart(x, y) {
        mouseStartX = x
        mouseStartY = y
        startOffsetX = cameraOffsetX
        startOffsetY = cameraOffsetY

    }

    function setMouseMove(x, y) {
        tempOfseetX = (x - mouseStartX)
        tempOfseetY = (y - mouseStartY)
        cameraOffsetX = startOffsetX - tempOfseetX
        cameraOffsetY = startOffsetY + tempOfseetY

    }

    function setMouseEnd(x, y) {
        tempOfseetX = 0
        tempOfseetX = 0
    }

}
