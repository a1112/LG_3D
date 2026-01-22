import QtQuick 2.15
Item{
    // 日期 时间
    property int fullYear: new Date().getFullYear()
    property int year: new Date().getFullYear() % 100
    property int month: new Date().getMonth() + 1
    property int week: new Date().getDay()
    property int day: new Date().getDate()

    property int hours: new Date().getHours()
    property int minutes: new Date().getMinutes()
    property int second: new Date().getSeconds()

}
