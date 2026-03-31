import QtQuick

import QtQuick3D

import QtQuick.Layouts
import QtQuick3D.Helpers

import QtQuick.Controls.Material
Item {
    id: root
    function getCoilDataValue(keys, defaultValue) {
        let info = surfaceData.coilInfo || {}
        let coilData = info.coilData || info
        for (let i = 0; i < keys.length; i++) {
            let key = keys[i]
            if (coilData[key] !== undefined && coilData[key] !== null && coilData[key] !== "") {
                let value = Number(coilData[key])
                if (isFinite(value) && value > 0)
                    return value
            }
            if (info[key] !== undefined && info[key] !== null && info[key] !== "") {
                let infoValue = Number(info[key])
                if (isFinite(infoValue) && infoValue > 0)
                    return infoValue
            }
        }
        return defaultValue
    }

    function getPixelOuterDiameter(defaultValue) {
        let info = surfaceData.coilInfo || {}
        let cropBox = info.crop_box
        if (cropBox && cropBox.length >= 4) {
            let cropW = Number(cropBox[2])
            let cropH = Number(cropBox[3])
            if (isFinite(cropW) && isFinite(cropH))
                return Math.max(cropW, cropH)
            if (isFinite(cropW) && cropW > 0)
                return cropW
        }
        return getCoilDataValue(["outerDiameterPx", "outer_diameter_px", "outerDiameterPixel", "width", "Width"],
                                defaultValue)
    }

    readonly property real coilWidthMm: getCoilDataValue(["ActWidth", "Width", "act_w", "width"], 0)
    readonly property real modelDisplayWidth: Math.max(singleSurfaceFrontNode.modelSize.x, 1)
    readonly property real modelDisplayDiameter: Math.max(singleSurfaceFrontNode.modelSize.x,
                                                          singleSurfaceFrontNode.modelSize.y,
                                                          modelDisplayWidth)
    readonly property real pixelOuterDiameter: getPixelOuterDiameter(0)
    readonly property real surfaceGapMm: coilWidthMm > 0 && pixelOuterDiameter > 0
                                         ? modelDisplayDiameter * coilWidthMm / pixelOuterDiameter
                                         : Math.max(modelDisplayDiameter * 0.35, 120)
    readonly property real surfaceSpacingMm: modelDisplayWidth + surfaceGapMm

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
                id: singleSurfaceFrontNode
                meshKey: surfaceData.key
                centerDepth: false
                alignMinDepthToZero: true
                modelOffsetX: -(root.surfaceSpacingMm / 2.0)
            }

            Node3D {
                id: singleSurfaceBackNode
                meshKey: surfaceData.key
                centerDepth: false
                alignMinDepthToZero: true
                modelOffsetX: root.surfaceSpacingMm / 2.0
                modelRotationY: 180
            }
        }

    }
    Rectangle {
        width: 112
        height: 32
        radius: 4
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.top: parent.top
        anchors.topMargin: 16
        color: "#66000000"
        border.width: 1
        border.color: "#66ffffff"

        Text {
            anchors.centerIn: parent
            color: "#f2f2f2"
            text: "Front"
        }
    }
    Rectangle {
        width: 112
        height: 32
        radius: 4
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.top: parent.top
        anchors.topMargin: 16
        color: "#66000000"
        border.width: 1
        border.color: "#66ffffff"

        Text {
            anchors.centerIn: parent
            color: "#f2f2f2"
            text: "Back"
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


