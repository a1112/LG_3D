import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import QtQuick.Layouts
import "../../../../types"
BaseSelectPop{
    id:root
    width:col.width
    height:col.height
     property DateTime dateTime
    property int currentYear: dateTime.fullYear
    property int currentMonth: dateTime.month
    property int currentDay:dateTime.day
    property date today: new Date() // 当前日期
    property int dayOfWeek:0
    property int days:flush(currentYear,currentMonth)

    function flush(year,month){
        let dat= new Date(currentYear, currentMonth , 0)

        dayOfWeek = dat.getDay()
        return dat.getDate()
    }

    Column {
        id:col
        anchors.centerIn: parent
        spacing: 2
        Pane{
            height: titleLab.height
            width: col.width
        RowLayout{
            anchors.fill:parent
            // Pane{
            //     anchors.fill: parent
            // }
        Label {
            id:titleLab
            text:root.dateTime.formatDate
            font.pixelSize: 24
            color:Material.color(Material.Blue)
            horizontalAlignment: Text.AlignHCenter

        }
            ComboBox{
                model: root.dateTime.yearModel
                currentIndex:root.dateTime.fullYear-dateTime.nowFullYear+7
                onCurrentTextChanged:
                {
                console.log(currentText)
                root.dateTime.fullYear=parseInt(currentText)
                }

                implicitHeight: titleLab.height

            }
            ComboBox{
                 model:  root.dateTime.monthModel
                 currentIndex:root.dateTime.month-1
                 implicitHeight: titleLab.height
                 onCurrentTextChanged:
                 {
                 root.dateTime.month=parseInt(currentText)
                 }
            }
        }
        }
        Grid {
            columns: 7
            spacing: 0

            // 显示星期标题
            Repeater {
                model: ["日", "一", "二", "三", "四", "五", "六"]
                Item{
                    width: 60
                    height:30
                CheckRec {
                    width:parent.width
                    text: modelData

                    checkColor:"#00000000"
                    height:30
                }
                }
            }

            // 显示天数
            Repeater {
                model: 40
                Item{
                    width: 60
                    height: 30
                CheckRec {
                    property int day:(index + 2-dayOfWeek)
                    width: parent.width
                    fillWidth:true
                    color:dateTime.day==day?Material.color(Material.Orange):coreStyle.textColor
                    checkColor:dateTime.day==day?Material.color(Material.Orange):"#00000000"
                    visible:day>=1&&day<=days
                    height: 30
                        text: day
                    onClicked:{
                        dateTime.day=day
                        root.close()
                    }
                }
                }
            }
        }
    }

    // 获取当前月份的天数

}
