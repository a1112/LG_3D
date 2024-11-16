import QtQuick 2.15
import QtQuick.Controls 2.15

Row {
    Timer {
        id: timer
        interval: 1000; running: true; repeat: true
        onTriggered: {
            var currentDate = new Date()
            label.text = currentDate.getFullYear() + "年" + (currentDate.getMonth() + 1) + "月" + currentDate.getDate() + "日 " + currentDate.toLocaleTimeString()
        }
    }

    Text {
        id: label
        font.pixelSize: 24
        color: "#FFF"
    }
}
