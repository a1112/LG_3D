import QtQuick

Item {
    id: root

    readonly property var now: getNow()
    readonly property int nowFullYear: now.getFullYear()

    property var dateTime: getNow()

    property int fullYear: dateTime.getFullYear()
    property int month: dateTime.getMonth() + 1

    property int day: dateTime.getDate()
    property int hour: dateTime.getHours()
    property int minute: dateTime.getMinutes()
    property int second: dateTime.getSeconds()

    readonly property int daysInMonth: new Date(fullYear, month, 0).getDate()
    readonly property string formatDate: Qt.formatDate(
                                                new Date(fullYear, month - 1, day),
                                                "yyyy-MM-dd")
    readonly property string formatDateTimeString: "yyyyMMddHHmm"
    readonly property string dateTimeString: Qt.formatDateTime(
                                                  getCurrentDate(),
                                                  formatDateTimeString)

    onFullYearChanged: clampDay()
    onMonthChanged: clampDay()

    function getCurrentDate() {
        return new Date(fullYear, month - 1, day, hour, minute, second)
    }

    function getNow() {
        return new Date()
    }

    function clampDay() {
        const maximum = new Date(fullYear, month, 0).getDate()
        day = Math.max(1, Math.min(day, maximum))
    }

    function setYear(value) {
        const parsed = Number(value)
        if (Number.isInteger(parsed) && parsed >= 1900 && parsed <= 9999) {
            fullYear = parsed
            clampDay()
            return true
        }
        return false
    }

    function setMonth(value) {
        const parsed = Number(value)
        if (Number.isInteger(parsed) && parsed >= 1 && parsed <= 12) {
            month = parsed
            clampDay()
            return true
        }
        return false
    }

    function setDay(value) {
        const parsed = Number(value)
        if (Number.isInteger(parsed) && parsed >= 1 && parsed <= daysInMonth) {
            day = parsed
            return true
        }
        return false
    }

    function setTime(newHour, newMinute) {
        const parsedHour = Number(newHour)
        const parsedMinute = Number(newMinute)
        if (!Number.isInteger(parsedHour) || parsedHour < 0 || parsedHour > 23
                || !Number.isInteger(parsedMinute) || parsedMinute < 0
                || parsedMinute > 59) {
            return false
        }
        hour = parsedHour
        minute = parsedMinute
        return true
    }

    function setDate(value) {
        if (!(value instanceof Date) || isNaN(value.getTime())) {
            return false
        }
        dateTime = value
        fullYear = value.getFullYear()
        month = value.getMonth() + 1
        day = value.getDate()
        hour = value.getHours()
        minute = value.getMinutes()
        second = value.getSeconds()
        return true
    }

    function applyDateTimeString(value) {
        if (!/^\d{12}$/.test(value)) {
            return false
        }

        const parsedYear = Number(value.slice(0, 4))
        const parsedMonth = Number(value.slice(4, 6))
        const parsedDay = Number(value.slice(6, 8))
        const parsedHour = Number(value.slice(8, 10))
        const parsedMinute = Number(value.slice(10, 12))
        const candidate = new Date(parsedYear, parsedMonth - 1, parsedDay,
                                   parsedHour, parsedMinute, 0)
        if (candidate.getFullYear() !== parsedYear
                || candidate.getMonth() + 1 !== parsedMonth
                || candidate.getDate() !== parsedDay
                || candidate.getHours() !== parsedHour
                || candidate.getMinutes() !== parsedMinute) {
            return false
        }

        fullYear = parsedYear
        month = parsedMonth
        day = parsedDay
        hour = parsedHour
        minute = parsedMinute
        second = 0
        return true
    }

    property ListModel yearModel: ListModel {}
    property ListModel monthModel: ListModel {}

    Component.onCompleted: {
        yearModel.clear()
        for (let year = nowFullYear - 7; year < nowFullYear + 2; year++) {
            yearModel.append({ value: year })
        }

        monthModel.clear()
        for (let monthValue = 1; monthValue <= 12; monthValue++) {
            monthModel.append({ value: monthValue })
        }
    }
}
