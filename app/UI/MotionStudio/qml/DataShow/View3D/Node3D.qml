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
    readonly property vector3d autoCenterOffset: modelCenterOffset()
    readonly property bool nativeMeshSource: /\.mesh(?:[?#].*)?$/i.test(meshes_url)
    readonly property vector3d modelBoundsMin: nativeMeshSource ? nativeModel.bounds.minimum : runtimeModel.bounds.minimum
    readonly property vector3d modelBoundsMax: nativeMeshSource ? nativeModel.bounds.maximum : runtimeModel.bounds.maximum
    readonly property vector3d modelSize: Qt.vector3d(
                                              Math.max(0, modelBoundsMax.x - modelBoundsMin.x),
                                              Math.max(0, modelBoundsMax.y - modelBoundsMin.y),
                                              Math.max(0, modelBoundsMax.z - modelBoundsMin.z)
                                              )
    readonly property bool modelReady: nativeMeshSource
                                       ? nativeModel.source.toString() !== "" && modelSize.x > 0 && modelSize.y > 0
                                       : runtimeModel.status === RuntimeLoader.Success
    property int reloadAttempt: 0
    property int maxReloadAttempts: 3
    readonly property string loadError: !nativeMeshSource && runtimeModel.status === RuntimeLoader.Error
                                       ? runtimeModel.errorString : ""

    function showBothSides(object) {
        if (!object)
            return
        // Imported materials are Object3D children in Qt 6.8. Keep their
        // colors/textures and change only culling for the measured surface.
        if (object instanceof Material)
            object.cullMode = Material.NoCulling
        if (object.children) {
            for (let index = 0; index < object.children.length; ++index)
                showBothSides(object.children[index])
        }
    }

    function modelCenterOffset() {
        let minBounds = modelBoundsMin
        let maxBounds = modelBoundsMax
        let centerX = (minBounds.x + maxBounds.x) / 2.0
        let centerY = (minBounds.y + maxBounds.y) / 2.0
        let centerZ = (minBounds.z + maxBounds.z) / 2.0
        let offsetZ = 0
        if (centerDepth)
            offsetZ = -centerZ
        else if (alignMinDepthToZero)
            offsetZ = -minBounds.z
        return Qt.vector3d(-centerX, -centerY, offsetZ)
    }

    property string meshes_url: root.surfaceData.meshUrl
    onMeshes_urlChanged: {
        reloadAttempt = 0
        scheduleModelLoad(1)
    }

    function scheduleModelLoad(delayMs) {
        if (!meshes_url) {
            runtimeModel.source = ""
            nativeModel.source = ""
            return
        }
        modelLoadTimer.interval = Math.max(1, delayMs)
        modelLoadTimer.restart()
    }

    function loadModel() {
        let expectedUrl = meshes_url
        runtimeModel.source = ""
        nativeModel.source = ""
        Qt.callLater(function() {
            if (expectedUrl === meshes_url) {
                if (root.nativeMeshSource)
                    nativeModel.source = expectedUrl
                else
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

    Connections {
        target: root.surfaceData
        ignoreUnknownSignals: true
        function onMeshReloadRequested() {
            root.reloadAttempt = 0
            root.scheduleModelLoad(1)
        }
    }

    Node {
        id: node3D_obj
        objectName: "3D.obj"
        x: root.modelOffsetX
        y: root.modelOffsetY
        z: root.modelOffsetZ
        // Center before rotation and scaling so viewing a surface from the
        // back does not move its center or invert its placement offset.
        pivot: Qt.vector3d(-root.autoCenterOffset.x,
                          -root.autoCenterOffset.y,
                          -root.autoCenterOffset.z)
        eulerRotation.x: root.modelRotationX
        eulerRotation.y: root.modelRotationY
        eulerRotation.z: root.modelRotationZ
        scale: root.modelScale
        Model {
            id: nativeModel
            objectName: "optimizedCoilMesh"
            source: ""
            visible: root.nativeMeshSource
            materials: [defaultMaterial_material]
        }
        RuntimeLoader {
            id: runtimeModel
            objectName: "defaultobject"
            source: ""
            visible: !root.nativeMeshSource
            onStatusChanged: {
                if (status === RuntimeLoader.Success) {
                    root.showBothSides(runtimeModel)
                    root.reloadAttempt = 0
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
        }
    }

    Node {
        id: __materialLibrary__
        PrincipledMaterial {
            id: defaultMaterial_material
            objectName: "DefaultMaterial"
            baseColor: "#d9d9d9"
            cullMode: Material.NoCulling
            indexOfRefraction: 1
        }
    }
}
