import QtQuick

QtObject {
    id: root

    property var data: null
    property int grad: 0
    property int defectGrad: 0
    property int taperShapeGrad: 0
    property int looseCoilGrad: 0
    property int flatRollGrad: 0
    property string defectMsg: ""
    property string taperShapeMsg: ""
    property string looseCoilMsg: ""
    property string flatRollMsg: ""

    function numberOr(value, fallback) {
        var number = Number(value)
        return isFinite(number) ? number : fallback
    }

    function applyData(value) {
        var source = value || {}
        grad = numberOr(source.grad, 0)
        defectGrad = numberOr(source.defectGrad, 0)
        taperShapeGrad = numberOr(source.taperShapeGrad, 0)
        looseCoilGrad = numberOr(source.looseCoilGrad, 0)
        flatRollGrad = numberOr(source.flatRollGrad, 0)
        defectMsg = source.defectMsg || ""
        taperShapeMsg = source.taperShapeMsg || ""
        looseCoilMsg = source.looseCoilMsg || ""
        flatRollMsg = source.flatRollMsg || ""
    }

    onDataChanged: applyData(data)
    Component.onCompleted: applyData(data)
}
