import QtQuick
// import QtWebSockets 1.8
Api_DataBase {

        //  6012
    readonly property int urlListModel_maxCouint:200
    property ListModel urlListModel:ListModel{

    }

    function appendUrl(url,type){
        if (urlListModel.count>urlListModel_maxCouint){
        urlListModel.remove(urlListModel_maxCouint-1,urlListModel.count-urlListModel_maxCouint)
        }
        urlListModel.insert(0,
                    {
                    url:url,
                    type:type,
                    timeString:tool.getNowTimeString()
                    }
                    )
    }

    function buildImageUrl(...args){
        let url = apiConfig.serverUrlImage
        for (let argIndex in args){
            url += "/" + args[argIndex]
        }
        return url
    }

    function getFileSource(_key_,_coilId_,_viewKey_,preView=false,mask=true){
        _viewKey_ = _viewKey_ === "2D" ? "AREA" : _viewKey_
        if(preView){
                return buildImageUrl("image/preview/"+_key_,_coilId_,_viewKey_)
        }
        if (_viewKey_ === "AREA"){
            return buildImageUrl("image/area/"+_key_,_coilId_)
        }
        if (_viewKey_ === "AREA_MASK"){
            return buildImageUrl("image/area/"+_key_,_coilId_,_viewKey_)
        }
        return buildImageUrl("image", "source",_key_,_coilId_,_viewKey_)+`?mask=${mask}`
    }

    function setImageServerBackend(useRust){
        coreSetting.useRustImageServer = useRust
    }

    function getImageServerBackend(){
        return coreSetting.useRustImageServer ? "rust" : "python"
    }

    function getRustImageServerUrl(){
        return apiConfig.rustImageServerUrl
    }

    function recacheAreaTiles(surfaceKey, coilId, viewKey, success, failure){
        viewKey = viewKey === "2D" ? "AREA" : viewKey
        if (viewKey !== "AREA" && viewKey !== "AREA_MASK") {
            viewKey = "AREA"
        }
        let url = apiConfig.serverUrl
                + "/image/area/cache/rebuild/"
                + encodeURIComponent(surfaceKey)
                + "/" + encodeURIComponent(coilId)
                + "/" + encodeURIComponent(viewKey)
        return ajax.post(url, {}, success, failure)
    }

    function clearRustImageCache(success, failure){
        return ajax.post(getRustImageServerUrl() + "/cache/clear", {}, success, failure)
    }

    //全局下载器
    function downloadFile(url,save_path,success,failure){
        return fileDownloader.downloadFile(url, save_path)
    }

    function getWsReDetectionUrl(){
        return apiConfig.url(apiConfig.wsServerUrl,"ws","reDetection")
    }

    function getAlgModels(success,failure){
        // 使用 serverUrl (port 5010) 和正确的路径 /alg_2d/models
        return ajax.get(apiConfig.serverUrl + "/alg_2d/models", success, failure)
    }

    function startAlgTest(payload,success,failure){
        // 使用 serverUrl (port 5010) 和正确的路径 /alg_2d/test/start
        return ajax.post(apiConfig.serverUrl + "/alg_2d/test/start", payload, success, failure)
    }

    function stopAlgTest(payload,success,failure){
        // 使用 serverUrl (port 5010) 和正确的路径 /alg_2d/test/stop
        return ajax.post(apiConfig.serverUrl + "/alg_2d/test/stop", payload, success, failure)
    }

    function getAlgTestWsUrl(){
        // 修复：使用正确的 ws 路径 ws/alg_2d/test/progress
        return apiConfig.url(apiConfig.wsServerUrl, "ws", "alg_2d", "test", "progress")
    }


    function clipMaxImage(coilId,key,success,failure){
        let url =  apiConfig.url(apiConfig.serverUrlData,"clipMaxImage",coilId,key)
            return ajax.get(url,success,failure)

    }

    function setAreaClipConfig(surfaceKey, payload, success, failure){
        let url = apiConfig.serverUrlAlg2D + "/clip_config"
        let body = Object.assign({surface_key: surfaceKey}, payload)
        return ajax.post(url, body, success, failure)
    }

    function rejoinArea(coilId, surfaceKey, success, failure){
        let url = apiConfig.serverUrlAlg2D + "/area/rejoin"
        let body = {coil_id: coilId}
        if (surfaceKey !== undefined && surfaceKey !== null && surfaceKey !== "") {
            body.surface_key = surfaceKey
        }
        return ajax.post(url, body, success, failure)
    }

    function get_defect_url(suface, coil_id, defect_name, x, y, w, h){
        let url = apiConfig.url(apiConfig.serverUrlData,"classifier_image",coil_id,suface,defect_name,x,y,w,h)
        return url
        // E:\Save_L\53501\classifier\背景\53501_1148_5058_1177_5080.png
    }

    function has_data(coil_id, success, failure, fast=false){
        let url = fast ? apiConfig.url(apiConfig.serverUrlData, "data_has", coil_id, {fast: true})
                       : apiConfig.url(apiConfig.serverUrlData, "data_has", coil_id)
        return ajax.get(url, success, failure)
    }

}
