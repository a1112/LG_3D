import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../../Model/server"
Item {
    width:200
    height:200
    id:root
    property ServerDefectModel defect: ServerDefectModel{}


    property real px_width:Math.min(Math.min(body.width,defect.defect_w)/defect.defect_w,
                                    Math.min(body.height,defect.defect_h)/defect.defect_h)
    Item{
        width: parent.width-6
        height: parent.height-6
        anchors.centerIn: parent

        Pane{
            anchors.fill: parent
            Material.elevation: 5
        }
        Frame{
            anchors.fill:parent
        }
        ColumnLayout{
            anchors.fill: parent
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
                    // if (defect.defect_w<body.width){

                    //     let out_w = (body.width - defect.defect_w)
                    //     console.log("out_w ",out_w," ", body.width)

                    //     x_=parseInt(x_-out_w/2)
                    //     w_=parseInt(w_+out_w)
                    // }
                    if (px_width*defectW <body.width){
                        let out_w = body.width/px_width-defectW
                        x_=parseInt(x_-out_w/2)
                        w_=parseInt(w_+out_w)
                    }

                    let y_=defect.defect_y
                    let h_=defect.defect_h
                    // if (defect.defect_h<body.height){
                    //     let out_h = (body.height - defect.defect_h)
                    //     y_=parseInt(y_-out_h/2 )
                    //     h_=parseInt(h_+out_h )
                    // }

                    if (px_width*defectH <body.height){
                        let out_h = body.height/px_width-defectH
                        y_=parseInt(y_-out_h/2)
                        h_=parseInt(h_+out_h)
                    }

                    // 外扩

                return api.defect_url(dataShowCore.coilId,dataShowCore.key,
                                      dataShowCore.currentViewKey,
                                      x_,y_,w_,h_
                                      )

                }
                }
                Rectangle{
                    border.width:1
                    border.color:"#88FF0000"
                    color:"#00000000"
                    anchors.centerIn: parent
                    width:px_width*defectW
                    height:px_width*defectH
                }
            }
    DefectInfos{

    }


    }


    }
    }

