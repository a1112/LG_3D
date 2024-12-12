import QtQuick
import QtQuick3D
import QtQuick3D.Effects
import QtQuick.Layouts
import QtQuick3D.Helpers
Item {
    Layout.fillWidth:true
    Layout.fillHeight:true
    anchors.fill:parent
    View3D {
        id: view3D
        anchors.fill: parent

        // environment: sceneEnvironment
        environment: SceneEnvironment {
            id: sceneEnvironment
                 backgroundMode: SceneEnvironment.SkyBox
                 lightProbe: Texture {
                     textureData: ProceduralSkyTextureData{}
                 }
                 InfiniteGrid {
                     gridInterval: 1000
                 }
             }

        Node {
            id: scene
            DirectionalLight {
                id: directionalLight
                x: -17050.938
                y: -3850.97
                eulerRotation.z: 48.83032
                eulerRotation.y: -55.19474
                eulerRotation.x: -42.53009
                brightness: 1.0
                csmBlendRatio: 100
                z: -850
                csmSplit1: 10
            }
            // Node3D {
            //     id:modelNode
            //     eulerRotation.z: sceneEnvironment.eulerRotation.z
            //     eulerRotation.y: sceneEnvironment.eulerRotation.y
            //     eulerRotation.x: sceneEnvironment.eulerRotation.x


            //     // eulerRotation.z: core3D.objectRotationZ
            //     // eulerRotation.y: core3D.objectRotationY
            //     // eulerRotation.x: core3D.objectRotationX
            //     // z: core3D.objectOffsetZ
            //     // x: core3D.objectOffsetX
            //     // y: core3D.objectOffsetY
            // }
            PerspectiveCamera {
                x:core3D.cameraOffsetX
                y:core3D.cameraOffsetY
                z:core3D.cameraOffsetZ+1000
                id: sceneCamera
                clipFar: 10000000
            }
        }

        Node3D {
            id:modelNode
            // eulerRotation.z: core3D.objectRotationZ
            // eulerRotation.y: core3D.objectRotationY
            // eulerRotation.x: core3D.objectRotationX
            z: core3D.objectOffsetZ
            x: core3D.objectOffsetX
            y: core3D.objectOffsetY
            scale: core3D.objectScale
        }

    }
    OrbitCameraController {
        enabled: dataShowCore.controls3D.isRotateModel
        origin: scene
        camera: sceneCamera

    }
    WasdController {
        enabled: dataShowCore.controls3D.isMoveModel
        controlledObject: sceneCamera
    }
    // Control3D{}
}


