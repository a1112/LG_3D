import QtQuick

Item {
    readonly property var now: getNow()

    readonly property int nowFullYear: now.getFullYear()

    property var dateTime:getNow()

    property int fullYear:dateTime.getFullYear()
    property int month:dateTime.getMonth()+1

    property int day:dateTime.getDate()
    property int hour:dateTime.getHours()
    property int minute:dateTime.getMinutes()
    property int second:dateTime.getSeconds()

    readonly property var formatDate: Qt.formatDate(new Date(fullYear, month-1, day), "yyyy-MM-dd")

    readonly property var formatDateTimeString:"yyyyMMddHHmm"
     property string dateTimeString:Qt.formatDateTime(getCurrentDate(), formatDateTimeString)

    function getCurrentDate(){
        return new Date(fullYear,month-1,day,hour,minute,second )
    }

    function getNow(){
        return new Date()
    }

    property ListModel yearModel:ListModel{
    }

    property ListModel monthModel:ListModel{
    }
    Component.onCompleted:{
        yearModel.clear()
        for(var i=nowFullYear -7;i<nowFullYear+2;i++){
            yearModel.append({
                                 value:i
                             })
        }

        monthModel.clear()
        for(var i=1;i<=12;i++){
            monthModel.append({
                                value:i
                             })
        }
    }
}
