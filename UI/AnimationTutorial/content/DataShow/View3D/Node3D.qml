import QtQuick3D


Node {
    id: node
    eulerRotation.z:-90

    Node {
        id: node3D_obj
        objectName: "3D.obj"
        Model {
            id: defaultobject
            pickable:false
            objectName: "defaultobject"
            source: "file:////"+surfaceData.meshUrl
            // source: "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+surfaceData.key+"/"+surfaceData.coilId+"/meshes/defaultobject_mesh.mesh"
            materials: [
                defaultMaterial_material,
            ]
            onStateChanged: {
                console.log("3D state: "+state)
                if (status === Model.Ready) {
                    console.log("Model loaded successfully");
                } else if (status === Model.Error) {
                    console.log("Failed to load model:", errorString);
                }


            }
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
