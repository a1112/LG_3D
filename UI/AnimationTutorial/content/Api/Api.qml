import QtQuick 2.15
// import QtWebSockets 1.8
Api_DataBase {

        //  6012

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



}
