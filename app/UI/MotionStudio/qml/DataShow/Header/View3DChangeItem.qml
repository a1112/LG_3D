pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../Style"
import "../../Controls/Menu"
ItemDelegate{
    id: root
    required property var controller
    required property var style

    text: root.controller.controls3D.control3DModelName + " ▼"
    font.family: "Material Icons"
    height: 25
    implicitHeight:25
    onClicked:{
        menu_type.popup()
    }
    Rectangle{
        border.color: root.style.headerBorderColor
        border.width: 1
        color: root.hovered ? root.style.buttonHoverColor : root.style.panelElevatedColor
        anchors.fill: parent
    }
    Menu{
        id:menu_type
        Repeater{
            model: root.controller.controls3D.control3DModel
            SelectMenuItem {
                required property var model
                style: root.style
                text: model.name || ""
                selectd: root.controller.controls3D.currentControlModel == model.key
                onClicked:{
                    root.controller.controls3D.currentControlModel = model.key
                }
            }

        }

    }
}
