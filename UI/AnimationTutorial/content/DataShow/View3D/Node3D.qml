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
            source: "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+surfaceData.key+"/"+surfaceData.coilId+"/meshes/defaultobject_mesh.mesh"
            materials: [
                defaultMaterial_material,
            ]
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
