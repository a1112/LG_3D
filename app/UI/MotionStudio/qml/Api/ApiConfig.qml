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


    readonly property string protocol: "http://"
    readonly property string ws_protocol:"ws://"

    property PortTool portTool :PortTool{
    }

    readonly property string serverUrl: protocol+hostname+":"+port
    readonly property string wsServerUrl: ws_protocol+hostname+":"+port

    readonly property string serverUrlDaaBase: protocol+hostname+":"+databasPort
    readonly property string wsServerUrlDaaBase: ws_protocol+hostname+":"+databasPort

    readonly property string serverUrlImage: protocol+hostname+":"+imageServerPort
    readonly property string serverUrlData: protocol+hostname+":"+dataPort


    readonly property string hostname:coreSetting.server_ip
    readonly property int port: coreSetting.server_port

    readonly property int databasPort:  coreSetting.databasPort
    readonly property int imageServerPort:  coreSetting.imageServerPort
    readonly property int dataPort:  coreSetting.dataPort
    readonly property int plcPort:  coreSetting.plcPort

    property bool auto_server_port:true
    property int _pre_port_value_:0

    function getBaseUrl(){
        return protocol+hostname+":"+server_port_base
    }
    function url(reUrl,...args){
        let key =""

        if (auto_server_port){
            // 自动端口映射
            if (reUrl.indexOf("ws")>=0){
                reUrl = portTool.getAutoWsUrl(args[0])
            }
            else{
                reUrl = portTool.getAutoUrl(args[0])
            }
        }

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
