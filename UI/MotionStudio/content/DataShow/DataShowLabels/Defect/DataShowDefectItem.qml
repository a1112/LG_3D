import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Base"
import "../../../btns"
import "../../Core"
import "../../../Core"
import "../../../Comp/Card"
CardBase {
    id:root
    Layout.fillWidth: true
    max_height:170
    property SurfaceData surfaceData
    property DataShowCore dataShowCore: DataShowCore{
    }
    // Pane{
    //     width: parent.width
    //     height: parent.height-5
    //     Material.elevation: 6
    // }
    // Rectangle{
    //     color:"transparent"
    //     anchors.fill: parent
    //     border.color: Material.color(Material.Blue)
    //     border.width: 1
    // }
    // ItemDelegate{
    //     anchors.fill: parent
    // }
content_body:
    Flow{
        Layout.fillWidth: true
        Layout.fillHeight: true
        FlowRowItem{
            title:"外圈塔形  "
            value:" 100 mm"

        }

        FlowRec{
        }
        FlowRowItem{
            title:"内圈塔形  "
            value:" 100 mm"
        }

        FlowRec{
        }
        FlowRowItem{
            title:"扁卷    "
            value:"655 mm"
        }

        FlowRec{
        }
        FlowRowItem{
            title:"松卷    "
            value:"----"
        }

        FlowRec{
        }
    }


    // ColumnLayout{
    //     id:col
    //     width:parent.width
    //     // Row{
    //     //     Layout.alignment: Qt.AlignHCenter
    //     //     LabelBase{
    //     //         text: title
    //     //         color: Material.color(Material.Blue)
    //     //         font.pixelSize: 20
    //     //         font.bold:true
    //     //     }
    //     // }
    //     Flow{
    //         Layout.fillWidth: true
    //         Layout.fillHeight: true
    //         FlowRowItem{
    //             title:"外圈塔形  "
    //             value:" 100 mm"

    //         }

    //         FlowRec{
    //         }
    //         FlowRowItem{
    //             title:"内圈塔形  "
    //             value:" 100 mm"
    //         }

    //         FlowRec{
    //         }
    //         FlowRowItem{
    //             title:"扁卷    "
    //             value:"655 mm"
    //         }

    //         FlowRec{
    //         }
    //         FlowRowItem{
    //             title:"松卷    "
    //             value:"----"
    //         }

    //         FlowRec{
    //         }
    //     }

    // }
}
