import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../btns"
import "../Foot"
import "../../Pages/Header"
Item {
    id:root
    height: 27
    Pane{
        id: pane
        anchors.fill: parent
        Material.elevation:6
    }
    MouseArea{
        anchors.fill: parent
        onDoubleClicked: {
            surfaceData.showMax = !surfaceData.showMax
        }
    }

    RowLayout{
        anchors.fill: parent
        spacing: 3
        Row{
            spacing: 5
            ItemDelegate{
                height: 20
                text: "缩放：" + ( dataShowCore.canvasScale*100).toFixed(0) + "%"
                onClicked: {
                    menu_scale.open()
                }
                Rectangle{
                    anchors.fill: parent
                    color:dataShowCore.errorScaleColor
                    opacity: dataShowCore.errorScaleSignal?1:0
                    Behavior on opacity {
                        NumberAnimation {
                            duration: 800
                        }
                    }
                    Timer{
                        interval: 800
                        running:dataShowCore.errorScaleSignal
                        onTriggered: {
                            dataShowCore.errorScaleSignal = false
                        }
                    }
                }
            }

            CheckRec{
                visible:false
                height: 20
                text: "亮度"
                // visible: dataShowCore.image_is_gray
                checkColor: Material.color(Material.Red)
                onCheckedChanged: dataShowCore.image_gamma_enable_btn = checked
                checked: dataShowCore.image_gamma_enable_btn
            }
            Slider{
                visible: dataShowCore.image_gamma_enable
                id:gammaSlider
                width:100
                height:20
                    from: 0.3
                    value: dataShowCore.image_gamma
                    onValueChanged: {
                        dataShowCore.image_gamma = gammaSlider.value
                    }
                    to: 1.3
                    stepSize:0.05
            }
            Label{
                visible: dataShowCore.image_gamma_enable
                height: 20
                text: gammaSlider.value.toFixed(2)
            }


        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }

        Label{
            font.bold: true
            text:surfaceData.key+"   "
            font.pointSize: 16
            color: surfaceData.keyColor
        }
        Label{
            font.bold: true
            text:surfaceData.rootViewIndex==0?surfaceData.currentViewKey: "3D"
        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        CheckRec{
            visible: false
            height: 20
            text: "塔形"
            checked: dataShowCore.telescopedJointView
            onCheckedChanged: {
                 dataShowCore.telescopedJointView=!dataShowCore.telescopedJointView
                // dataShowCore.resetView()
            }
        }


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


    Popup{
        id: popup
        width: showViewListView.width+20
        height: showViewListView.height
        topMargin : 0
        leftMargin: 0
        bottomMargin: 0
        rightMargin: 0
        topPadding: 0
        leftPadding: 0
        bottomPadding: 0
        rightPadding: 0
        y: 30
        x: parent.width - width-30
        Material.elevation: 12

        ShowViewListView{
            id:showViewListView
            implicitHeight: 100
            width: 300
        }

        HoverHandler{
            id:hoverHandlerPop
        }
    }
}
