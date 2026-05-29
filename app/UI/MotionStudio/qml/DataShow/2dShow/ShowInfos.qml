import QtQuick
import QtQuick.Controls
Item {
    Column{
        Row{
                spacing:10
        Label{
            text:dataShowCore_.coilId
            color:"green"
            background: Rectangle{
                color: "#772e2e2e"
            }
        }
        Label{
            text:dataShowCore_.coilId
            color:"green"
            background: Rectangle{
                color: "#772e2e2e"
            }
        }

        }
        Row{
                spacing:10
        Row{
            Label{
                text: "X: "
                color: coreStyle.labelColor
            }
            Label{
                text: dataShowCore_.hoverPoint.x.toFixed(0)
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
                text: dataShowCore_.hoverPoint.y.toFixed(0)
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
                text: (dataShowCore_.sourceWidth*dataShowCore_.scan3dScaleX).toFixed(0)
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
                text: (dataShowCore_.sourceHeight*dataShowCore_.scan3dScaleY).toFixed(0)
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
                text: dataShowCore_.sourceWidth
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "x"
                color: coreStyle.labelColor
            }
            Label{
                text: dataShowCore_.sourceHeight
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
