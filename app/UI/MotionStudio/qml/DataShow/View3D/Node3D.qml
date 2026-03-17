import QtQuick
import QtQuick3D


Node {
    id: node
    eulerRotation.z:-90
    property vector3d autoCenterOffset: Qt.vector3d(0, 0, 0)

    function updateModelCenter() {
        let minBounds = defaultobject.bounds.minimum
        let maxBounds = defaultobject.bounds.maximum
        let centerX = (minBounds.x + maxBounds.x) / 2.0
        let centerY = (minBounds.y + maxBounds.y) / 2.0
        let centerZ = (minBounds.z + maxBounds.z) / 2.0
        autoCenterOffset = Qt.vector3d(-centerX, -centerY, -centerZ)
    }

    property string meshes_url: "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+surfaceData.key+"/"+surfaceData.coilId+"/meshes/defaultobject_mesh.mesh"
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
        x: node.autoCenterOffset.x
        y: node.autoCenterOffset.y
        z: node.autoCenterOffset.z
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
