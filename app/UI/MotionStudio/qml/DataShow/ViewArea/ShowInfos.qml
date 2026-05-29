import QtQuick
import QtQuick.Controls
Item {
    Column{

        Row{
                spacing:10
        Row{
            Label{
                text: "X: "
                color: coreStyle.labelColor
            }
            Label{
                text: dataShowCore.hoverPoint.x.toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }

        }
        Row{
            Label{
                text: "Y: "
                color: coreStyle.labelColor
            }
            Label{
                text: dataShowCore.hoverPoint.y.toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }

        }
        }

        Row{
            Label{
                text: "宽: "
                color: coreStyle.labelColor
            }
            Label{
                text: (dataShowCore.sourceWidth*surfaceData.scan3dScaleX).toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "mm "
                color: coreStyle.labelColor
            }
        }
        Row{

            Label{

                text: "高: "
                color: coreStyle.labelColor
            }
            Label{
                text: (dataShowCore.sourceHeight*surfaceData.scan3dScaleY).toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "mm "
                color: coreStyle.labelColor
            }
        }


        Row{
            Label{
                text: dataAreaShowCore.sourceWidth
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "x"
                color: coreStyle.labelColor
            }
            Label{
                text: dataAreaShowCore.sourceHeight
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "px "
                color: coreStyle.labelColor
            }
        }

        // 瓦片信息
        Row{
            visible: dataAreaShowCore.sourceWidth > 0 && dataAreaShowCore.sourceHeight > 0
            Label{
                text: "瓦片: "
                color: coreStyle.labelColor
            }
            Label{
                text: parseInt(dataAreaShowCore.sourceWidth / 3) + "x" + parseInt(dataAreaShowCore.sourceHeight / 3)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "px "
                color: coreStyle.labelColor
            }
        }

        // 显示区域像素
        Row{
            visible: dataAreaShowCore.flick !== null
            Label{
                text: "显示: "
                color: coreStyle.labelColor
            }
            Label{
                text: dataAreaShowCore.flick.width + "x" + dataAreaShowCore.flick.height
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "px "
                color: coreStyle.labelColor
            }
        }
}
}
