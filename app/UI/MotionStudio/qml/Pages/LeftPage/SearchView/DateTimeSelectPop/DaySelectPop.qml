pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import QtQuick.Layouts
import "../../../../types"
BaseSelectPop {
    id: root

    required property DateTime dateTime

    readonly property int firstDayOffset: new Date(
                                              root.dateTime.fullYear,
                                              root.dateTime.month - 1,
                                              1).getDay()
    readonly property int days: root.dateTime.daysInMonth

    width: col.width
    height: col.height

    Column {
        id: col
        anchors.centerIn: parent
        spacing: 2

        Pane {
            height: titleLab.height
            width: col.width
            Material.background: root.style.panelElevatedColor

            RowLayout {
                anchors.fill: parent

                Label {
                    id: titleLab
                    text: root.dateTime.formatDate
                    font.pixelSize: 24
                    color: root.style.titleColor
                    horizontalAlignment: Text.AlignHCenter
                }

                ComboBox {
                model: root.dateTime.yearModel
                    currentIndex: root.dateTime.fullYear
                                  - root.dateTime.nowFullYear + 7
                    onActivated: root.dateTime.setYear(Number(currentText))
                implicitHeight: titleLab.height
                }

                ComboBox {
                    model: root.dateTime.monthModel
                    currentIndex: root.dateTime.month - 1
                    implicitHeight: titleLab.height
                    onActivated: root.dateTime.setMonth(Number(currentText))
                }
            }
        }

        Grid {
            columns: 7
            spacing: 0

            Repeater {
                model: ["日", "一", "二", "三", "四", "五", "六"]

                delegate: Item {
                    id: weekdayDelegate
                    required property string modelData
                    width: 60
                    height: 30

                    CheckRec {
                        style: root.style
                        width: parent.width
                        text: weekdayDelegate.modelData
                        checked: false
                        checkColor: "transparent"
                        height: 30
                    }
                }
            }

            Repeater {
                model: 42

                delegate: Item {
                    id: dayDelegate
                    required property int index
                    readonly property int day: index - root.firstDayOffset + 1
                    width: 60
                    height: 30

                    CheckRec {
                        style: root.style
                        width: parent.width
                        fillWidth: true
                        checked: root.dateTime.day === dayDelegate.day
                        color: checked ? root.style.statusWarningColor
                                       : root.style.textColor
                        checkColor: checked ? root.style.statusWarningColor
                                            : "transparent"
                        visible: dayDelegate.day >= 1
                                 && dayDelegate.day <= root.days
                        height: 30
                        text: dayDelegate.day
                        onClicked: {
                            root.dateTime.setDay(dayDelegate.day)
                            root.close()
                        }
                    }
                }
            }
        }
    }
}
