import QtQuick
import "ViewChang"
import "2dShow"
import "Menu/MainShow"
Item {
    id:root
    required property var controller
    required property var style
    required property var surfaceData
    required property var globalContext
    required property var adaptiveMetrics
    required property var modelStore
    required property var view3DController
    width:parent.width
    height:parent.height

    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
            mainShowMenu.popup()
        }
    }


    ShowInfos{
        controller: root.controller
        style: root.style
        width: root.width
        height: root.height
    }

    ViewChangView{  // 右侧的数据切换
        adaptiveMetrics: root.adaptiveMetrics
        surfaceData: root.surfaceData
        dataShowCore: root.controller
        modelStore: root.modelStore
        view3DController: root.view3DController
        style: root.style
        height:root.height
        x:root.width- width -70
        y:25
    }

    MainShowMenu{
        id: mainShowMenu
        controller: root.controller
        surfaceData: root.surfaceData
        globalContext: root.globalContext
    }

}
