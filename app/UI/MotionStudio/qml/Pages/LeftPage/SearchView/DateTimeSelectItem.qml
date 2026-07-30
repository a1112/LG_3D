import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../types"
import "../../Header"
import "DateTimeSelectPop"
ColumnLayout {
    id: root

    required property DateTime dateTime_
    required property var style

    height: 35
    property string title_: "起始:"

    RowLayout {
        Layout.fillWidth: true
        id: dt

        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        Label{
            color: root.style.titleColor
            font.bold: true
            font.family: "Microsoft YaHei UI"
            font.pointSize: 14
            text: root.title_
        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }

        CheckRec{
            style: root.style
            fillWidth: true
            text: root.dateTime_.fullYear
            implicitHeight: 20
            onClicked: yc.popup()

            YearSelectPop{
                id: yc
                dateTime: root.dateTime_
                style: root.style
            }
        }
        Label{
            text: "年"
        }
        CheckRec{
            style: root.style
            fillWidth: true
            text: root.dateTime_.month
            onClicked: mc.popup()
            implicitHeight: 20

            MonthSelectPop{
                id: mc
                dateTime: root.dateTime_
                style: root.style
            }

        }
        Label{
            text: "月"
        }
        CheckRec{
            style: root.style
            fillWidth: true
            text: root.dateTime_.day
            implicitHeight: 20
            onClicked: dc.popup()

            DaySelectPop{
                id: dc
                dateTime: root.dateTime_
                style: root.style
            }
        }
        Label{
            text: "日  "
        }
    }

    RowLayout{
        Layout.fillWidth: true
        Item{
            implicitHeight: 40
            Layout.fillWidth: true
            TextField {
                x:-20
                height: 40
                scale: 0.7
                width: parent.width/0.8
                text: root.dateTime_.dateTimeString
                placeholderText: root.dateTime_.formatDateTimeString
                validator: RegularExpressionValidator{
                    regularExpression: /^[0-9]{4}[0-9]{2}[0-9]{2}[0-9]{2}[0-9]{2}$/
                }
                color: acceptableInput ? root.style.statusSuccessColor
                                       : root.style.statusErrorColor
                selectByMouse: true
                onEditingFinished: {
                    if (!root.dateTime_.applyDateTimeString(text)) {
                        text = root.dateTime_.dateTimeString
                    } else {
                        text = root.dateTime_.dateTimeString
                    }
                }
            }


        }
        CheckRec{
            style: root.style
            text: root.dateTime_.hour
            implicitHeight: 20
            onClicked: d_t.popup()
            fillWidth:true
            TimeSelectPop{
                id: d_t
                dateTime: root.dateTime_
                style: root.style
            }
        }
        Label{
            text: "时"
        }
        CheckRec{
            style: root.style
            text: root.dateTime_.minute
            implicitHeight: 20
            fillWidth: true
            onClicked: d_t.popup()
        }
        Label{
            text: "分"
        }
    }
}
