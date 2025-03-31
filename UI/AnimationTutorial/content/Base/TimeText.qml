import QtQuick 2.15
import QtQuick.Controls 2.15

Row {
    Timer {
        id: timer
        interval: 1000; running: true; repeat: true
        onTriggered: {
            var currentDate = new Date()
            label.text = currentDate.getFullYear() + "-" + (currentDate.getMonth() + 1) + "-" + currentDate.getDate() + " " + currentDate.toLocaleTimeString()
        }
    }

    Label {
        font.family: fonts.timeFamioly//"DS-DIGIT"
        id: label
        font.pixelSize: 24

    }
}
