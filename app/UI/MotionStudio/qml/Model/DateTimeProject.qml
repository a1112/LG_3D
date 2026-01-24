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
        // 后端数据的转换，支持多种输入格式
        if (!date_time) {
            dateTime = new Date()
            return
        }

        // 如果是字典格式 {"year":..., "month":..., ...}
        if (typeof date_time === "object" && "year" in date_time) {
            dateTime = new Date(date_time["year"], date_time["month"]-1, date_time["day"],
                                date_time["hour"], date_time["minute"], date_time["second"])
        }
        // 如果是字符串格式 (ISO 8601 或其他 Date.parse 支持的格式)
        else if (typeof date_time === "string") {
            dateTime = new Date(date_time)
        }
        // 如果已经是 Date 对象
        else if (date_time instanceof Date) {
            dateTime = new Date(date_time)
        }
        else {
            console.warn("DateTimeProject.initByDict: unsupported date_time format", date_time)
            dateTime = new Date()
        }
    }
}
