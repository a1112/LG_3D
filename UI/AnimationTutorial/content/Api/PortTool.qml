import QtQuick

Item {

    property var server_port_base: coreSetting.server_port
    property int server_port_count:coreSetting.server_port_count

    property int porintCount:0

    property var eqMap:{
    "defect_image":"image"
    }

    property var port_assignments:{
        //  端口自动分配字典
        return {}
    }

    function stringToHash(str) {
        let hash = 0
        for (let i = 0; i < str.length; i++) {
            let ch = str.charCodeAt(i)
            hash = (hash << 5) - hash + ch
            hash |= 0 // 转换为 32 位整数
        }
        return hash
    }

    function get_key_port(key){
       // console.log("get_key_port ", key)
        if (key in eqMap){
            key=eqMap[key]
        }
        if (key in port_assignments){
            return server_port_base + Math.min(port_assignments[key], server_port_count-1)
        }

        let hash_key = stringToHash(key)
        port_assignments[key] = Math.abs(parseInt(hash_key % server_port_count))
        // _pre_port_value_+=1
        // if (_pre_port_value_>=server_port_count){
        //     _pre_port_value_=0
        // }
        return get_key_port(key)
    }

    function getAutoUrl(key){
        return protocol + hostname + ":" + get_key_port(key)
    }
    function getAutoWsUrl(key){
        return ws_protocol + hostname+ ":" + server_port_base
    }
}
