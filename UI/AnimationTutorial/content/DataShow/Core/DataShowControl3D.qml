import QtQuick

Item {
    property real scaleZ: 1
    readonly  property int controlCameraRotateModel: 0
    readonly property int  controlCameraMoveModel:1
    property int currentControlModel:controlCameraRotateModel
    readonly property bool isRotateModel: currentControlModel==controlCameraRotateModel
    readonly property bool isMoveModel: currentControlModel==controlCameraMoveModel

    property string control3DModelName: control3DModel.get(currentControlModel).name

    property ListModel control3DModel:ListModel{
        ListElement{
            name:"自由旋转"
            key:0
        }
        ListElement{
            name:"自由移动"
            key:1
        }
    }
}
