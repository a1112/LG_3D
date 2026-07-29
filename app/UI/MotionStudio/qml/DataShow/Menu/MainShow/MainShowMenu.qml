
import QtQuick.Controls.Material
Menu {
    id: mainShowMenu
    property bool canRecacheAreaTiles: surfaceData && surfaceData.isAreaRootView
                                       && dataShowCore_
                                       && typeof dataShowCore_.recacheAreaTiles === "function"
    title:"功能菜单"
    MenuItem{
        text:"打开URL..."
        onClicked:{
            Qt.openUrlExternally(dataShowCore_.source)
        }
    }

    MenuItem{
        text:"重置"
        onClicked:{
            dataShowCore_.resetView()
        }
    }

    MenuItem{
        text: dataShowCore_ && dataShowCore_.recacheInProgress ? "\u91cd\u65b0\u7f13\u5b58\u4e2d..." : "\u91cd\u65b0\u7f13\u5b582D\u56fe\u50cf"
        visible: mainShowMenu.canRecacheAreaTiles
        enabled: mainShowMenu.canRecacheAreaTiles && !dataShowCore_.recacheInProgress
        onClicked:{
            dataShowCore_.recacheAreaTiles()
        }
    }

    ViewChangeMenu{
    }
    DefectViewMenu{}
    AnnotationMenu{}
}
