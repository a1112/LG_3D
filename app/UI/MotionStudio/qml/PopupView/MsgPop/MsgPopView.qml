pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Core/JsonUtils.js" as JsonUtils
Menu {
    id: menu
    required property var adaptiveMetrics
    required property var coreController
    required property var modelStore
    required property var apiClient
    required property var style

    width: menu.adaptiveMetrics.boundedWidth(700, 520, 900)
    height: menu.adaptiveMetrics.boundedHeight(500, 380, 680)
    ListModel{
        id:coreCoilModel
        dynamicRoles: true
    }
    function asText(value) {
        if (value === undefined || value === null) {
            return ""
        }
        return String(value)
    }
    function fixedText(value, digits) {
        let numberValue = Number(value)
        if (!isFinite(numberValue)) {
            return ""
        }
        return numberValue.toFixed(digits)
    }
    function initcoreCoil(){
        // 检查 currentCoilModel 是否存在
        if (!menu.coreController.currentCoilModel) {
            return
        }
        let coil = menu.coreController.currentCoilModel
        coreCoilModel.clear()
        coreCoilModel.append({
                                 "key": "流水号",
                                 "value": (coil.coilId || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "卷号",
                                 "value": (coil.coilNo || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "钢种",
                                 "value": (coil.coilType || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "内径",
                                 "value": (coil.coilInside || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "外径",
                                 "value": (coil.coilDia || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "厚度",
                                 "value": (coil.coilThickness || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "生产宽度",
                                 "value": (coil.coilWidth || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "实际宽度",
                                 "value": (coil.coilActWidth || "")+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "去向",
                                 "value": (coil.nextInfo || "")+""
                             }
                            )
    }

    property int detailsRequestGeneration: 0
    readonly property int currentCoilId: menu.coreController.currentCoilModel
                                         ? Number(menu.coreController.currentCoilModel.coilId || 0) : 0
    onCurrentCoilIdChanged: {
        if (menu.visible) {
            menu.refreshDetails()
        }
    }
    onAboutToShow: menu.refreshDetails()
    onAboutToHide: menu.detailsRequestGeneration += 1

    function refreshDetails() {
        menu.detailsRequestGeneration += 1
        let generation = menu.detailsRequestGeneration
        let requestedCoilId = menu.currentCoilId
        initcoreCoil()
        if (requestedCoilId <= 0) {
            return
        }
        menu.apiClient.getPlcData(requestedCoilId,
                       (result)=>{
                        if (generation !== menu.detailsRequestGeneration
                                || requestedCoilId !== menu.currentCoilId) {
                            return
                        }
                        var plcData = JsonUtils.parse(result, null, "PLC data")
                        // 检查数据是否存在再添加
                        if (plcData) {
                            if (plcData.location_S !== undefined && plcData.location_S !== null) {
                                coreCoilModel.append({
                                    "key": "设备位置_S",
                                    "value": plcData.location_S+""
                                })
                            }
                            if (plcData.location_L !== undefined && plcData.location_L !== null) {
                                coreCoilModel.append({
                                    "key": "设备位置_L",
                                    "value": plcData.location_L+""
                                })
                            }
                            if (plcData.location_laser !== undefined && plcData.location_laser !== null) {
                                coreCoilModel.append({
                                    "key": "激光",
                                    "value": plcData.location_laser+""
                                })
                            }
                        }
                       },
                       (error)=>{
                           console.log("getPlcData error:", error)
                       }
                       )
        menu.apiClient.getCoilState(requestedCoilId,(result)=>{
                            if (generation !== menu.detailsRequestGeneration
                                    || requestedCoilId !== menu.currentCoilId) {
                                return
                            }
                                var coilStateData = JsonUtils.parse(result, [], "coil state details")
                                for (let i=0;i<coilStateData.length;i++){
                                 var cData = coilStateData[i]
                                 var msg_item= msg_l
                                 // console.log("getCoilState result",cData["surface"])
                                 if (cData["surface"]==="S")
                                     {
                                        msg_item= msg_s
                                     menu.modelStore.surfaceS.medianZ=Number(cData["median_3d_mm"]) || 0
                                     menu.modelStore.surfaceS.medianZInt=Number(cData["median_3d"]) || 0

                                    }
                                    else
                                 {
                                    menu.modelStore.surfaceL.medianZ=Number(cData["median_3d_mm"]) || 0
                                    menu.modelStore.surfaceL.medianZInt=Number(cData["median_3d"]) || 0
                                 }

                                let model=msg_item.model
                                 msg_item.model.clear()



                                 model.append({
                                                  key: "标定X",
                                                  value: fixedText(cData["scan3dCoordinateScaleX"], 4)
                                              }
                                              )
                                 model.append({
                                                  key: "标定Y",
                                                  value: fixedText(cData["scan3dCoordinateScaleY"], 4)
                                              }
                                              )
                                 model.append({
                                                  key: "标定Z",
                                                  value: fixedText(cData["scan3dCoordinateScaleZ"], 4)
                                              }
                                              )
                                 model.append({
                                                  key: " ",
                                                  value: ""
                                              }
                                              )
                                 model.append({
                                                  key: "下报警mm",
                                                  value: fixedText(cData["colorFromValue_mm"], 4)
                                              }
                                              )
                                 model.append({
                                                  key: "上报警mm",
                                                  value: fixedText(cData["colorToValue_mm"], 4)
                                              }
                                              )
                                 model.append({
                                                  key: "下报警int",
                                                  value: cData["lowerLimit"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "上报警int",
                                                  value: cData["upperLimit"]+""
                                              }
                                              )

                                 model.append({
                                                  key: "报警int",
                                                  value: cData["start"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "报警范围int",
                                                  value: cData["step"]+""
                                              }
                                              )

                                 model.append({
                                                  key: "rotate",
                                                  value: cData["rotate"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "x_rotate",
                                                  value: cData["x_rotate"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "3d平均",
                                                  value: cData["median_3d"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "3d平均mm",
                                                  value: cData["median_3d_mm"]+""
                                              }
                                              )
                                model.append({
                                                  key: "宽度px",
                                                  value: cData["width"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "高度px",
                                                  value: cData["height"]+""
                                              }
                                              )

                                 model.append({
                                                  key: "卷像素面积",
                                                  value: cData["mask_area"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "卷面积",
                                                  value: ""
                                              }
                                              )
                                 model.append({
                                                  key: "下报警面积",
                                                  value: cData["lowerArea"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "上报警面积",
                                                  value: cData["upperArea"]+""
                                              }
                                              )
                                 model.append({
                                                  key: "下报警%",
                                                  value: fixedText(Number(cData["lowerArea_percent"]) * 100, 2)
                                              }
                                              )
                                 model.append({
                                                  key: "上报警%",
                                                  value: fixedText(Number(cData["upperArea_percent"]) * 100, 2)
                                              }
                                              )



                                }


                         },
                          (error)=>{
                              console.log("getCoilState error",error)
                                }
            )
    }


        Item{
            width: parent.width
            height: menu.height
        ColumnLayout{
            width: parent.width
            height: parent.height
            Label{
            text: "详细信息"
            Layout.alignment: Qt.AlignHCenter
            font.bold: true
            font.pointSize: menu.adaptiveMetrics.fontMetric(24, 18, 30)
            color: menu.style.titleColor
            }

            GridView{
                id:grid
                Layout.fillWidth: true
                height: 80
                cellWidth: grid.width/4
                cellHeight: 25
                model:coreCoilModel
                delegate:
                    RowItemView {
                        required property string key
                        required property string value

                        width: grid.cellWidth
                        itemKey: key
                        itemValue: value
                        style: menu.style
                    }
            }
            RowLayout{
                Layout.fillWidth: true
                Layout.fillHeight: true
                MsgItem{
                    id:msg_s
                    style: menu.style
                    title:"S端"
                    // surface:coreModel.surfaceS
                }
                MsgItem{
                    id:msg_l
                    style: menu.style
                    title:"L端"
                     // surface:coreModel.surfaceL
                }
            }


        }
}
}
