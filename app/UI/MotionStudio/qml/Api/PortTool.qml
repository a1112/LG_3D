import QtQuick

Item {
    property var server_port_base: coreSetting.server_port

    function getAutoUrl(key){
        return protocol + hostname + ":" + server_port_base
    }
    function getAutoWsUrl(key){
        return ws_protocol + hostname + ":" + server_port_base
    }
}
