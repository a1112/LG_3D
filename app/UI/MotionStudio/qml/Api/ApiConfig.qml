import QtQuick

Item {
    id: root
    required property var settings

    property var lastUrls: ({})

    readonly property string protocol: "http://"
    readonly property string ws_protocol: "ws://"
    readonly property string hostname: root.settings.server_ip

    readonly property int pythonApiPort: 5010
    readonly property int rustApiPort: 5011
    readonly property int pythonImageServerPort: 6012
    readonly property int rustImageServerPort: 6013
    readonly property int activeApiPort: root.settings.useRustTestServer ? rustApiPort : pythonApiPort
    readonly property int activeImageServerPort: root.settings.useRustImageServer
                                                  ? rustImageServerPort : pythonImageServerPort

    readonly property string serverUrl: protocol + hostname + ":" + activeApiPort
    readonly property string wsServerUrl: ws_protocol + hostname + ":" + activeApiPort
    readonly property string serverUrlDaaBase: serverUrl
    readonly property string wsServerUrlDaaBase: wsServerUrl
    readonly property string serverUrlData: serverUrl
    readonly property string serverUrlImage: protocol + hostname + ":" + activeImageServerPort
    readonly property string rustImageServerUrl: protocol + hostname + ":" + rustImageServerPort
    readonly property string serverUrlAlg2D: root.settings.useRustTestServer
                                              ? serverUrl
                                              : protocol + hostname + ":6020"

    // These values are retained for network diagnostics; they are not user settings.
    readonly property int port: activeApiPort
    readonly property int databasPort: activeApiPort
    readonly property int dataPort: activeApiPort
    readonly property int plcPort: activeApiPort
    readonly property int alg2dPort: root.settings.useRustTestServer ? rustApiPort : 6020
    readonly property bool usingRustImageServer: root.settings.useRustImageServer

    function getLastUrlByKey(key) {
        return lastUrls[key]
    }

    function getBaseUrl() {
        return serverUrl
    }

    function url(reUrl, ...args) {
        let key = args.length > 0 ? String(args[0]) : reUrl
        for (let argIndex = 0; argIndex < args.length; ++argIndex) {
            let argument = args[argIndex]
            if (argument !== null && typeof argument === "object") {
                reUrl += getGetArgs(argument)
            } else {
                reUrl += "/" + String(argument)
            }
        }
        // Keep URL construction safe inside bindings (especially WebSocket.url).
        // Reassigning lastUrls here would make the binding depend on and mutate
        // the same property, causing a binding loop.
        root.lastUrls[key] = reUrl
        return reUrl
    }

    function getPostArgs(dictData) {
        let res = ""
        for (let key in dictData) {
            if (res) {
                res += "&"
            }
            res += encodeURIComponent(key) + "=" + encodeURIComponent(dictData[key])
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
            res += encodeURIComponent(key) + "=" + encodeURIComponent(dictData[key])
        }
        return res
    }
}
