import QtQuick
import "../../btns"
import "../../DataShow/Foot"

RowBase {
    id: root

    required property var adaptiveMetrics
    required property var modelStore
    required property var authManager

    visible: root.authManager.isAdmin
    spacing: root.adaptiveMetrics.headerSpacing
    Row{
        ItemDelegateItem {
            height: root.adaptiveMetrics.headerTabHeight
            text: "2D视图"
            onClicked: {
                root.modelStore.surfaceL.rootViewIndex = 0
                root.modelStore.surfaceS.rootViewIndex = 0
            }
        }
        ItemDelegateItem {
            height: root.adaptiveMetrics.headerTabHeight
            text: "3D视图"
            onClicked: {
                root.modelStore.surfaceL.rootViewIndex = 1
                root.modelStore.surfaceS.rootViewIndex = 1
            }
        }
    }

    CheckRec{
        id: maskToggle
        implicitWidth: root.adaptiveMetrics.scaleMetric(35, 30, 46)
        typeIndex:1
        checkColor: "#FFCB3D"
        text: "MASK"
        checked: root.modelStore.imageMaskChecked
        onCheckedChanged: root.modelStore.imageMaskChecked = maskToggle.checked
    }
    CheckRec{
        id: quickToggle
        visible: !root.modelStore.imageMaskChecked
        implicitWidth: root.adaptiveMetrics.scaleMetric(35, 30, 46)
        typeIndex:1
        checkColor: "#CB3DFF"
        text: "QUICK"
        checked: root.modelStore.quickLyImage
        onCheckedChanged: root.modelStore.quickLyImage = quickToggle.checked
    }

    SeparatorLine{
        color: "#CAF143"
    }

    CheckRec{
        id: surfaceSToggle
        implicitWidth: root.adaptiveMetrics.scaleMetric(35, 30, 46)
        text: "S端"
        checked: root.modelStore.surfaceS.show_visible
        onCheckedChanged: root.modelStore.surfaceS.show_visible = surfaceSToggle.checked
    }


    CheckRec{
        id: surfaceLToggle
        implicitWidth: root.adaptiveMetrics.scaleMetric(35, 30, 46)
        text: "L端"
        checked: root.modelStore.surfaceL.show_visible
        onCheckedChanged: root.modelStore.surfaceL.show_visible = surfaceLToggle.checked
    }
}
