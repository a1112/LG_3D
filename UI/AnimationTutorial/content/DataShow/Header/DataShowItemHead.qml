import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../btns"
import "../Foot"

import "../Core"
HeaderBase {
    id:root
    height: 27

    RowLayout{
        anchors.fill: parent
        spacing: 3
        Row{
            spacing: 5
            ScaleBtn{}
            GammaBtn{}
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
        ItemDelegateItem {
            height: 20
            text: surfaceData.currentViewKey
            selected:surfaceData.rootViewIndex==0
            onClicked: {
                surfaceData.rootViewIndex = 0
            }

            HoverHandler{
                id:hoverHandler2D
            }
        }
        ItemDelegateItem {
            height: 20
            text: "3D"
            selected:surfaceData.rootViewIndex==1
            onClicked: surfaceData.rootViewIndex = 1
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
                text: ((dataShowCore.minScale+((1-dataShowCore.minScale)/5 * (modelData)))*100).toFixed(0) + "%"
                onClicked: {
                    dataShowCore.canvasScale = dataShowCore.minScale+((1-dataShowCore.minScale)/5 * (modelData))
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

    property bool in2D:hoverHandler2D.hovered||hoverHandlerPop.hovered
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
