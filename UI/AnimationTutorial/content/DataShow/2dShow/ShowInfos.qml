import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    Column{
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

    Column{
        anchors.bottom: parent.bottom
        anchors.right: parent.right
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
                text: dataShowCore.sourceWidth
                background: Rectangle{
                    color: "#772e2e2e"
                }
            }
            Label{
                text: "x"
                color: "#747474"
            }
            Label{
                text: dataShowCore.sourceHeight
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
