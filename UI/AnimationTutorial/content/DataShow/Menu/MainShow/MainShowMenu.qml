
import QtQuick.Controls.Material
Menu {
    title:"功能菜单"
    MenuItem{
        text:"打开URL..."
        onClicked:{
            console.log(dataShowCore.source)
            Qt.openUrlExternally(dataShowCore.source)
        }
    }

    MenuItem{
        text:"重置"
        onClicked:{
            dataShowCore.resetView()
        }
    }


    ViewChangeMenu{
    }
    DefectViewMenu{}
    AnnotationMenu{}
}
