pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import "../../../../types"
BaseSelectPop {
    id: root

    required property DateTime dateTime

    width: 170
    height: 150

    GridView {
        anchors.fill: parent
        anchors.margins: 8
        model: root.dateTime.monthModel
        cellWidth: 50
        cellHeight: 32

        delegate: CheckRec {
                required property int value
                style: root.style
                height: 30
                checked: root.dateTime.month === value
                checkColor: checked ? root.style.statusWarningColor
                                    : "transparent"
                fillWidth: true
                width: 48
                text: value
                onClicked: {
                    root.dateTime.setMonth(value)
                    root.close()
                }
            }
    }
}

