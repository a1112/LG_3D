import QtQuick

import QtQuick3D

import QtQuick.Layouts
import QtQuick3D.Helpers

import QtQuick.Controls.Material
Item {
    function getOppositeKey(currentKey) {
        if (currentKey === "S")
            return "L"
        if (currentKey === "L")
            return "S"
        return currentKey
    }

    Layout.fillWidth:true
    Layout.fillHeight:true
    anchors.fill:parent
    Rectangle{
        anchors.fill: parent
        color: "#22000000"
        border.width: 1
        border.color:Material.color(Material.Blue)
    }
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
                z:core3D.cameraOffsetZ+450
                id: sceneCamera
                clipFar: 10000000
            }
        }

        Node {
            id:modelNode
            z: core3D.objectOffsetZ
            x: core3D.objectOffsetX
            y: core3D.objectOffsetY
            scale: core3D.objectScale

            Node3D {
                id: primaryModelNode
                meshKey: surfaceData.key
            }

            Node3D {
                id: secondaryModelNode
                visible: core3D.stitchDualMesh && getOppositeKey(surfaceData.key) !== surfaceData.key
                meshKey: getOppositeKey(surfaceData.key)
                modelOffsetX: ((primaryModelNode.modelSize.x + modelSize.x) / 2.0) + core3D.stitchGapX + core3D.secondaryOffsetX
                modelOffsetY: core3D.stitchGapY + core3D.secondaryOffsetY
                modelOffsetZ: core3D.stitchGapZ + core3D.secondaryOffsetZ
                modelRotationX: core3D.secondaryRotationX
                modelRotationY: core3D.secondaryRotationY
                modelRotationZ: core3D.secondaryRotationZ
            }
        }

    }
    OrbitCameraController {
        enabled: dataShowCore.controls3D.isRotateModel
        origin: modelNode
        camera: sceneCamera

    }
    WasdController {
        enabled: dataShowCore.controls3D.isMoveModel
        controlledObject: sceneCamera
    }
    // Control3D{}
}


