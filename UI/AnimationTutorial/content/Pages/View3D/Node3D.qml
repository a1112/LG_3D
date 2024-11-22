import QtQuick
import QtQuick3D
import QtQuick 2.15


Node {
    id: node
    // Nodes:
    Node {
        id: node3D_obj
        objectName: "3D.obj"
        Model {
            id: defaultobject
            pickable:true
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

    // Animations:
}
