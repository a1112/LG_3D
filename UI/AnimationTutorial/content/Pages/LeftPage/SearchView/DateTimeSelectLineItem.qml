import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../types"
import "../../Header"
import "DateTimeSelectPop"

    RowLayout {
        id:root
        property DateTime dateTime_
        height: 20
        property string title_:""

        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        Label{
            color:Material.color(Material.Blue)
            font.bold:true
            font.family: "Microsoft YaHei UI"
            font.pointSize: 14
            text:root.title_
        }
        CheckRec{
            fillWidth: true
            text: root.dateTime_.fullYear
            implicitHeight: 20
            onClicked:{
            yc.popup()
            }

            YearSelectPop{
                id:yc
                dateTime:root.dateTime_
            }
        }
        Label{
            text: "年"
        }
        CheckRecTimeItem{
            fillWidth: true
            text: root.dateTime_.month
            onClicked:mc.popup()
            implicitHeight: 20
            MonthSelectPop{
                id:mc
                dateTime:root.dateTime_
            }

        }
        Label{
            text: "月"
        }
        CheckRecTimeItem{
            fillWidth: true
            text: root.dateTime_.day
            implicitHeight: 20
            onClicked:dc.popup()
            DaySelectPop{
                id:dc
                dateTime:root.dateTime_
            }
        }
        Label{
            text: "日  "
        }

        CheckRecTimeItem{
            text: root.dateTime_.hour
            implicitHeight: 20
            onClicked: d_t.popup()
            fillWidth:true
            TimeSelectPop{
                id:d_t
                dateTime:root.dateTime_
            }
        }
        Label{
            text: "时"
        }
        CheckRecTimeItem{
            text: root.dateTime_.minute
            implicitHeight: 20
            fillWidth:true
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

