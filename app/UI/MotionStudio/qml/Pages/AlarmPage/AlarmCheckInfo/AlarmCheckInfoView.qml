import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
import "../../../Pages/Header"
CardBase {
    id: root
    height: 70
    title: "判级"
    max_height: 70 + ta.implicitHeight
    property int currentPortInt: 0

    function setCurrentPortInt(currentPortInt_){
        currentPortInt = currentPortInt_
        coreControl.setCoilStatus(core.currentCoilModel.coilId, currentPortInt_, ta.text,
                                  (text)=>{

                                       },(err)=>{
                                  }
                                  )
        core.currentCoilModel.coilCheck.status = currentPortInt_
        core.currentCoilModel.coilCheck.msg = ta.text

    }
    // Timer{
    //     interval:120
    //     id : t
    // onTriggered:{
    //     currentPortInt = core.currentCoilModel.coilCheck.status
    //     ta.text = core.currentCoilModel.coilCheck.msg
    // }
    // }
    property var coilId: core.currentCoilModel
    onCoilIdChanged:{
        if (core.currentCoilModel.coilId<=0){
            return
        }
        api.getCoilStatus(core.currentCoilModel.coilId,
                          (text)=>{
                              let data = JSON.parse(text)
                                console.log("getCoilStatus ",core.currentCoilModel.coilId,"  ",typeof(text),"  ", text)
                                ta.text =  data["msg"]
                                root.currentPortInt = data["status"]

                              core.currentCoilModel.coilCheck.status = currentPortInt
                              core.currentCoilModel.coilCheck.msg = ta.text

                          }

                            ,

                          (err)=>{}
                          )

        // core.currentCoilModel.coilCheck.status = currentPortInt
        // ta.text = core.currentCoilModel.coilCheck.msg
    }

    // title_vis:false
    content_body: ColumnLayout{
        width :root.width
        RowLayout{
            //width :root.width
            Layout.fillWidth:true
            height:30

                Item{
                    width:20
                    height:5
                }
                CheckRec{
                    fillWidth: true
                    text : "返修"
                    color: root.currentPortInt == 2? "red": coreStyle.textColor
                    checkColor: root.currentPortInt == 2?color:"#00000000"
                    onClicked:{
                        root.setCurrentPortInt(2)
                    }
                }
                Item{
                Layout.fillWidth:true
                height:1
                }

                CheckRec{
                    fillWidth: true
                    text : "未确认"
                    color: root.currentPortInt == 0? "yellow": coreStyle.textColor
                    checkColor: root.currentPortInt == 0?color:"#00000000"
                    onClicked:{
                        root.setCurrentPortInt(0)
                    }
                }
                Item{
                Layout.fillWidth:true
                height:1
                }

                CheckRec{
                    fillWidth: true
                    text : "通过"
                    color: root.currentPortInt == 1? "green": coreStyle.textColor
                    checkColor: root.currentPortInt == 1?color:"#00000000"
                    onClicked:{
                         root.setCurrentPortInt(1)
                    }
                }
                Item{
                    width:20
                    height:5
                }

        }

        TextArea{
            id:ta
            Layout.fillWidth:true
            Layout.fillHeight:true
            // width :root.width
            // height:20
        }
    }

    CheckLabel{
        anchors.right:parent.right

    }
}
