import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../types"
import "../../Header"
import "DateTimeSelectPop"

RowLayout {
    id: root

    required property DateTime dateTime_
    required property var style

    height: 20
    property string title_: ""


        Label{
            color: root.style.titleColor
            font.bold: true
            font.family: "Microsoft YaHei UI"
            font.pointSize: 14
            text: root.title_
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
        CheckRecTimeItem{
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
        CheckRecTimeItem{
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

        CheckRecTimeItem{
            style: root.style
            text: root.dateTime_.hour
            implicitHeight: 20
            onClicked: d_t.popup()
            fillWidth: true

            TimeSelectPop{
                id: d_t
                dateTime: root.dateTime_
                style: root.style
            }
        }
        Label{
            text: "时"
        }
        CheckRecTimeItem{
            style: root.style
            text: root.dateTime_.minute
            implicitHeight: 20
            fillWidth: true
            onClicked: d_t.popup()
        }
        Label{
            text: "分"
        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
}

