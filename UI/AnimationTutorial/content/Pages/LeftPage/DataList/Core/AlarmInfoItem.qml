import QtQuick

Item {

property var data

property int grad:data.grad
property int defectGrad: data.defectGrad??1

property int taperShapeGrad:data.taperShapeGrad
property int looseCoilGrad:data.looseCoilGrad
property int flatRollGrad:data.flatRollGrad

property string defectMsg:data.defectMsg
property string taperShapeMsg:data.taperShapeMsg
property string looseCoilMsg:data.looseCoilMsg
property string flatRollMsg:data.flatRollMsg




}
