//全局状态

import QtQuick

Item {
    property bool connectServer:false

    Timer {
        id: connectServerFlushTimer
        interval: 300
        repeat: false
        onTriggered: coreSignal.flush_app()
    }

    onConnectServerChanged:{
        if (connectServer){
            connectServerFlushTimer.restart()
        }
    }


}
