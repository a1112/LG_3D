import QtQuick
QtObject {
    property var dateTime: new Date()
    property string str:Qt.formatDateTime(dateTime,"yyyy_MM_dd hh_mm_ss")
    property var dataString:Qt.formatDateTime(dateTime,"yyyy年MM月dd日")
    property var timeString:Qt.formatDateTime(dateTime,"hh点mm分ss秒")
    function formatDateTime(formatStr="yyyy_MM_dd hh_mm_ss"){
        return Qt.formatDateTime(dateTime,formatStr)
    }

    function initByDict(date_time){
        // 后端数据的转换
        dateTime = new Date(date_time["year"],date_time["month"]-1,date_time["day"],
                            date_time["hour"],date_time["minute"],date_time["second"])

    }
}
