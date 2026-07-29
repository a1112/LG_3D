import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
import "../../../Pages/Header"
import "../../../Core/JsonUtils.js" as JsonUtils
CardBase {
    id: root
    height: 70
    title: "判级"
    max_height: 70 + ta.implicitHeight
    property int currentPortInt: 0
    property int statusRequestGeneration: 0

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
    readonly property int coilId: core.currentCoilModel
                                  ? Number(core.currentCoilModel.coilId || 0) : 0
    onCoilIdChanged: {
        root.statusRequestGeneration += 1
        let generation = root.statusRequestGeneration
        let requestedCoilId = root.coilId
        if (requestedCoilId <= 0) {
            root.currentPortInt = 0
            ta.text = ""
            return
        }
        api.getCoilStatus(requestedCoilId,
                          (text)=>{
                              if (generation !== root.statusRequestGeneration
                                      || requestedCoilId !== root.coilId) {
                                  return
                              }
                              let data = JsonUtils.parse(text, null, "coil status")
                              if (!data || typeof data !== "object") {
                                  return
                              }
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
                    color: root.currentPortInt == 2
                           ? coreStyle.statusErrorColor : coreStyle.textColor
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
                    color: root.currentPortInt == 0
                           ? coreStyle.statusWarningColor : coreStyle.textColor
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
                    color: root.currentPortInt == 1
                           ? coreStyle.statusSuccessColor : coreStyle.textColor
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
