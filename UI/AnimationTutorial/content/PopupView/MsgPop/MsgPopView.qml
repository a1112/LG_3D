import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Menu {
    id:menu
    width: 700
    height: 500
    ListModel{
        id:coreCoilModel
    }
    function initcoreCoil(){
        coreCoilModel.clear()
        coreCoilModel.append({
                                 "key": "流水号",
                                 "value": core.currentCoilModel.coilId+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "卷号",
                                 "value": core.currentCoilModel.coilNo+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "钢种",
                                 "value": core.currentCoilModel.coilType+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "内径",
                                 "value": core.currentCoilModel.coilInside+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "外径",
                                 "value": core.currentCoilModel.coilDia+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "厚度",
                                 "value": core.currentCoilModel.coilThickness+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "生产宽度",
                                 "value": core.currentCoilModel.coilWidth+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "实际宽度",
                                 "value": core.currentCoilModel.coilActWidth+""
                             }
                            )
        coreCoilModel.append({
                                 "key": "去向",
                                 "value": core.currentCoilModel.nextInfo+""
                             }
                            )
    }

    property string currentCoilNo: core.currentCoilModel.coilNo
    onCurrentCoilNoChanged: {
        initcoreCoil()
        api.getPlcData(core.currentCoilModel.coilId,
                       (result)=>{
                        var plcData=JSON.parse(result)
                           coreCoilModel.append({
                                                    "key": "设备位置_S",
                                                    "value": plcData.location_S+""
                                                }
                                               )
                           coreCoilModel.append({
                                                    "key": "设备位置_L",
                                                    "value": plcData.location_L+""
                                                }
                                               )
                           coreCoilModel.append({
                                                    "key": "激光",
                                                    "value": plcData.location_laser+""
                                                }
                                               )
                       },
                       (error)=>{

                       }
                       )
        api.getCoilState(core.currentCoilModel.coilId,(result)=>{
                            var t = [{"scan3dCoordinateScaleX":0.339437,"colorFromValue_mm":-20.0,"lowerArea_percent":0.00707693,
                                  "scan3dCoordinateScaleY":1.0,"colorToValue_mm":20.0,"upperArea_percent":3.6634e-05,
                                  "Id":307,"scan3dCoordinateScaleZ":0.0161155,"start":46595.4,"mask_area":25249781,
                                  "rotate":-90,"step":2483.0,"width":6995,"secondaryCoilId":1868,
                                  "x_rotate":10,"upperLimit":6205.2,"height":5180,"median_3d":47837.4,
                                  "lowerLimit":-3102.6,
                                  "jsonData":"{'coilId': '1868', 'direction': 'R', 'startTime': datetime.datetime(2024, 8, 16, 17, 28, 54, 517439), 'scan3dCoordinateScaleX': 0.33943653106689453, 'scan3dCoordinateScaleY': 1.0, 'scan3dCoordinateScaleZ': 0.016115527600049973, 'crossPoints': [(2275, 63), (2362, 359)], 'rotate': -90, 'crop_box': (1, 1538, 6995, 5180), 'x_rotate': 10, 'median_3d': 47837.397452758094, 'median_3d_mm': 770.9248989644833, 'colorFromValue_mm': -20, 'colorToValue_mm': 20, 'start': 46595.397452758094, 'step': 2483.0, 'upperLimit': 6205.19554070882, 'lowerLimit': -3102.59777035441, 'lowerArea': 178691, 'upperArea': 925, 'lowerArea_percent': 0.00707693266725759, 'upperArea_percent': 3.663398110264798e-05, 'mask_area': 25249781, 'width': 6995, 'height': 5180, 'circleConfig': {'inner_circle': {'circlex': [3521, 2971, 1337], 'ellipse': ((3527.085693359375, 2853.949462890625), (1946.699951171875, 2614.9560546875), 89.48193359375), 'inner_circle': [(3521.5, 2852.0), 986.0]}}}",
                                  "surface":"R","median_3d_mm":null,"lowerArea":178691,
                                  "startTime":{"year":2024,"month":8,"weekday":4,"day":16,"hour":17,"minute":28,"second":55},
                                  "upperArea":925},

                                {"scan3dCoordinateScaleX":0.339437,
                                    "colorFromValue_mm":-20.0,
                                  "lowerArea_percent":0.00812553
                                ,"scan3dCoordinateScaleY":1.0,
                                    "colorToValue_mm":20.0,
                                  "upperArea_percent":0.000164062,
                                         "Id":306,
                                         "scan3dCoordinateScaleZ":0.0161155,
                                         "start":54211.2,
                                        "mask_area":25715871,
                                         "rotate":90,
                                         "step":2483.0,
                                         "width":7024,
                                         "secondaryCoilId":1868,
                                  "x_rotate":17,
                                    "upperLimit":6205.2,
                                    "height":5336,
                                    "median_3d":55453.2,
                                  "lowerLimit":-3102.6,
                                  "jsonData":
                                         "{'coilId': '1868', 'direction': 'L', 'startTime': datetime.datetime(2024, 8, 16, 17, 28, 54, 608487), 'scan3dCoordinateScaleX': 0.33943653106689453, 'scan3dCoordinateScaleY': 1.0, 'scan3dCoordinateScaleZ': 0.016115527600049973, 'crossPoints': [(2236, 188), (2068, 377)], 'rotate': 90, 'crop_box': (4164, 1401, 7024, 5336), 'x_rotate': 17, 'median_3d': 55453.21641044834, 'median_3d_mm': 893.6578395741243, 'colorFromValue_mm': -20, 'colorToValue_mm': 20, 'start': 54211.21641044834, 'step': 2483.0, 'upperLimit': 6205.19554070882, 'lowerLimit': -3102.59777035441, 'lowerArea': 208955, 'upperArea': 4219, 'lowerArea_percent': 0.00812552683904815, 'upperArea_percent': 0.00016406210779327678, 'mask_area': 25715871, 'width': 7024, 'height': 5336, 'circleConfig': {'inner_circle': {'circlex': [3557, 2940, 1386], 'ellipse': ((3520.43310546875, 2854.49365234375), (2177.34033203125, 2689.84375), 83.79122924804688), 'inner_circle': [(3568.13720703125, 2891.76513671875), 1122.9912109375]}}}",
                                  "surface":"L",
                                         "median_3d_mm":null,
                                         "lowerArea":208955,
                                         "startTime":{"year":2024,"month":8,
                                   "weekday":4,"day":16,"hour":17,"minute":28,"second":55},"upperArea":4219}]


                                var coilStateData=JSON.parse(result)
                                for (let i=0;i<coilStateData.length;i++){
                                 var cData = coilStateData[i]
                                 var msg_item= msg_l
                                 // console.log("getCoilState result",cData["surface"])
                                 console.log("cData[median_3d_mm].toFixed(2)")
                                 console.log(cData["median_3d_mm"].toFixed(2))
                                 if (cData["surface"]==="S")
                                     {
                                        msg_item= msg_s
                                     coreModel.surfaceS.medianZ=cData["median_3d_mm"].toFixed(2)
                                     coreModel.surfaceS.medianZInt=cData["median_3d"].toFixed(2)

                                    }
                                    else
                                 {
                                    coreModel.surfaceL.medianZ=cData["median_3d_mm"].toFixed(2)
                                    coreModel.surfaceL.medianZInt=cData["median_3d"].toFixed(2)
                                 }

                                let model=msg_item.model
                                 msg_item.model.clear()



                                 model.append({
                                                  key: "标定X",
                                                  value: cData["scan3dCoordinateScaleX"].toFixed(4)+""
                                              }
                                              )
                                 model.append({
                                                  key: "标定Y",
                                                  value: cData["scan3dCoordinateScaleY"].toFixed(4)+""
                                              }
                                              )
                                 model.append({
                                                  key: "标定Z",
                                                  value: cData["scan3dCoordinateScaleZ"].toFixed(4)+""
                                              }
                                              )
                                 model.append({
                                                  key: " ",
                                                  value: ""
                                              }
                                              )
                                 model.append({
                                                  key: "下报警mm",
                                                  value: cData["colorFromValue_mm"].toFixed(4)+""
                                              }
                                              )
                                 model.append({
                                                  key: "上报警mm",
                                                  value: cData["colorToValue_mm"].toFixed(4)+""
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
                                                  value: +"？"
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
                                                  value: (cData["lowerArea_percent"]*100).toFixed(2)+""
                                              }
                                              )
                                 model.append({
                                                  key: "上报警%",
                                                  value: (cData["upperArea_percent"]*100).toFixed(2)+""
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
            font.pointSize:24
            color:Material.color(Material.Blue)
            }

            GridView{
                id:grid
                Layout.fillWidth: true
                height: 80
                cellWidth: grid.width/4
                cellHeight: 25
                model:coreCoilModel
                delegate:
                    RowItemView{}
            }
            RowLayout{
                Layout.fillWidth: true
                Layout.fillHeight: true
                MsgItem{
                    id:msg_s
                    title:"S端"
                    // surface:coreModel.surfaceS
                }
                MsgItem{
                    id:msg_l
                    title:"L端"
                     // surface:coreModel.surfaceL
                }
            }


        }
}
}
