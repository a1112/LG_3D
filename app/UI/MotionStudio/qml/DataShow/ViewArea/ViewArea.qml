import QtQuick
import QtQuick.Controls
import "../Aerial"
import "../Comps"
Item {
    id:root

    required property var dataAreaShowCore
    required property var style
    required property var globalContext
    required property var apiClient
    required property var settings
    required property var surfaceData

    anchors.fill: parent


    Flickable{
        id:flick
        clip: true
        anchors.fill: parent
        contentWidth: root.dataAreaShowCore.canvasContentWidth
        contentHeight: root.dataAreaShowCore.canvasContentHeight
        Component.onCompleted: {
            root.dataAreaShowCore.flick = this
        }
        ScrollBar.vertical: ScrollBar {
            id:scrollBarV
        }
        ScrollBar.horizontal: ScrollBar {
            id:scrollBarH
        }
        Item{
            id:canvas
            width: root.dataAreaShowCore.canvasContentWidth
            height: root.dataAreaShowCore.canvasContentHeight

            ImageView {
                areaController: root.dataAreaShowCore
                apiService: root.apiClient
                settingsStore: root.settings
                surfaceData: root.surfaceData
                appStyle: root.style
            }

            ShowDefects { // 缺陷绘制
                controller: root.dataAreaShowCore
                defectClassController: root.globalContext.defectClassProperty
                style: root.style
            }
            ControlView {
                controller: root.dataAreaShowCore
                flickable: flick
                style: root.style
            }
        }

    }

    AerialView{// 鸟亏图
        source: root.dataAreaShowCore.pre_source  // 缩略图像
        controller: root.dataAreaShowCore
        style: root.style
        y:root.height - height-scrollBarH.height
    }


}
