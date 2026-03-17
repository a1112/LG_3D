import QtQuick
import QtQuick3D


Node {
    id: node
    eulerRotation.z:-90
    property string meshKey: surfaceData.key
    property real modelOffsetX: 0
    property real modelOffsetY: 0
    property real modelOffsetZ: 0
    property real modelRotationX: 0
    property real modelRotationY: 0
    property real modelRotationZ: 0
    property vector3d autoCenterOffset: Qt.vector3d(0, 0, 0)
    readonly property vector3d modelBoundsMin: defaultobject.bounds.minimum
    readonly property vector3d modelBoundsMax: defaultobject.bounds.maximum
    readonly property vector3d modelSize: Qt.vector3d(
                                              Math.max(0, modelBoundsMax.x - modelBoundsMin.x),
                                              Math.max(0, modelBoundsMax.y - modelBoundsMin.y),
                                              Math.max(0, modelBoundsMax.z - modelBoundsMin.z)
                                              )
    readonly property bool modelReady: defaultobject.status === Model.Ready

    function updateModelCenter() {
        let minBounds = defaultobject.bounds.minimum
        let maxBounds = defaultobject.bounds.maximum
        let centerX = (minBounds.x + maxBounds.x) / 2.0
        let centerY = (minBounds.y + maxBounds.y) / 2.0
        let centerZ = (minBounds.z + maxBounds.z) / 2.0
        autoCenterOffset = Qt.vector3d(-centerX, -centerY, -centerZ)
    }

    property string meshes_url: "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+meshKey+"/"+surfaceData.coilId+"/meshes/defaultobject_mesh.mesh"
    onMeshes_urlChanged: {
        defaultobject.source = ""
        autoCenterOffset = Qt.vector3d(0, 0, 0)
        t_.start()
    }
    Timer{
        id:t_
        interval:5000
        onTriggered: {
            defaultobject.source = meshes_url
        }
    }

    Node {
        id: node3D_obj
        objectName: "3D.obj"
        x: node.autoCenterOffset.x + node.modelOffsetX
        y: node.autoCenterOffset.y + node.modelOffsetY
        z: node.autoCenterOffset.z + node.modelOffsetZ
        eulerRotation.x: node.modelRotationX
        eulerRotation.y: node.modelRotationY
        eulerRotation.z: node.modelRotationZ
        Model {
            id: defaultobject
            pickable:false
            objectName: "defaultobject"
            //source: "file:////"+surfaceData.meshUrl
            source: ""
            materials: [
                defaultMaterial_material,
            ]
            onStateChanged: {
                console.log("3D state: "+state)
                if (status === Model.Ready) {
                    node.updateModelCenter()
                    console.log("Model loaded successfully");
                } else if (status === Model.Error) {
                    console.log("Failed to load model:", errorString);
                }


            }
            onBoundsChanged: node.updateModelCenter()
        }
    }

    Node {
        id: __materialLibrary__
        PrincipledMaterial {
            id: defaultMaterial_material
            objectName: "DefaultMaterial"
            baseColor: "#ffdede"
            indexOfRefraction: 1
        }
    }
}
