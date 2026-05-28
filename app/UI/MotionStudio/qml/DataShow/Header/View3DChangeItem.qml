import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../Style"
import "../../Controls/Menu"
ItemDelegate{

    text: dataShowCore.controls3D.control3DModelName+" ▼"
    font.family: "Material Icons"
    height: 25
    implicitHeight:25
    onClicked:{
        menu_type.popup()
    }
    Rectangle{
        border.color: coreStyle.headerBorderColor
        border.width: 1
        color: hovered ? coreStyle.buttonHoverColor : coreStyle.panelElevatedColor
        anchors.fill: parent
    }
    Menu{
        id:menu_type
        Repeater{
            model: dataShowCore.controls3D.control3DModel
            SelectMenuItem{
                text:name
                selectd:dataShowCore.controls3D.currentControlModel==key
                onClicked:{
                    dataShowCore.controls3D.currentControlModel=key
                }
            }

        }

    }
}
