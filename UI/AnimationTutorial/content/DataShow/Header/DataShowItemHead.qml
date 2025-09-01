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
    height: 27

    RowLayout{
        anchors.fill: parent
        spacing: 20
        Row{
            spacing: 5
            ScaleBtn{}
            GammaBtn{
             visible: surfaceData.is2DrootView
            }
        }
            ToolBtns{
                visible: ! surfaceData.is3DrootView
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
            visible: surfaceData.is3DrootView
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
            selected:surfaceData.rootViewIndex  == 2
            onClicked: {
                surfaceData.rootViewtoArea()  // 2
            }
        }

        ItemDelegateItemLabel {
            key:qsTr("JPG")
            height: 20
            text: surfaceData.currentViewKey
            selected:surfaceData.rootViewIndex==0
            onClicked: {
                surfaceData.rootViewto2D()
            }

            HoverHandler{
                id:hoverHandler2D
            }
        }
        ItemDelegateItemLabel {
            height: 20
            key:"MESH"
            text: qsTr("3D")
            selected:surfaceData.rootViewIndex==1
            onClicked: surfaceData.rootViewto3D()
        }
        }


        Row{
            WindowModelChangeButton {
                height:25
                width: 25
                shouMaxIcon:surfaceData.showMax
                onClicked: {
                    surfaceData.showMax = !surfaceData.showMax
                }
            }
        }
    }
    Menu{
        id: menu_scale
        Repeater{
            model: 6
            MenuItem{
                text: ((dataShowCore_.minScale+((1-dataShowCore_.minScale)/5 * (modelData)))*100).toFixed(0) + "%"
                onClicked: {
                    dataShowCore_.canvasScale = dataShowCore_.minScale+((1-dataShowCore_.minScale)/5 * (modelData))
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
