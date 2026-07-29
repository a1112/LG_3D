/*
    信号处理中心


*/
import QtQuick

Item {
    required property var initController

    function flush_app() {
        // A reconnect can point to another server. Refresh server metadata,
        // the defect dictionary and the live coil list as one operation.
        initController.refreshAll(true)
    }

}
