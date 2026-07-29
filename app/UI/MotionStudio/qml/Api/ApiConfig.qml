import QtQuick

Item {
    id: root

    property var lastUrls: ({})

    readonly property string protocol: "http://"
    readonly property string ws_protocol: "ws://"
    readonly property string hostname: coreSetting.server_ip

    readonly property int pythonApiPort: 5010
    readonly property int rustApiPort: 5011
    readonly property int pythonImageServerPort: 6012
    readonly property int rustImageServerPort: 6013
    readonly property int activeApiPort: coreSetting.useRustTestServer ? rustApiPort : pythonApiPort
    readonly property int activeImageServerPort: coreSetting.useRustImageServer ? rustImageServerPort : pythonImageServerPort

    readonly property string serverUrl: protocol + hostname + ":" + activeApiPort
    readonly property string wsServerUrl: ws_protocol + hostname + ":" + activeApiPort
    readonly property string serverUrlDaaBase: serverUrl
    readonly property string wsServerUrlDaaBase: wsServerUrl
    readonly property string serverUrlData: serverUrl
    readonly property string serverUrlImage: protocol + hostname + ":" + activeImageServerPort
    readonly property string rustImageServerUrl: protocol + hostname + ":" + rustImageServerPort
    readonly property string serverUrlAlg2D: coreSetting.useRustTestServer
                                              ? serverUrl
                                              : protocol + hostname + ":6020"

    // These values are retained for network diagnostics; they are not user settings.
    readonly property int port: activeApiPort
    readonly property int databasPort: activeApiPort
    readonly property int dataPort: activeApiPort
    readonly property int plcPort: activeApiPort
    readonly property int alg2dPort: coreSetting.useRustTestServer ? rustApiPort : 6020
    readonly property bool usingRustImageServer: coreSetting.useRustImageServer

    function getLastUrlByKey(key) {
        return lastUrls[key]
    }

    function getBaseUrl() {
        return serverUrl
    }

    function url(reUrl, ...args) {
        let key = ""
        for (let argIndex in args) {
            key = args[0]
            if (typeof(args[argIndex]) === "object") {
                reUrl += getGetArgs(args[argIndex])
            } else {
                reUrl += "/" + args[argIndex]
            }
        }
        lastUrls[key] = reUrl
        return reUrl
    }

    function getPostArgs(dictData) {
        let res = ""
        for (let key in dictData) {
            if (res) {
                res += "&"
            }
            res += key + "=" + dictData[key]
        }
        return res
    }

    function getGetArgs(dictData) {
        let res = ""
        for (let key in dictData) {
            if (res) {
                res += "&"
            } else {
                res += "?"
            }
            res += key + "=" + dictData[key]
        }
        return res
    }
}
