import QtQuick

import QtQuick3D

import QtQuick.Layouts
import QtQuick3D.Helpers

import QtQuick.Controls.Material
Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var view3DController
    required property var style

    function getCoilDataValue(keys, defaultValue) {
        let info = root.surfaceData.coilInfo || {}
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
        let info = root.surfaceData.coilInfo || {}
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
    // Node3D applies a -90 degree Z rotation. Use the larger measured
    // horizontal bound so spacing remains correct for either source axis.
    readonly property real modelDisplayWidth: Math.max(singleSurfaceFrontNode.modelSize.x,
                                                       singleSurfaceFrontNode.modelSize.y,
                                                       1)
    readonly property real modelDisplayDiameter: Math.max(singleSurfaceFrontNode.modelSize.x,
                                                          singleSurfaceFrontNode.modelSize.y,
                                                          modelDisplayWidth)
    // Keep the two views separated in scene coordinates. Business coil
    // metadata is not a reliable scene scale, so spacing follows the loaded
    // model bounds only.
    readonly property real surfaceGapMm: Math.max(modelDisplayDiameter * 0.35, 120)
    readonly property real surfaceSpacingMm: modelDisplayWidth + surfaceGapMm
    readonly property bool frontModelReady: singleSurfaceFrontNode.modelReady
    readonly property vector3d frontModelSize: singleSurfaceFrontNode.modelSize
    readonly property real frontModelWidth: singleSurfaceFrontNode.modelSize.x
    readonly property real frontModelHeight: singleSurfaceFrontNode.modelSize.y
    readonly property string frontLoadError: singleSurfaceFrontNode.loadError
    property real initialCameraDistance: 450
    property bool initialCameraFitApplied: false

    function resetInitialCameraFit() {
        initialCameraFitApplied = false
        updateInitialCameraFit()
    }

    function updateInitialCameraFit() {
        if (initialCameraFitApplied || width <= 0 || height <= 0
                || !singleSurfaceFrontNode.modelReady
                || !singleSurfaceBackNode.modelReady
                || singleSurfaceFrontNode.modelSize.x <= 0
                || singleSurfaceFrontNode.modelSize.y <= 0
                || singleSurfaceBackNode.modelSize.x <= 0
                || singleSurfaceBackNode.modelSize.y <= 0)
            return
        let widthMm = surfaceSpacingMm + modelDisplayWidth
        let heightMm = modelDisplayDiameter
        let objectScale = root.view3DController.objectScale || Qt.vector3d(1, 1, 1)
        let sceneScale = Math.max(Math.abs(objectScale.x), Math.abs(objectScale.y),
                                  Math.abs(objectScale.z), 0.001)
        widthMm *= sceneScale
        heightMm *= sceneScale
        let verticalFov = sceneCamera.fieldOfView * Math.PI / 180.0
        let horizontalFov = 2.0 * Math.atan(
                    Math.tan(verticalFov / 2.0) * width / height)
        let verticalDistance = heightMm / (2.0 * Math.tan(verticalFov / 2.0))
        let horizontalDistance = widthMm / (2.0 * Math.tan(horizontalFov / 2.0))
        initialCameraDistance = Math.max(450, verticalDistance, horizontalDistance) * 1.18
        initialCameraFitApplied = true
    }

    Layout.fillWidth:true
    Layout.fillHeight:true
    anchors.fill:parent
    Rectangle{
        anchors.fill: parent
        color: root.style.viewportBackgroundColor
        border.width: 1
        border.color: root.style.headerBorderColor
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
                x: root.view3DController.cameraOffsetX
                y: root.view3DController.cameraOffsetY
                z: root.view3DController.cameraOffsetZ + root.initialCameraDistance
                id: sceneCamera
                clipFar: 10000000
            }
        }

        Node {
            id:modelNode
            z: root.view3DController.objectOffsetZ
            x: root.view3DController.objectOffsetX
            y: root.view3DController.objectOffsetY
            scale: root.view3DController.objectScale

            Node {
                id: frontPlacement
                x: -(root.surfaceSpacingMm / 2.0)

                Node3D {
                id: singleSurfaceFrontNode
                surfaceData: root.surfaceData
                meshKey: root.surfaceData.key
                centerDepth: false
                alignMinDepthToZero: true
                onModelReadyChanged: root.updateInitialCameraFit()
                onModelSizeChanged: root.resetInitialCameraFit()
                }
            }

            Node {
                id: backPlacement
                x: root.surfaceSpacingMm / 2.0

                Node3D {
                id: singleSurfaceBackNode
                surfaceData: root.surfaceData
                meshKey: root.surfaceData.key
                centerDepth: false
                alignMinDepthToZero: true
                modelRotationY: 180
                onModelReadyChanged: root.updateInitialCameraFit()
                onModelSizeChanged: root.resetInitialCameraFit()
                }
            }
        }

    }
    Connections {
        target: root.surfaceData
        ignoreUnknownSignals: true
        function onMeshReloadRequested() { root.resetInitialCameraFit() }
        function onMeshUrlChanged() { root.resetInitialCameraFit() }
    }

    Timer {
        interval: 100
        repeat: true
        running: !root.initialCameraFitApplied
        onTriggered: root.updateInitialCameraFit()
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
            text: "当前端面正面"
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
            text: "当前端面背面"
        }
    }
    OrbitCameraController {
        enabled: root.dataShowCore.controls3D.isRotateModel
        origin: modelNode
        camera: sceneCamera

    }
    WasdController {
        enabled: root.dataShowCore.controls3D.isMoveModel
        controlledObject: sceneCamera
    }
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 12
        width: meshStatusLabel.implicitWidth + 24
        height: meshStatusLabel.implicitHeight + 16
        radius: 4
        color: "#bb202020"
        visible: root.surfaceData.meshBuildState === "processing"
                 || root.surfaceData.meshBuildState === "error"
                 || singleSurfaceFrontNode.loadError !== ""
        Text {
            id: meshStatusLabel
            anchors.centerIn: parent
            color: "#f2f2f2"
            text: root.surfaceData.meshBuildState === "processing" ? "正在重建 3D 模型…"
                  : root.surfaceData.meshBuildState === "error"
                    ? (root.surfaceData.meshExits ? "重建失败，显示上次模型" : "3D 模型重建失败")
                    : "3D 模型加载失败"
        }
    }

    onWidthChanged: updateInitialCameraFit()
    onHeightChanged: updateInitialCameraFit()
}


