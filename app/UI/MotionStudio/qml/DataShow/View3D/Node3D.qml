import QtQuick
import QtQuick3D


Node {
    id: node
    eulerRotation.z:-90

    property string meshes_url: "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+surfaceData.key+"/"+surfaceData.coilId+"/meshes/defaultobject_mesh.mesh"
    onMeshes_urlChanged: {
        defaultobject.source = ""
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
