import QtQuick
import "../../btns"
import "../../DataShow/Foot"

RowBase {
    visible:auth.isAdmin
    spacing: adaptive.headerSpacing
    Row{
        ItemDelegateItem {
            height: adaptive.headerTabHeight
            text: "2D视图"
            onClicked: {
                coreModel.surfaceL.rootViewIndex = 0
                coreModel.surfaceS.rootViewIndex = 0
            }
        }
        ItemDelegateItem {
            height: adaptive.headerTabHeight
            text: "3D视图"
            onClicked: {
                coreModel.surfaceL.rootViewIndex = 1
                coreModel.surfaceS.rootViewIndex = 1
            }
        }
    }

    CheckRec{
        implicitWidth: adaptive.scaleMetric(35, 30, 46)
        typeIndex:1
        checkColor: "#FFCB3D"
        text: "MASK"
        checked:  coreModel.imageMaskChecked
        onCheckedChanged: coreModel.imageMaskChecked = checked
    }
    CheckRec{
        visible: !coreModel.imageMaskChecked
        implicitWidth: adaptive.scaleMetric(35, 30, 46)
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
        implicitWidth: adaptive.scaleMetric(35, 30, 46)
        text: "S端"
        checked:  coreModel.surfaceS.show_visible
        onCheckedChanged: coreModel.surfaceS.show_visible = checked
    }


    CheckRec{
        implicitWidth: adaptive.scaleMetric(35, 30, 46)
        text: "L端"
        checked:  coreModel.surfaceL.show_visible
        onCheckedChanged: coreModel.surfaceL.show_visible = checked
    }
}
