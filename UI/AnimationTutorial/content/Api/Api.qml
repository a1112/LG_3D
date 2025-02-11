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

    function getFileSource(_key_,_coilId_,_viewKey_,preView=false,mask=true){
        if(preView){
                return apiConfig.url(apiConfig.serverUrlImage,"image/preview/"+_key_,_coilId_,_viewKey_)
        }
        return apiConfig.url(apiConfig.serverUrlImage,"image/source/"+_key_,_coilId_,_viewKey_)+`?mask=${mask}`
    }



    //全局下载器
    function downloadFile(url,save_path,success,failure){
        return cpp.fileDownloader.downloadFile(url, save_path)
    }

    function getWsReDetectionUrl(){
        return apiConfig.url(apiConfig.wsServerUrl,"ws","reDetection")
    }


    function clipMaxImage(coilId,key,success,failure){
        let url =  apiConfig.url(apiConfig.serverUrlData,"clipMaxImage",coilId,key)
            return ajax.get(url,success,failure)

    }
}
