.pragma library

function numberOr(value, fallback) {
    var number = Number(value)
    return isFinite(number) ? number : fallback
}

function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value))
}

function zoomAt(controller, flickable, eventX, eventY, wheelDelta) {
    if (!controller || !flickable || !controller.getAspectRatioByPoint
            || controller.canvasContentWidth <= 0
            || controller.canvasContentHeight <= 0) {
        return 0
    }

    var viewportX = numberOr(eventX, 0) - numberOr(flickable.contentX, 0)
    var viewportY = numberOr(eventY, 0) - numberOr(flickable.contentY, 0)
    var viewportPoint = Qt.point(viewportX, viewportY)
    var minimum = Math.max(0.0001, numberOr(controller.minScale, 1))
    var maximum = Math.max(minimum, numberOr(controller.maxScale, 1))
    var factor = wheelDelta > 0 ? 1.1 : 0.9
    var targetScale = clamp(numberOr(controller.canvasScale, minimum) * factor,
                            minimum,
                            maximum)

    controller.scaleTempPoint = controller.getAspectRatioByPoint(viewportPoint)
    controller.canvasScale = targetScale
    controller.setFlickablebyPoint(viewportPoint)

    if (targetScale >= maximum) {
        return 1
    }
    if (targetScale <= minimum) {
        return -1
    }
    return 0
}
