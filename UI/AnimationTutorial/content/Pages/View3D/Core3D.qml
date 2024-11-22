import QtQuick

Item {
    // 移动值
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

    function setMouseMoveStart(x, y) {
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

    function setMouseMoveEnd(x, y) {
        tempOfseetX = 0
        tempOfseetX = 0
    }

    property real objectRotationX: 0
    property real objectRotationY: 0
    property real objectRotationZ: 270

    function setMouseRotateStart(x, y) {
        mouseStartX = x
        mouseStartY = y
        startOffsetX = objectRotationX
        startOffsetY = objectRotationY
    }

    function setMouseRotate(x, y) {
        tempOfseetX = (x - mouseStartX)
        tempOfseetY = (y - mouseStartY)
        objectRotationX = startOffsetX - tempOfseetX
        objectRotationY = startOffsetY + tempOfseetY
    }

    function setMouseRotateMoveEnd(x, y) {
        tempOfseetX = 0
        tempOfseetX = 0
    }

}
