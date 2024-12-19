import QtQuick

Item {

property var data
onDataChanged:{
    grad = data.grad
    defectGrad = data.defectGrad
    taperShapeGrad=data.taperShapeGrad
    looseCoilGrad = data.looseCoilGrad
    flatRollGrad = data.flatRollGrad
    defectMsg = data.defectMsg
    taperShapeMsg = data.taperShapeMsg
    looseCoilMsg = data.looseCoilMsg
    flatRollMsg = data.flatRollMsg
}


property int grad:0
property int defectGrad:1

property int taperShapeGrad:1
property int looseCoilGrad:1
property int flatRollGrad:1

property string defectMsg:""
property string taperShapeMsg:""
property string looseCoilMsg:""
property string flatRollMsg:""
}
