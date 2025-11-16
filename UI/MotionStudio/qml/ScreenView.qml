import QtQuick 2.15
import QtQuick.Controls 2.15
import LG3D

Item {
    Image {
        id: background1
        anchors.fill: parent
        source: Constants.backgroundImage
    }
    property var ball: ContCore.modelViewIndex ? mainScreen.ball:mainScreen.ball2
    Screen01 {
        anchors.fill: parent
        id: mainScreen
        ball.eulerRotation.y:ContCore.rotatePoint.x
        ball.eulerRotation.x:ContCore.rotatePoint.y
        ball2.eulerRotation.y:ContCore.rotatePoint.x
        ball2.eulerRotation.x:ContCore.rotatePoint.y
        camera.x:-ContCore.movePoint.x
        camera.y:ContCore.movePoint.y
        MouseArea {
            id:mouse
               anchors.fill: parent

                onPressed: {
                    ContCore.startPoint=Qt.point(mouse.x,mouse.y)
                }

                onReleased: {
                    ContCore.endPoint=Qt.point(mainScreen.ball.eulerRotation.y,mainScreen.ball.eulerRotation.x)
                }
                onPositionChanged: {
                    ContCore.currentPoint=Qt.point(mouse.x,mouse.y)
                }

                onWheel: {
                    if (wheel.angleDelta.y>0){
                        mainScreen.camera.z *=0.95
                    }
                    else{
                         mainScreen.camera.z*=1.05
                    }

                }

               // onClicked: {
               //     mainScreen.ball.eulerRotation.y+=10
               //     var mouse = Qt.point(mouse.x, mouse.y);
               //     var ray = mainScreen.camera.unproject(mouse);
               //     var intersection = mainScreen.view.rayTest(ray.from, ray.to);
               //     if (intersection.hasHit) {
               //         var selectedEntity = intersection.entity;
               //         // 处理选中的对象，可以改变外观或执行其他操作
               //         console.log("Selected Entity: " + selectedEntity.name);
               //          selectedEntity.x+=100
               //     }
               // }
           }


    }
}
