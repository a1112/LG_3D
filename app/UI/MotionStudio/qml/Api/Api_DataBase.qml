
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
    let url =  apiConfig.url(apiConfig.serverUrlData,"coilData","heightData",_key_,coilId_)+`?x1=${x1}&y1=${y1}&x2=${x2}&y2=${y2}`
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

    function geRenderDrawerSource(key,coil_id,scale,minValue,maxValue,mask=false){
        //  http://127.0.0.1:6013/coilData/L/1924?mask=true&minValue=0&maxValue=255
        let url_= apiConfig.url(apiConfig.serverUrlData,"coilData","Render",key,coil_id)+`?scale=${scale}&mask=${mask}&minValue=${minValue}&maxValue=${maxValue}`

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
        console.log(apiConfig.url(apiConfig.serverUrlDaaBase,"flush",coilId))
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"flush",coilId),success,failure)
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
}

