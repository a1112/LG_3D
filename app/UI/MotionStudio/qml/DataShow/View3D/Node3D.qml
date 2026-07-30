import QtQuick
import QtQuick3D
import QtQuick3D.AssetUtils


Node {
    id: root

    required property var surfaceData

    eulerRotation.z:-90
    property string meshKey: root.surfaceData.key
    property bool centerDepth: true
    property bool alignMinDepthToZero: false
    property real modelOffsetX: 0
    property real modelOffsetY: 0
    property real modelOffsetZ: 0
    property real modelRotationX: 0
    property real modelRotationY: 0
    property real modelRotationZ: 0
    property vector3d modelScale: Qt.vector3d(1, 1, 1)
    property vector3d autoCenterOffset: Qt.vector3d(0, 0, 0)
    readonly property vector3d modelBoundsMin: runtimeModel.bounds.minimum
    readonly property vector3d modelBoundsMax: runtimeModel.bounds.maximum
    readonly property vector3d modelSize: Qt.vector3d(
                                              Math.max(0, modelBoundsMax.x - modelBoundsMin.x),
                                              Math.max(0, modelBoundsMax.y - modelBoundsMin.y),
                                              Math.max(0, modelBoundsMax.z - modelBoundsMin.z)
                                              )
    readonly property bool modelReady: runtimeModel.status === RuntimeLoader.Success
    property int reloadAttempt: 0
    property int maxReloadAttempts: 3

    function updateModelCenter() {
        let minBounds = runtimeModel.bounds.minimum
        let maxBounds = runtimeModel.bounds.maximum
        let centerX = (minBounds.x + maxBounds.x) / 2.0
        let centerY = (minBounds.y + maxBounds.y) / 2.0
        let centerZ = (minBounds.z + maxBounds.z) / 2.0
        let offsetZ = 0
        if (centerDepth)
            offsetZ = -centerZ
        else if (alignMinDepthToZero)
            offsetZ = -minBounds.z
        autoCenterOffset = Qt.vector3d(-centerX, -centerY, offsetZ)
    }

    property string meshes_url: root.surfaceData.meshUrl
    onMeshes_urlChanged: {
        reloadAttempt = 0
        autoCenterOffset = Qt.vector3d(0, 0, 0)
        scheduleModelLoad(1)
    }

    function scheduleModelLoad(delayMs) {
        if (!meshes_url) {
            runtimeModel.source = ""
            return
        }
        modelLoadTimer.interval = Math.max(1, delayMs)
        modelLoadTimer.restart()
    }

    function loadModel() {
        let expectedUrl = meshes_url
        runtimeModel.source = ""
        Qt.callLater(function() {
            if (expectedUrl === meshes_url) {
                runtimeModel.source = expectedUrl
            }
        })
    }

    Timer {
        id: modelLoadTimer
        repeat: false
        onTriggered: root.loadModel()
    }

    Component.onCompleted: scheduleModelLoad(1)

    Node {
        id: node3D_obj
        objectName: "3D.obj"
        x: root.autoCenterOffset.x + root.modelOffsetX
        y: root.autoCenterOffset.y + root.modelOffsetY
        z: root.autoCenterOffset.z + root.modelOffsetZ
        eulerRotation.x: root.modelRotationX
        eulerRotation.y: root.modelRotationY
        eulerRotation.z: root.modelRotationZ
        scale: root.modelScale
        RuntimeLoader {
            id: runtimeModel
            objectName: "defaultobject"
            source: ""
            onStatusChanged: {
                if (status === RuntimeLoader.Success) {
                    root.reloadAttempt = 0
                    root.updateModelCenter()
                } else if (status === RuntimeLoader.Error) {
                    if (root.reloadAttempt < root.maxReloadAttempts) {
                        root.reloadAttempt += 1
                        root.scheduleModelLoad(Math.min(
                                                   3000,
                                                   500 * Math.pow(
                                                       2,
                                                       root.reloadAttempt - 1)))
                    } else {
                        console.warn("3D model load failed:", errorString)
                    }
                }


            }
            onBoundsChanged: root.updateModelCenter()
        }
    }

    Node {
        id: __materialLibrary__
        PrincipledMaterial {
            id: defaultMaterial_material
            objectName: "DefaultMaterial"
            baseColor: "#d9d9d9"
            indexOfRefraction: 1
        }
    }
}
