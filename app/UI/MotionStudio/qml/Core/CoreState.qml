//全局状态

import QtQuick

Item {
    property bool connectServer:false
    onConnectServerChanged:{
        if (connectServer){
            coreSignal.flush_app()
        }
    }


}
