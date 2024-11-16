

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import QtQuick3D
import QtQuick3D.Effects


Item {
    property Core3D core3D: Core3D{}

    View3D {
        id: view3D
        anchors.fill: parent
        // environment: sceneEnvironment
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

            PerspectiveCamera {
                x:core3D.cameraOffsetX
                y:core3D.cameraOffsetY
                z:core3D.cameraOffsetZ
                id: sceneCamera
            }

            Loader {
                source: "Node3D.qml"
            }

            Node3D {
                id:modelNode
                eulerRotation.z: 270
                eulerRotation.y: 0
                eulerRotation.x: 0
                z: core3D.objectOffsetZ
                x: core3D.objectOffsetX
                y: core3D.objectOffsetY
            }
        }
    }
    Control3D{}

Item {
    id: __materialLibrary__
}
}


