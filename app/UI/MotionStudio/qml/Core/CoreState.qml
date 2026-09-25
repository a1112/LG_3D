//全局状态

import QtQuick

Item {
    id: root

    required property var signalController

    property bool connectServer: false
    readonly property bool connected: connectServer
    property date lastConnectedAt
    property date lastDisconnectedAt
    property int reconnectCount: 0

    Timer {
        id: connectServerFlushTimer
        interval: 300
        repeat: false
        onTriggered: root.signalController.flush_app()
    }

    onConnectServerChanged: {
        if (connectServer) {
            lastConnectedAt = new Date()
            reconnectCount += 1
            connectServerFlushTimer.restart()
        } else {
            lastDisconnectedAt = new Date()
            connectServerFlushTimer.stop()
        }
    }


}
