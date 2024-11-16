import QtQuick 2.15

Item {
    id:root
    property bool hasError: false
    property int errorCode:-1
    property string errorStr:"服务器连接失败！"
    property bool hasGlobalError: false
    property var errorLevelDict:{
    return {}
    }

    Timer{
        interval: 500
        running:true
        repeat: true
        onTriggered:root.flushLevel()
    }

    function flushLevel(){
        if(errorState)
        {
            let newLevel={}
                            hasGlobalError=false
            for(let key in errorState)
            {
                newLevel[key] = 0

                for(let key2 in errorState[key])
                {
                    if(errorState[key][key2]>newLevel[key]){
                        newLevel[key] = errorState[key][key2]
                        hasGlobalError=true
                    }
                }
            }
              errorLevelDict = newLevel
        }


    }

    property var errorState: {
        return {}
    }
    Component.onCompleted:{
        var st={}
        for(let key in coreModel.alarmGlobVis)
        {
            st[key] = {}
        }

        for(let key in coreModel.alarmVis)
        {
            st[key] = {}
        }
        errorState = st
    }

    onErrorStateChanged:{
        flushLevel()
    }

    property var errorDict: {
        return {}
    }

    function setError(code,hasError){
        var str=""
        if (code == 1001) {
            str="数据服务器连接失败！"
        }
        if (code == 2001){
            str="检测数据获取失败！"
        }
        _setGlobalError(code,str,hasError)
    }

    function _setGlobalError(code,str,hasError_){
        errorDict[code] = {}
        errorDict[code].code = code
        errorDict[code].str = str
        errorDict[code].hasError = hasError_
        if (errorCode == code || errorCode<0) {
            errorCode = code
            errorStr = str
            hasError = hasError_
        }
    }
}
