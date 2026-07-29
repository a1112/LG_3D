import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../../Model/server"
ItemDelegate {

    id:root
    required property var controller
    required property var areaController
    required property var surfaceData
    required property var style
    required property var apiClient
    required property var defectClassController

    property ServerDefectModel defect: ServerDefectModel{}
    readonly property int defectImageWidth: root.defect.isArea
                                            ? (root.controller.dataShowAreaCore.sourceWidth
                                               || root.controller.sourceWidth || 5000)
                                            : (root.controller.sourceWidth || 5000)
    readonly property int defectImageHeight: root.defect.isArea
                                             ? (root.controller.dataShowAreaCore.sourceHeight
                                                || root.controller.sourceHeight || 5000)
                                             : (root.controller.sourceHeight || 5000)


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
                        let x_ = root.defect.defect_x
                        let w_ = root.defect.defect_w
                        let imgW = root.defectImageWidth

                        if (root.px_width * root.defect.defect_w < body.width ){
                            let out_w = body.width / root.px_width - root.defect.defect_w
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

                        let y_ = root.defect.defect_y
                        let h_ = root.defect.defect_h
                        let imgH = root.defectImageHeight

                        if (root.px_width * root.defect.defect_h < body.height){
                            let out_h = body.height / root.px_width - root.defect.defect_h
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

                        let viewKey = root.defect.isArea
                                      ? "AREA" : root.controller.currentViewKey
                        return root.apiClient.defect_url(
                                    root.controller.coilId,
                                    root.controller.key,
                                    viewKey, x_, y_, w_, h_)
                    }

                }
                Rectangle{
                    border.width : 1
                    border.color : "#88FF0000"
                    color : "#00000000"
                    anchors.centerIn : parent
                    width : root.px_width * root.defect.defect_w
                    height : root.px_width * root.defect.defect_h
                }

                MouseArea{
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    anchors.fill:parent
                    onClicked: function(mouse) {

                        if(root.defect.isArea)
                            root.surfaceData.rootViewtoArea()
                        else {
                            root.surfaceData.rootViewto2D()
                        }

                        if (mouse.button === Qt.LeftButton){
                            root.areaController.setDefectShowView(root.defect)
                        }
                        if (mouse.button === Qt.RightButton)
                        {
                            root.controller.setToMinScale()
                        }
                    }

                }
            }
            DefectInfos{
                defect: root.defect
                defectClassController: root.defectClassController
            }
        }
    }
    Rectangle{
        anchors.fill: parent
        color: "#00000000"
        border.width: 2
        opacity: 0.5
        border.color: root.style.accentColor
        visible: root.defect.isArea
    }

}

