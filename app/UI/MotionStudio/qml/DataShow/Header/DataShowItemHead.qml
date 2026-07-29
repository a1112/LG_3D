pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../btns"
import "../Foot"

import "../Core"
HeaderBase {
    // 数据显示标签
    id:root
    required property var surfaceData
    required property var controller
    required property var areaController
    required property var style

    height: 27

    RowLayout{
        anchors.fill: parent
        spacing: 20
        Row{
            spacing: 5
            ScaleBtn{
                controller: root.areaController
                menuController: menu_scale
            }
            GammaBtn{
                visible: root.surfaceData.is2DrootView
                controller: root.controller
            }
        }
            ToolBtns{
                visible: !root.surfaceData.is3DrootView
                controller: root.controller
                style: root.style
            }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }

        HeaderTitle{}

        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        Row{
            spacing: 10
            visible: root.surfaceData.is3DrootView
            View3DZScaleBtn{
                anchors.verticalCenter:parent.verticalCenter
            }
            View3DChangeItem{

            }
        }

        // CheckRec{
        //     visible: false
        //     height: 20
        //     text: "塔形"
        //     checked: dataShowCore.telescopedJointView
        //     onCheckedChanged: {
        //          dataShowCore.telescopedJointView=!dataShowCore.telescopedJointView
        //         // dataShowCore.resetView()
        //     }
        // }
        Row{
        ItemDelegateItemLabel {
            height: 20
            text: qsTr("2D")
            key:qsTr("2D")
            has_data: true
            selected: root.surfaceData.rootViewIndex === 2
            onClicked: {
                root.surfaceData.rootViewtoArea()
            }
        }

        ItemDelegateItemLabel {
            key: root.surfaceData.currentViewKey
            has_data: true
            height: 20
            text: root.surfaceData.currentViewKey
            selected: root.surfaceData.rootViewIndex === 0
            onClicked: {
                root.surfaceData.rootViewto2D()
            }

            HoverHandler{
                id:hoverHandler2D
            }
        }
        ItemDelegateItemLabel {
            height: 20
            key:"MESH"
            text: qsTr("3D")
            selected: root.surfaceData.rootViewIndex === 1
            onClicked: root.surfaceData.rootViewto3D()
        }
        }


        Row{
            WindowModelChangeButton {
                height:25
                width: 25
                shouMaxIcon: root.surfaceData.showMax
                onClicked: {
                    root.surfaceData.showMax = !root.surfaceData.showMax
                }
            }
        }
    }
    Menu{
        id: menu_scale
        Repeater{
            model: 6
            MenuItem{
                required property int modelData
                text: ((root.areaController.minScale
                        + ((1 - root.areaController.minScale) / 5
                           * modelData)) * 100).toFixed(0) + "%"
                onClicked: {
                    root.areaController.canvasScale =
                        root.areaController.minScale
                        + ((1 - root.areaController.minScale) / 5
                           * modelData)
                }
            }
        }
    }

    Timer{
        id:t
        interval: 300
        onTriggered: {
            popup.close()
        }
    }

    property bool in2D:hoverHandler2D.hovered||popup.hovered
    onIn2DChanged: {
        if(in2D){
            popup.open()
            t.stop()
        }else{
            t.start()
        }
    }


    Popup2D{
        id: popup

    }
    TitleMenu{
        id:titleMenu
    }
}
