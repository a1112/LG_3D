import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item{
    Layout.fillWidth: true
    height: col.height
    ColumnLayout{
        id:col
        width: parent.width
        RowLayout{
            Layout.alignment:Qt.AlignHCenter

            CheckButtonOk{
                visible:hovrHanller.hovered
            }

            Label{
                text:defect.defect_name
                font.pointSize: 20
                MouseArea{
                    anchors.fill:parent
                    acceptedButtons:Qt.RightButton
                    onClicked:{
                        defectMenu.popup()
                    }
                }
            }

            CheckButtonNo{
                visible:hovrHanller.hovered
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
                }
                delegate:RowItemView{
                }
                Component.onCompleted: {
                    msgModel.clear()
                    // msgModel.append({
                    //                 key:"id",
                    //                 value:Id
                    //                 })
                    // msgModel.append({
                    //                 key:"名称",
                    //                 value:defectName
                    //                 })
                    msgModel.append({
                                        key:"x",
                                        value:defect.defect_x_mm
                                    })
                    msgModel.append({
                                        key:"y",
                                        value:defect.defect_y_mm
                                    })
                    msgModel.append({
                                        key:"宽",
                                        value:defect.defect_w_mm
                                    })
                    msgModel.append({
                                        key:"高",
                                        value:defect.defect_h_mm
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
    }

}
