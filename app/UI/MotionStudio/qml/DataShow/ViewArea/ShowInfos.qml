import QtQuick
import QtQuick.Controls
Item {
    Column{

        Row{
                spacing:10
        Row{
            Label{
                text: "X: "
                color: "#747474"
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
                color: "#747474"
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
                color: "#747474"
            }
            Label{
                text: (dataShowCore.sourceWidth*surfaceData.scan3dScaleX).toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "mm "
                color: "#747474"
            }
        }
        Row{

            Label{

                text: "高: "
                color: "#747474"
            }
            Label{
                text: (dataShowCore.sourceHeight*surfaceData.scan3dScaleY).toFixed(0)
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "mm "
                color: "#747474"
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
                color: "#747474"
            }
            Label{
                text: dataAreaShowCore.sourceHeight
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "px "
                color: "#747474"
            }
        }
}
}
