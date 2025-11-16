/*
    信号处理中心


*/
import QtQuick

Item {
    function flush_app(){
        console.log("flush app")
        // 刷新 连接状态，在 IP 刷新时 或者连接启动时
        init.flushDefectDict()
        init.flushList()
    }

}
