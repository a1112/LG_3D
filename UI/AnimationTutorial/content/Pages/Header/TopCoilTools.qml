import QtQuick
import "../../btns"
import "../../DataShow/Foot"

RowBase {
    visible:auth.isAdmin
    spacing: 15
    Row{
        ItemDelegateItem {
            height: 35
            text: "2D视图"
            onClicked: {
                coreModel.surfaceL.rootViewIndex = 0
                coreModel.surfaceS.rootViewIndex = 0
            }
        }
        ItemDelegateItem {
            height: 35
            text: "3D视图"
            onClicked: {
                coreModel.surfaceL.rootViewIndex = 1
                coreModel.surfaceS.rootViewIndex = 1
            }
        }
    }

    CheckRec{
        implicitWidth: 35
        typeIndex:1
        checkColor: "#FFCB3D"
        text: "MASK"
        checked:  coreModel.imageMaskChecked
        onCheckedChanged: coreModel.imageMaskChecked = checked
    }
    CheckRec{
        visible: !coreModel.imageMaskChecked
        implicitWidth: 35
        typeIndex:1
        checkColor: "#CB3DFF"
        text: "QUICK"
        checked:  coreModel.quickLyImage
        onCheckedChanged: coreModel.quickLyImage = quickLyImage
    }

    SeparatorLine{
        color: "#CAF143"
    }

    CheckRec{
        implicitWidth: 35
        text: "S端"
        checked:  coreModel.surfaceS.show_visible
        onCheckedChanged: coreModel.surfaceS.show_visible = checked
    }


    CheckRec{
        implicitWidth: 35
        text: "L端"
        checked:  coreModel.surfaceL.show_visible
        onCheckedChanged: coreModel.surfaceL.show_visible = checked
    }
}
