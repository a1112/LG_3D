import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../../Model/server"
ItemDelegate {

    id:root
    property ServerDefectModel defect: ServerDefectModel{}


    property real px_width:Math.min(Math.min(body.width,defect.defect_w)/defect.defect_w,
                                    Math.min(body.height,defect.defect_h)/defect.defect_h)
    Item{
        width: parent.width-6
        height: parent.height-6
        anchors.centerIn: parent

        Pane{
            anchors.fill : parent
            Material.elevation : 5
        }
        Frame{
            anchors.fill : parent
        }
        ColumnLayout{
            anchors.fill : parent
            Item{
                id:body
                Layout.fillHeight: true
                Layout.fillWidth: true
                Image{
                    anchors.centerIn: parent
                    width: parent.width
                    height: parent.height
                    asynchronous:true
                    fillMode: Image.PreserveAspectFit
                    source: {
                        let x_ = defect.defect_x
                        let w_ = defect.defect_w
                        let imgW = dataShowCore.sourceWidth || 5000

                        if ( px_width * defectW < body.width ){
                            let out_w = body.width/px_width-defectW
                            let left_expand = out_w/2
                            let right_expand = out_w/2

                            // 边界检查：左侧扩展不超过 0
                            if (x_ - left_expand < 0) {
                                right_expand += left_expand - x_  // 将左侧多余的扩展量加到右侧
                                left_expand = x_
                            }
                            // 边界检查：右侧扩展不超过图像宽度
                            if (x_ + w_ + right_expand > imgW) {
                                let excess = (x_ + w_ + right_expand) - imgW
                                if (left_expand >= excess) {
                                    left_expand -= excess
                                    right_expand = 0
                                } else {
                                    right_expand = imgW - (x_ + w_)
                                }
                            }

                            x_ = parseInt(x_-left_expand)
                            w_ = parseInt(w_+left_expand+right_expand)
                        }

                        let y_ = defect.defect_y
                        let h_ = defect.defect_h
                        let imgH = dataShowCore.sourceHeight || 5000

                        if (px_width*defectH <body.height){
                            let out_h = body.height / px_width - defectH
                            let top_expand = out_h/2
                            let bottom_expand = out_h/2

                            // 边界检查：顶部扩展不超过 0
                            if (y_ - top_expand < 0) {
                                bottom_expand += top_expand - y_
                                top_expand = y_
                            }
                            // 边界检查：底部扩展不超过图像高度
                            if (y_ + h_ + bottom_expand > imgH) {
                                let excess = (y_ + h_ + bottom_expand) - imgH
                                if (top_expand >= excess) {
                                    top_expand -= excess
                                    bottom_expand = 0
                                } else {
                                    bottom_expand = imgH - (y_ + h_)
                                }
                            }

                            y_=parseInt(y_ - top_expand)
                            h_=parseInt(h_+top_expand+bottom_expand)
                        }

                        return api.defect_url(dataShowCore.coilId, dataShowCore.key,
                                              dataShowCore.currentViewKey,
                                              x_,  y_, w_, h_
                                              )
                    }

                }
                Rectangle{
                    border.width : 1
                    border.color : "#88FF0000"
                    color : "#00000000"
                    anchors.centerIn : parent
                    width : px_width*defectW
                    height : px_width*defectH
                }

                MouseArea{
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    anchors.fill:parent
                    onClicked:{

                        if(defect.isArea)
                            surfaceData.rootViewtoArea()
                        else if (!defect.isArea){
                            surfaceData.rootViewto2D()
                        }

                        if (mouse.button === Qt.LeftButton){
                            dataShowCore_.setDefectShowView(  defect )
                        }
                        if (mouse.button === Qt.RightButton)
                        {
                            dataShowCore.setToMinScale()
                        }
                    }

                }
            }
            DefectInfos{

            }
        }
    }
    Rectangle{
        anchors.fill: parent
        color: "#00000000"
        border.width: 2
        opacity: 0.5
        border.color: "blue"
        visible: defect.isArea
    }

}

