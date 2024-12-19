import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    width:200
    height:200
    id:root
    property real px_width:Math.min(Math.min(body.width,defectW)/defectW,
                                    Math.min(body.height,defectH)/defectH)
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
                    let x_=defectX
                    let w_=defectW

                    if (px_width*defectW <body.width){
                        let out_w = body.width/px_width-defectW
                        x_=parseInt(x_-out_w/2)
                        w_=parseInt(w_+out_w/2)
                    }

                    let y_=defectY
                    let h_=defectH
                    if (px_width*defectH <body.height){
                        let out_h = body.height/px_width-defectH
                        y_=parseInt(y_-out_h/2)
                        h_=parseInt(h_+out_h/2)
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
                    border.color:"red"
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

