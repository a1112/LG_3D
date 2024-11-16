import QtQuick
import QtQuick.Controls.Material
import "_base_"
CoreModel_ {

    property CoreGlobalError coreGlobalError:CoreGlobalError{}

    property int maxCoilListModelLen: 500

    property int currentCoilListIndex: 0

    readonly property bool isListRealModel:currentCoilListIndex==0
    readonly property bool isListHistoryModel:currentCoilListIndex==1

    function listToRealModel(){
        currentCoilListIndex=0
    }
    function listToHistoryModel(){
        currentCoilListIndex=1
    }

    function switchListModel(){
        if(isListRealModel){
            listToHistoryModel()
        }
        else{
            listToRealModel()
        }
        }

    readonly property color currentCoilListTextColor: currentCoilListIndex === 0 ? Material.color(Material.Green) : Material.color(Material.Yellow)
    property ListModel historyCoilListModel: ListModel{
    }

    property ListModel coilListModel: ListModel{  // list
    }

    property ListModel realCoilListModel: coilListModel

    readonly property ListModel currentCoilListModel: currentCoilListIndex === 0 ? realCoilListModel : historyCoilListModel
    function getCurrentCoilListModelMinMaxId(){
        return [currentCoilListModel.get(currentCoilListModel.count-1).Id,currentCoilListModel.get(0).Id]
    }
    function getCurrentCoilListModelMinMaxDateTime(){
        return [currentCoilListModel.get(currentCoilListModel.count-1).DateTime,currentCoilListModel.get(0).DateTime]
    }


    property int lastCoilId: 0

    property ListModel surfaceModel: ListModel{
    }

    function setShowMax(key,value){
        if(key === "L"){
            surfaceS.show_visible=!surfaceS.show_visible
        }
        else if(key === "S"){
            surfaceL.show_visible=!surfaceL.show_visible
        }
    }

    property SurfaceData surfaceL: SurfaceData{
        currentCoilModel: core.currentCoilModel
        key:"L"
    }

    property SurfaceData surfaceS: SurfaceData{
        currentCoilModel: core.currentCoilModel
        key:"S"
    }


    property var errorMap: {return {}}
    property var rendererList: []
    property var colorMaps: {return {}}
    property string saveImageType: "png"
    property var previewSize: [512,512]

    property var t:
    {"coilList":
     [
         [
             {"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23201,
                 "DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":8},
                 "CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23201,"DefectCountL":0,"Status_L":0,
                 "Grade":0,"AlarmInfo":{"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"",
                         "crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":5},"nextCode":"7",
                         "secondaryCoilId":23201,"Id":351,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,
                         "defectGrad":1,"grad":1,"data":null},"L":
                     {"surface":"L","taperShapeMsg":"正常外径最高值 235.62888012066344 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常",
                         "defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":5}
                         ,"nextCode":"7","secondaryCoilId":23201,"Id":352,"nextName":"外委横切(配送)","taperShapeGrad":3,
                         "looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,
                 "ActWidth":1069,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":35,
                     "second":52}
                 ,"CoilNo":"4V08329700","CoilInside":762,"CoilDia":1838,"Thickness":2.3,
                 "childrenAlarmInfo":
                     [{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常",
                         "defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":5}
                         ,"nextCode":"7","secondaryCoilId":23201,"Id":351,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,
                         "flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}
                     ,{"surface":"L","taperShapeMsg":"正常外径最高值 235.62888012066344 >= 80 检测角度0 \n","looseCoilMsg":"",
                         "flatRollMsg":"正常","defectMsg":"",
                         "crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":5},
                         "nextCode":"7","secondaryCoilId":23201,"Id":352,"nextName":"外委横切(配送)","taperShapeGrad":3,
                         "looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}
                 ],
                 "childrenCoil":[{"SecondaryCoilId":23201,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,
                             "minute":39,"second":8},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42975,"DefectCountL":0,
                         "Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,
                 "SecondaryCoilId":23202,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":41},
                 "CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23202,"DefectCountL":0,"Status_L":0,"Grade":0,
                 "AlarmInfo":{"L":{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"",
                         "crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":37},
                         "nextCode":"7","secondaryCoilId":23202,"Id":353,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 34.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":39},"nextCode":"7","secondaryCoilId":23202,"Id":354,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,"ActWidth":1070,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":37,"second":43},"CoilNo":"4V08329800","CoilInside":762,"CoilDia":1826,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":37},"nextCode":"7","secondaryCoilId":23202,"Id":353,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 34.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"
    year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":39},"nextCode":"7","secondaryCoilId":23202,"Id":354,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}],"childrenCoil":[{"SecondaryCoilId":23202,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":39,"second":41},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42976,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23203,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":16},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23203,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"L":{"surface":"L","taperShapeMsg":"正常外径最高值 243.59184232416192 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":11},"nextCode":"7","secondaryCoilId":23203,"Id":355,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null},"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 35.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":13},"nextCode":"7","secondaryCoilId":23203,"Id":356,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,"ActWidth":1072,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":39,"second":39},"CoilNo":"4V08329900","CoilInside":762,"CoilDia":1818,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"L","taperShapeMsg":"正常外径最高值 243.59184232416192 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":11},"nextCode":"7","secondaryCoilId":23203,"Id":355,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null},{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 35.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":13},"nextCode":"7","secondaryCoilId":23203,"Id":356,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}],"childrenCoil":[{"SecondaryCoilId":23203,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":16},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42977,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23204,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":47},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23204,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"L":{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 47.0 超过限制值 25松卷检测最宽 35.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":43},"nextCode":"7","secondaryCoilId":23204,"Id":357,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null},"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":46},"nextCode":"7","secondaryCoilId":23204,"Id":358,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}},"Width":1059,"Weight":55,"ActWidth":1069,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":42
    ,"second":1},"CoilNo":"4V08330000","CoilInside":762,"CoilDia":1819,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"松卷检测最宽 47.0 超过限制值 25松卷检测最宽 35.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":43},"nextCode":"7","secondaryCoilId":23204,"Id":357,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null},{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":46},"nextCode":"7","secondaryCoilId":23204,"Id":358,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}],"childrenCoil":[{"SecondaryCoilId":23204,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":40,"second":47},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42978,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23205,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":20},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23205,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":14},"nextCode":"7","secondaryCoilId":23205,"Id":359,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"L":{"surface":"L","taperShapeMsg":"正常外径最高值 242.74224206360645 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":17},"nextCode":"7","secondaryCoilId":23205,"Id":360,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,"ActWidth":1073,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":44,"second":2},"CoilNo":"4V08330100","CoilInside":762,"CoilDia":1818,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":14},"nextCode":"7","secondaryCoilId":23205,"Id":359,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"L","taperShapeMsg":"正常外径最高值 242.74224206360645 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":17},"nextCode":"7","secondaryCoilId":23205,"Id":360,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}],"childrenCoil":[{"SecondaryCoilId":23205,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":20},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42979,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23206,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":6},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23206,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"L":{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":59},"nextCode":"7","secondaryCoilId":23206,"Id":361,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null
    },"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":59},"nextCode":"7","secondaryCoilId":23206,"Id":362,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}},"Width":1059,"Weight":55,"ActWidth":1071,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":46,"second":12},"CoilNo":"4V08330200","CoilInside":762,"CoilDia":1825,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":59},"nextCode":"7","secondaryCoilId":23206,"Id":361,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":41,"second":59},"nextCode":"7","secondaryCoilId":23206,"Id":362,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}],"childrenCoil":[{"SecondaryCoilId":23206,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":6},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42980,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23207,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":51},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23207,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":43},"nextCode":"7","secondaryCoilId":23207,"Id":363,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"L":{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":47},"nextCode":"7","secondaryCoilId":23207,"Id":364,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}},"Width":1059,"Weight":55,"ActWidth":1071,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":48,"second":16},"CoilNo":"4V08330300","CoilInside":762,"CoilDia":1826,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":43},"nextCode":"7","secondaryCoilId":23207,"Id":363,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":47},"nextCode":"7","secondaryCoilId":23207,"Id":364,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}],"childrenCoil":[{"SecondaryCoilId":23207,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":42,"second":51},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42981,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23208,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":28},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23208,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"L":{"surfac
    e":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":23},"nextCode":"7","secondaryCoilId":23208,"Id":365,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"S":{"surface":"S","taperShapeMsg":"正常外径最高值 223.86738554537646 >= 80 检测角度180 \n","looseCoilMsg":"松卷检测最宽 31.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":24},"nextCode":"7","secondaryCoilId":23208,"Id":366,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,"ActWidth":1071,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":50,"second":35},"CoilNo":"4V08330400","CoilInside":762,"CoilDia":1817,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":23},"nextCode":"7","secondaryCoilId":23208,"Id":365,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"S","taperShapeMsg":"正常外径最高值 223.86738554537646 >= 80 检测角度180 \n","looseCoilMsg":"松卷检测最宽 31.0 超过限制值 25","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":24},"nextCode":"7","secondaryCoilId":23208,"Id":366,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":3,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}],"childrenCoil":[{"SecondaryCoilId":23208,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":43,"second":28},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42982,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23209,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":5},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23209,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":1},"nextCode":"7","secondaryCoilId":23209,"Id":367,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"L":{"surface":"L","taperShapeMsg":"正常外径最高值 237.14621342598218 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":3},"nextCode":"7","secondaryCoilId":23209,"Id":368,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":3,"data":null}},"Width":1059,"Weight":55,"ActWidth":1070,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":52,"second":27},"CoilNo":"4V08330500","CoilInside":762,"CoilDia":1827,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":1},"nextCode":"7","secondaryCoilId":23209,"Id":367,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"L","taperShapeMsg":"正常外径最高值 237.14621342598218 >= 80 检测角度0 \n","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":3},"nextCode":"7","secondaryCoilId":23209,"Id":368,"nextName":"外委横切(配送)","taperShapeGrad":3,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"gr
    ad":3,"data":null}],"childrenCoil":[{"SecondaryCoilId":23209,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":5},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42983,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"},{"hasCoil":true,"hasAlarmInfo":true,"SecondaryCoilId":23210,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":54},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":23210,"DefectCountL":0,"Status_L":0,"Grade":0,"AlarmInfo":{"S":{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":46},"nextCode":"7","secondaryCoilId":23210,"Id":369,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},"L":{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":47},"nextCode":"7","secondaryCoilId":23210,"Id":370,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}},"Width":1059,"Weight":55,"ActWidth":1071,"CoilType":"LGQX-1","CreateTime":{"year":2024,"month":10,"weekday":4,"day":18,"hour":9,"minute":54,"second":46},"CoilNo":"4V08330600","CoilInside":762,"CoilDia":1825,"Thickness":2.3,"childrenAlarmInfo":[{"surface":"S","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":46},"nextCode":"7","secondaryCoilId":23210,"Id":369,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null},{"surface":"L","taperShapeMsg":"正常","looseCoilMsg":"","flatRollMsg":"正常","defectMsg":"","crateTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":47},"nextCode":"7","secondaryCoilId":23210,"Id":370,"nextName":"外委横切(配送)","taperShapeGrad":1,"looseCoilGrad":1,"flatRollGrad":1,"defectGrad":1,"grad":1,"data":null}],"childrenCoil":[{"SecondaryCoilId":23210,"DetectionTime":{"year":2024,"month":11,"weekday":2,"day":13,"hour":9,"minute":44,"second":54},"CheckStatus":0,"Status_S":0,"Msg":"","DefectCountS":0,"Id":42984,"DefectCountL":0,"Status_L":0,"Grade":0}],"NextCode":"7","NextInfo":"外委横切(配送)"}]]}

    function updateData(upData){
        while(coilListModel.count > maxCoilListModelLen){
            coilListModel.remove(coilListModel.count-1,1)
        }
        upData["coilList"].forEach(function(coil){
            if(coil.SecondaryCoilId > lastCoilId){
                coilListModel.insert(0,coil)
                lastCoilId = coil.SecondaryCoilId
            }
        })
        if (keepLatest){
        core.setCoilIndex(0)
        }
    }

    // search

    function setSearch(data){

    currentCoilListIndex=1
        historyCoilListModel.clear()
        for(var i=0;i<data.length;i++){
            historyCoilListModel.insert(0,data[i])
        }
        core.setCoilIndex(-1)
        core.setCoilIndex(0)
    }

    function searchByCoilNo(coilNo){
        api.searchByCoilNo(coilNo,
                           (result)=>{
                                setSearch(JSON.parse(result))
                           },
                           (error)=>{}
                           )
    }
    function searchByCoilId(coilId){
        api.searchByCoilId(coilId,
                           (result)=>{
                               setSearch(JSON.parse(result))
                           },
                           (error)=>{}

                           )
    }

    function searchByCoilDateTime(start,end){
        api.searchByTime(start,end,
                           (result)=>{
                                     console.log(result)
                                     setSearch(JSON.parse(result))
                                 },
                           (error)=>{}
        )
    }


}
