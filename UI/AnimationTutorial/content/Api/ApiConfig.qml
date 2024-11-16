import QtQuick
import Qt.labs.settings
Item {
    id:root

    property var lastUrls:{return {}}

    function getLastUrlByKey(key){
        return lastUrls[key]
    }

    ListModel{

    }

    readonly property string serverUrl: protocol+hostname+":"+port
    readonly property string wsServerUrl: "ws://"+hostname+":"+port

    readonly property string serverUrlDaaBase: protocol+hostname+":"+databasPort
    readonly property string wsServerUrlDaaBase: "ws://"+hostname+":"+databasPort

    readonly property string serverUrlImage: protocol+hostname+":"+imageServerPort
    readonly property string serverUrlData: protocol+hostname+":"+dataPort

    readonly property string protocol: "http://"
    readonly property string hostname:coreSetting.server_ip
    readonly property int port: coreSetting.server_port

    readonly property int databasPort:  coreSetting.databasPort
    readonly property int imageServerPort:  coreSetting.imageServerPort
    readonly property int dataPort:  coreSetting.dataPort
    readonly property int plcPort:  coreSetting.plcPort
    function url(reUrl,...args){
        let key =""
        for(let argIndex in args){
            key=args[0]
            if (typeof(args[argIndex])=='object')
            {
                reUrl+=getGetArgs(args[argIndex])
            }
            else{
            reUrl+="/"+args[argIndex]
                }
        }
        lastUrls[key]=reUrl
        return reUrl
    }
    function getPostArgs(dictData){
        let res=""
        for(let key in dictData){
            if(res){
                res+="&"
            }
            res+=key+"="+dictData[key]
        }
        return res
    }
    function getGetArgs(dictData){
        let res=""
        for(let key in dictData){
            if(res){
                res+="&"
            }
            else{
            res+="?"
            }
            res+=key+"="+dictData[key]
        }
        return res
    }
}
