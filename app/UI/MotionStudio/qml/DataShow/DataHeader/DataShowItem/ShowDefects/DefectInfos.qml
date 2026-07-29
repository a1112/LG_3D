import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item{
    id: root

    required property var defect
    required property var defectClassController

    Layout.fillWidth: true
    height: col.height


    ColumnLayout{
        id:col
        width: parent.width
        RowLayout{
            Layout.alignment:Qt.AlignHCenter

            Label{
                text:"2D "
                font.pointSize: 15
                color: "blue"
                visible: root.defect.isArea
            }
            Label{
                text: root.defect.defect_name
                font.pointSize: 20
                MouseArea{
                    anchors.fill:parent
                    acceptedButtons:Qt.RightButton
                    onClicked:{
                        defectMenu.popup()
                    }
                }
            }

        }
        Item{
            Layout.fillWidth: true
            width: parent.width
            height: 50
            GridView {
                id:grid
                width: parent.width
                cellWidth: grid.width/2
                cellHeight: 25
                height:50
                model:ListModel{
                    id:msgModel
                    dynamicRoles: true
                }
                delegate:RowItemView{
                }
                Component.onCompleted: {
                    msgModel.clear()
                    msgModel.append({
                                        key:"x",
                                        value: root.defect.defect_x_mm
                                    })
                    msgModel.append({
                                        key:"y",
                                        value: root.defect.defect_y_mm
                                    })
                    msgModel.append({
                                        key:"宽",
                                        value: root.defect.defect_w_mm
                                    })
                    msgModel.append({
                                        key:"高",
                                        value: root.defect.defect_h_mm
                                    })
                }
            }
        }
    }

    HoverHandler{
        id : hovrHanller
    }
    DefectSelectMenu{
        id : defectMenu
        defect: root.defect
        defectClassController: root.defectClassController
    }

}
