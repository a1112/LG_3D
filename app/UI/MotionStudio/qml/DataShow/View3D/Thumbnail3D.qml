import QtQuick
import QtQuick3D
import QtQuick.Layouts
import QtQuick3D.Helpers
Item {
    id: root

    required property var surfaceData
    required property var view3DController

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
                z: 660
                id: sceneCamera

            }
        }

        Node3D {
            id:modelNode
            surfaceData: root.surfaceData
            z: root.view3DController.objectOffsetZ
            x: root.view3DController.objectOffsetX
            y: root.view3DController.objectOffsetY
            scale: root.view3DController.objectScale
            eulerRotation.y:-75
        }

    }
    OrbitCameraController {
        origin: modelNode
        camera: sceneCamera
    }
}


