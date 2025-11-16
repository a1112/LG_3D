import QtQuick 2.15
DateTime{
    //   刷新 时间
        property alias interval: timer.interval
    Timer{
        id:timer
        triggeredOnStart:true
        repeat: true
        running: true
        interval: 1000
        onTriggered: {
            let nowDate= new Date()
            fullYear=nowDate.getFullYear()
            year=fullYear%100
            month=nowDate.getMonth()+1
            day=nowDate.getDate()
            week=nowDate.getDay()
            hours=nowDate.getHours()
            minutes=nowDate.getMinutes()
            second=nowDate.getSeconds()
        }

    }
}
