import QtQuick

Item {

    id:api_base

    property int delay: 0
    property color connectColor: delay>0?delay<200?"green":"yellow" :"red"

    // WebSocket {}


    function showConnectDialog(){
    }

    property Ajax ajax: Ajax{}
    function url(serverUrl, ...args){
        let reUrl=serverUrl
        for(let argIndex in args){
            reUrl+="/"+args[argIndex]
        }
        return reUrl
    }

    property ApiConfig apiConfig: ApiConfig{}

    function getLastUrlByKey(key){
        return apiConfig.getLastUrlByKey(key)
    }

    function loadJsonData(source,success,failure){
        return ajax.get(source,success,failure)
    }

    // 6013


    function __getDelay__(port,success,failure){
        var startTime = new Date().getTime()
        ajax.get(apiConfig.url(apiConfig.protocol+apiConfig.hostname+":"+port,"delay"),function(data){
            let delay = new Date().getTime()-startTime
            success(delay)
        },function(err){
            let delay = new Date().getTime()-startTime
            failure(delay-startTime)
        }
        )

    }

    function getDelay__(){
        let startTime = new Date().getTime()
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"delay"),function(data){
            delay = new Date().getTime()-startTime
            delayTimer.restart()
            coreModel.coreGlobalError.setError(1001,false)
        }

        ,function(err){
            delay= -1
            coreModel.coreGlobalError.setError(1001,true)
            delayTimer.restart()
        }
        )

    }

    Timer{
        interval: 5000
        running: true
        id: delayTimer
        onTriggered: {
            api_base.getDelay__()
        }
    }

    function openApi(port){
            return Qt.openUrlExternally(apiConfig.url(apiConfig.protocol+apiConfig.hostname+":"+port,"docs"))
    }
}
