import QtQuick

Item {

    id: api_base

    required property var connectionState
    required property var errorModel

    property int delay: -1
    readonly property bool connected: delay >= 0
    property color statusSuccessColor: "#4ADE80"
    property color statusWarningColor: "#FBBF24"
    property color statusErrorColor: "#FB7185"
    readonly property color connectColor: !connected
                                          ? statusErrorColor
                                          : delay < 200
                                            ? statusSuccessColor
                                            : statusWarningColor
    readonly property string connectionText: !connected
                                              ? qsTr("离线")
                                              : delay < 200
                                                ? qsTr("正常")
                                                : qsTr("延迟")
    property bool delayRequestRunning: false
    property int consecutiveDelayFailures: 0

    // WebSocket {}

    property Ajax ajax: Ajax {
        requestLogger: api_base
    }
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
            failure(delay)
        }
        )

    }

    function getDelay__(){
        if (delayRequestRunning) {
            return null
        }
        delayRequestRunning = true
        let startTime = new Date().getTime()
        return ajax.get(apiConfig.url(apiConfig.serverUrlDaaBase,"delay"),function(data){
            delayRequestRunning = false
            consecutiveDelayFailures = 0
            connectionState.connectServer = true
            delay = new Date().getTime()-startTime
            // delayTimer.restart()
            if (errorModel && errorModel.coreGlobalError) {
                errorModel.coreGlobalError.setError(1001, false)
            }
        }
        ,function(err){
            delayRequestRunning = false
            consecutiveDelayFailures += 1
            connectionState.connectServer = false
            delay= -1
            if (errorModel && errorModel.coreGlobalError) {
                errorModel.coreGlobalError.setError(1001, true)
            }
            // delayTimer.restart()
        }
        )

    }

    Timer{
        interval: 8000
        repeat:true
        running: true
        id: delayTimer
        triggeredOnStart:true
        onTriggered: {
            api_base.getDelay__()
        }
    }

    function openApi(port){
            return Qt.openUrlExternally(apiConfig.url(apiConfig.protocol+apiConfig.hostname+":"+port,"docs"))
    }
}
