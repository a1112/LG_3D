import QtQuick 2.15
import QtQuick.Controls 2.15
import "../fonts" as Fonts

Row {
    property var fonts: Fonts.LoadFont {}

    Timer {
        id: timer
        interval: 1000; running: true; repeat: true
        triggeredOnStart: true
        onTriggered: {
            var currentDate = new Date()
            var year = currentDate.getFullYear()
            var month = currentDate.getMonth() + 1
            var day = currentDate.getDate()
            var hours = currentDate.getHours()
            var minutes = currentDate.getMinutes()
            var seconds = currentDate.getSeconds()
            // 格式化：YYYY-MM-DD HH:mm:ss
            label.text = year + "-" +
                         (month < 10 ? "0" : "") + month + "-" +
                         (day < 10 ? "0" : "") + day + " " +
                         (hours < 10 ? "0" : "") + hours + ":" +
                         (minutes < 10 ? "0" : "") + minutes + ":" +
                         (seconds < 10 ? "0" : "") + seconds
        }
    }

    Label {
        font.family: fonts.timeFamioly || "Microsoft YaHei"
        id: label
        font.pixelSize: 24
        color: "#333"
    }
}
