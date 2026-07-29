import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
import "../../../Pages/Header"
import "../../../Core/JsonUtils.js" as JsonUtils
CardBase {
    id: root

    required property var style
    required property var authManager
    required property var apiClient
    required property var coreController
    required property var leftController

    cardStyle: root.style
    cardAuthManager: root.authManager

    readonly property var currentCoil: root.coreController.currentCoilModel

    height: 70
    title: qsTr("判级")
    max_height: 70 + ta.implicitHeight
    property int currentPortInt: 0
    property int statusRequestGeneration: 0
    property int statusWriteGeneration: 0

    function setCurrentPortInt(nextStatus) {
        const requestedCoilId = root.coilId
        if (requestedCoilId <= 0) {
            return
        }
        const previousStatus = root.currentPortInt
        const previousMessage = root.currentCoil.coilCheck.msg
        const nextMessage = ta.text
        const generation = ++root.statusWriteGeneration

        root.currentPortInt = nextStatus
        root.currentCoil.coilCheck.status = nextStatus
        root.currentCoil.coilCheck.msg = nextMessage
        root.apiClient.setCoilStatus(
            requestedCoilId,
            nextStatus,
            nextMessage,
            function() {},
            function(error) {
                if (generation !== root.statusWriteGeneration
                        || requestedCoilId !== root.coilId) {
                    return
                }
                root.currentPortInt = previousStatus
                root.currentCoil.coilCheck.status = previousStatus
                root.currentCoil.coilCheck.msg = previousMessage
                ta.text = previousMessage
                console.warn("coil status update failed:", error)
            })
    }
    // Timer{
    //     interval:120
    //     id : t
    // onTriggered:{
    //     currentPortInt = core.currentCoilModel.coilCheck.status
    //     ta.text = core.currentCoilModel.coilCheck.msg
    // }
    // }
    readonly property int coilId: root.currentCoil
                                  ? Number(root.currentCoil.coilId || 0) : 0
    onCoilIdChanged: {
        root.statusRequestGeneration += 1
        root.statusWriteGeneration += 1
        let generation = root.statusRequestGeneration
        let requestedCoilId = root.coilId
        if (requestedCoilId <= 0) {
            root.currentPortInt = 0
            ta.text = ""
            return
        }
        root.apiClient.getCoilStatus(requestedCoilId,
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

                              root.currentCoil.coilCheck.status = root.currentPortInt
                              root.currentCoil.coilCheck.msg = ta.text

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
                           ? root.style.statusErrorColor : root.style.textColor
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
                           ? root.style.statusWarningColor : root.style.textColor
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
                           ? root.style.statusSuccessColor : root.style.textColor
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
        statsController: root.leftController
    }
}
