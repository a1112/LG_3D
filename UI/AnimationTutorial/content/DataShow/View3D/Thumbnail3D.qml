import QtQuick
import QtQuick3D
import QtQuick.Layouts
import QtQuick3D.Helpers
Item {
    View3D {
        id: view3D
        anchors.fill: parent
        environment: SceneEnvironment {
            id: sceneEnvironment
             }

        Node {
            id: scene
            DirectionalLight {
                id: directionalLight
                x: -17050.938
                y: -3850.97
                z: 48.83032
                eulerRotation.y: -55.19474
                eulerRotation.x: -42.53009
                brightness: 1.0
                csmBlendRatio: 100
                csmSplit1: 10
            }
            PerspectiveCamera {
                z: 650
                id: sceneCamera

            }
        }

        Node3D {
            id:modelNode
            z: core3D.objectOffsetZ
            x: core3D.objectOffsetX
            y: core3D.objectOffsetY
            scale: core3D.objectScale
            eulerRotation.y:-65
        }

    }
    OrbitCameraController {
        origin: scene
        camera: sceneCamera
    }
}


