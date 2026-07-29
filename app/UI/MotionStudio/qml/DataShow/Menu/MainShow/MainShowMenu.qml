
import QtQuick.Controls.Material
Menu {
    id: root

    required property var controller
    required property var surfaceData
    required property var globalContext

    readonly property bool canRecacheAreaTiles:
        root.surfaceData && root.surfaceData.isAreaRootView
        && typeof root.controller.recacheAreaTiles === "function"

    title: qsTr("功能菜单")
    MenuItem{
        text: qsTr("打开 URL...")
        enabled: Boolean(root.controller.source)
        onClicked:{
            Qt.openUrlExternally(root.controller.source)
        }
    }

    MenuItem{
        text: qsTr("重置")
        onClicked:{
            root.controller.resetView()
        }
    }

    MenuItem{
        text: root.controller.recacheInProgress
              ? qsTr("重新缓存中...") : qsTr("重新缓存 2D 图像")
        visible: root.canRecacheAreaTiles
        enabled: root.canRecacheAreaTiles && !root.controller.recacheInProgress
        onClicked:{
            root.controller.recacheAreaTiles()
        }
    }

    ViewChangeMenu{
    }
    DefectViewMenu{}
    AnnotationMenu{
        controller: root.controller
        surfaceData: root.surfaceData
        defectClassController: root.globalContext.defectClassProperty
    }
}
