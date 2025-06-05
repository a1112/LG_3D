
import QtQuick.Controls.Material
Menu {
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


    ViewChangeMenu{
    }
    DefectViewMenu{}
    AnnotationMenu{}
}
