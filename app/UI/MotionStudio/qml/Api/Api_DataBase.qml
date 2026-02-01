
import QtWebSockets
Api_Base {
    id:api_database


    property string oldHeightDatUrl:""
    property WebSocket heightPointSocket: WebSocket{
        id: heightPointWs
        // Direct URL to avoid auto remapping.
        url: apiConfig.ws_protocol+apiConfig.hostname+":"+apiConfig.dataPort+"/ws/coilData/heightPoint"
        active: true
        onStatusChanged: {
            if (status === WebSocket.Open) {
                while (_heightPointQueue.length > 0) {
                    let payload = _heightPointQueue.shift()
                    sendTextMessage(payload)
                }
            } else if (status === WebSocket.Error || status === WebSocket.Closed) {
                console.log("heightPoint ws closed/error", status, errorString)
                // flush pending with failure
                for (let key in _heightPointRequests) {
                    let cb = _heightPointRequests[key]
                    if (cb && cb.failure) {
                        cb.failure("ws error")
                    }
                }
                _heightPointRequests = {}
                _heightPointQueue = []
            }
        }
        onTextMessageReceived: function(message){
            try{
                let data = JSON.parse(message)
                let reqId = data.id
                let cb = _heightPointRequests[reqId]
                delete _heightPointRequests[reqId]
                if (!cb) return
                if (data.error !== undefined){
                    cb.failure && cb.failure(data.error)
                }else if (data.value !== undefined){
                    if (isFinite(data.value)){
                        cb.success && cb.success(data.value)
                    }else{
                        cb.failure && cb.failure("invalid value")
                    }
                }else{
                    cb.failure && cb.failure("ws no value")
                }
            }catch(e){
                console.log("ws parse error", e)
            }
        }
    }

    property int _heightPointReqId: 0
    property var _heightPointRequests: ({})
    property var _heightPointQueue: []

    function _sendHeightPointWs(payload, success, failure){
        _heightPointReqId += 1
        payload.id = _heightPointReqId
        _heightPointRequests[payload.id] = {
            success: success,
            failure: failure
        }
        let text = JSON.stringify(payload)
        if (heightPointSocket.status === WebSocket.Open){
            heightPointSocket.sendTextMessage(text)
        }else{
            _heightPointQueue.push(text)
            if (!heightPointSocket.active){
                heightPointSocket.active = true
            }
        }
    }

    function getHeightData(_key_,coilId_,x1,y1,x2,y2,success,failure){
        x1 = Number(x1); y1 = Number(y1); x2 = Number(x2); y2 = Number(y2)
        if (!isFinite(x1) || !isFinite(y1) || !isFinite(x2) || !isFinite(y2)){
            console.log("getHeightData: invalid coords", x1, y1, x2, y2)
            failure && failure("invalid coords")
            return null
        }
        let url = apiConfig.url(apiConfig.serverUrlData,"coilData","heightData",_key_,coilId_)+`?x1=${x1}&y1=${y1}&x2=${x2}&y2=${y2}`
        oldHeightDatUrl=url
        return ajax.get(url,success,failure)
    }


    function get_zValueData(_key_,coilId_,x1,y1,success,failure){
        // Prefer WebSocket for low-latency single-point queries; fallback to HTTP.
        _sendHeightPointWs({
                              "surface_key": _key_,
                              "coil_id": coilId_,
                              "x": x1,
                              "y": y1
                          }, success, function(err){
                              let url =  apiConfig.url(apiConfig.serverUrlData,"coilData","heightPoint",_key_,coilId_)+`?x=${x1}&y=${y1}`
                              let failureCb = failure ? failure : function(e){console.log("heightPoint http error", e, err)}
                              return ajax.get(url,function(val){
                                  if (isFinite(val)){
                                      success && success(val)
                                  }else{
                                      failureCb("invalid value")
                                  }
                              },failureCb)
                          })
    }

    function geRenderDrawerSource(key,coil_id,scale,minValue,maxValue,mask=false,grayscale=false){
        //  http://127.0.0.1:6013/coilData/L/1924?scale=xxx&mask=xxx&minValue=xxx&maxValue=xxx&grayscale=xxx
        let url_= apiConfig.url(apiConfig.serverUrlData,"coilData","Render",key,coil_id)
        url_ += `?scale=${scale}&mask=${mask}&minValue=${minValue}&maxValue=${maxValue}&grayscale=${grayscale}`
        return url_
    }

    function geErrorDrawerSource(key,coil_id,scale,minValue,maxValue,mask=false){
        let url_= apiConfig.url(apiConfig.serverUrlData,"coilData","Error",key,coil_id)+`?scale=${scale}&mask=${mask}&minValue=${minValue}&maxValue=${maxValue}`

        return url_
    }

    //  6011
    function getCoilList(num,success,failure){
        let url_= apiConfig.url(apiConfig.serverUrlDaaBase,"coilList",num)
        return ajax.get(url_,success,failure)
    }

    function getInfo(success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"info"),success,failure)
    }

    function getRuntimeInfo(success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"runtime_info"), success, failure)
    }

    function getDatabaseInfo(success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"database_info"), success, failure)
    }

    function getServerVersion(success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"version"), success, failure)
    }

    function getDataFlush(coilId,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"flush",coilId),success,failure)
    }

    // 获取卷材详情（完整数据：缺陷列表、塔形点等）
    function getCoilDetail(coilId,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"detail",coilId),success,failure)
    }

    // search
    function getCoilState(coilId_,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","CoilState",coilId_),success,failure)
    }
    function getPlcData(coilId_,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","PlcData",coilId_),success,failure)
    }

    function searchByCoilNo(coilNo,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","coilNo",coilNo),success,failure)
    }
    function getSearchByCoilIdUrl(coilId){
        return apiConfig.url(apiConfig.serverUrlDaaBase,"search","coilId",coilId)
    }


    function searchByCoilId(coilId,success,failure){
        return ajax.get(getSearchByCoilIdUrl(coilId),success,failure)
    }
    function searchByTime(startTime,endTime,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","DateTime",startTime,endTime),success,failure)
    }

    function  getDefects(coilId,key,success,failure){
        // 获取缺陷数据
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","defects",coilId,key),success,failure)
    }

    function  getDefectsByCoilId(fromCoilId,toCoilId,success,failure){
        // 获取缺陷数据
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","getDefectAll",fromCoilId,toCoilId),success,failure)
    }
    function getDefectAll(startCoilId,endCoilId, success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","getDefectAll", startCoilId, endCoilId), success, failure)
    }
    function getDefectDict(success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"defectDict"),success,failure)
    }
    function setDefecctClassConfig(data,success,failure){
        // 设置 缺陷数据
        return ajax.post(apiConfig.url(apiConfig.serverUrlDaaBase,"setDefectDict"),data,success,failure)
    }


    function getCoilInfo(coilId_,key_,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"coilInfo",coilId_,key_),success,failure)
    }
    function getHardware(success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"hardware"),success,failure)
    }

    function getCameraAlarm(success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"cameraAlarm"),success,failure)
    }

    function getCameraDataUrl(coilId_,camera_key,success,failure){
        return apiConfig.url(apiConfig.serverUrlDaaBase,"cameraData",coilId_,camera_key)
    }

    function getCoilAlarm(coilId_,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"coilAlarm",coilId_),success,failure)
    }

    function setBackupImageTask(from_coilId,to_coilId,folder,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"backupImageTask",from_coilId,to_coilId,folder),success,failure)
    }

    function getWsBackupImageUrl(){
        return apiConfig.url(apiConfig.wsServerUrlDaaBase,"ws","backupImageTask")
    }



    function exportDataSimple(success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"exportDataSimple"),success,failure)
    }

    function getExportByDateTimeUrl(startTime,endTime,exportType){
        return apiConfig.url(apiConfig.serverUrlDaaBase,"exportXlsxByDateTime",startTime,endTime,apiConfig.getGetArgs({
                                                                                                                      export_type:exportType
                                                                                                                      }))
    }

    function getPostExportUrl(){
        // 通过 post 全球完成下载，导出
        return apiConfig.url(apiConfig.serverUrlDaaBase,"export_xlsx")
    }

    function getExport1hUrl(){
        // 快速导出最近1小时数据（使用主服务器端口5010）
        return "http://"+apiConfig.hostname+":"+apiConfig.port+"/export_1h"
    }

    function getExport24hUrl(){
        // 快速导出最近24小时数据（使用主服务器端口5010）
        return "http://"+apiConfig.hostname+":"+apiConfig.port+"/export_24h"
    }

    function getExportTodayUrl(){
        // 快速导出今天数据（使用主服务器端口5010）
        return "http://"+apiConfig.hostname+":"+apiConfig.port+"/export_today"
    }


    function getPointDatas(coilId,key,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"get_point_data",coilId,key),success,failure)
    }

    function getLineDatas(coilId,key,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"get_line_data",coilId,key),success,failure)
    }

    function save_to_sql(sql_file,success,failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"save_to_sql",sql_file),success,failure)
    }

    function defect_url(coilId,key,viewKey,x,y,w,h){
        return apiConfig.url(apiConfig.serverUrlDaaBase,"defect_image",key,coilId,viewKey,x,y,w,h)
    }

    // function defectClasses(success,failure){
    //      return ajax.get(apiConfig.url("defectClasses"),success,failure)
    // }

    function getCoilListValueChangeKeys(success,failure){
        // 获取变化曲线数值键
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"coil_list_value_change_keys"),success,failure)
    }

    function getCoilStatus(coil_id,success,failure){
        return  ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"check","get_coil_status",coil_id),success,failure)
    }

    function setCoilStatus(coil_id, status, msg,success,failure)
    {
         return  ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"check","set_coil_status",coil_id,status, msg),success,failure)
    }


    function set_check_defect_name(defect_name){
        // 设置新的
    }


    function getPlcCurveData(field, startId, endId, limit, success, failure){
        let args = []
        if (startId !== undefined && startId !== null && startId !== "" && !isNaN(startId)){
            args.push("start_id="+startId)
        }
        if (endId !== undefined && endId !== null && endId !== "" && !isNaN(endId)){
            args.push("end_id="+endId)
        }
        if (limit !== undefined && limit !== null && limit !== "" && !isNaN(limit)){
            args.push("limit="+limit)
        }
        let url = apiConfig.url(apiConfig.serverUrlDaaBase,"plc_curve",field)
        if (args.length > 0){
            url = url + "?" + args.join("&")
        }
        return ajax.get(url,success,failure)
    }



    function getPlcCurveAllData(startId, endId, limit, success, failure){
        let args = []
        if (startId !== undefined && startId !== null && startId !== "" && !isNaN(startId)){
            args.push("start_id="+startId)
        }
        if (endId !== undefined && endId !== null && endId !== "" && !isNaN(endId)){
            args.push("end_id="+endId)
        }
        if (limit !== undefined && limit !== null && limit !== "" && !isNaN(limit)){
            args.push("limit="+limit)
        }
        let url = apiConfig.url(apiConfig.serverUrlDaaBase,"plc_curve_all")
        if (args.length > 0){
            url = url + "?" + args.join("&")
        }
        return ajax.get(url,success,failure)
    }


    // ==================== 手动标注缺陷 API ====================

    // 获取所有缺陷（包括自动检测和手动标注）
    function getDefectsAll(coilId, key, success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"search","defects_all",coilId,key),success,failure)
    }

    // 获取手动标注的缺陷列表
    function getManualDefects(coilId, key, success, failure){
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"manual_defects",coilId,key),success,failure)
    }

    // 添加手动标注的缺陷
    function addManualDefect(data, success, failure){
        return ajax.post(apiConfig.url(apiConfig.serverUrlDaaBase,"manual_defect","add"),data,success,failure)
    }

    // 更新手动标注的缺陷
    function updateManualDefect(defectId, data, success, failure){
        return ajax.put(apiConfig.url(apiConfig.serverUrlDaaBase,"manual_defect","update",defectId),data,success,failure)
    }

    // 删除手动标注的缺陷
    function deleteManualDefect(defectId, success, failure){
        return ajax.delete_(apiConfig.url(apiConfig.serverUrlDaaBase,"manual_defect","delete",defectId),success,failure)
    }

    // 导出标记缺陷图像
    function exportManualDefects(data, success, failure){
        return ajax.post(apiConfig.url(apiConfig.serverUrlDaaBase,"export_defects"),data,success,failure)
    }

    // ==================== 一键导出功能 ====================

    // 导出最近1小时的数据
    function export1h(exportType, success, failure){
        let args = exportType ? "?export_type=" + exportType : ""
        let url = apiConfig.url(apiConfig.serverUrlDaaBase,"export_1h") + args
        // 直接下载，通过window.open或iframe
        return url
    }

    // 导出最近24小时的数据
    function export24h(exportType, success, failure){
        let args = exportType ? "?export_type=" + exportType : ""
        let url = apiConfig.url(apiConfig.serverUrlDaaBase,"export_24h") + args
        return url
    }

    // 执行浏览器下载
    function downloadExport(url){
        let iframe = document.createElement("iframe")
        iframe.style.display = "none"
        iframe.src = url
        document.body.appendChild(iframe)
        setTimeout(function(){
            document.body.removeChild(iframe)
        }, 1000)
    }

}