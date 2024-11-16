import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Pages/Header"
import "Base"
import "../../Base"
ColumnLayout {
    Layout.fillWidth: true
    property int level:1
    Row{
                Layout.alignment: Qt.AlignHCenter
    DropShadowRec{
        radius: 15
        width: 20
        height: 20
        color: {
            if (level==1){
                return Material.color(Material.Green)
            }
            if (level==2){
                return Material.color(Material.Yellow)
            }
            if (level==3){
                return Material.color(Material.Red)
            }
            return Material.color(Material.Grey)
        }
    }
    TitleLabel{
        text: "塔形(mm)"

    }
    }
    RowLayout{
        KeyLabel{
            text: "外 :"
        }
        ValueLabel{
            text: "1"
            Layout.fillWidth: true
        }
        Label{
            text: "圈"
        color: "#747474"
        }
        ValueLabel{
            text: "30"
            Layout.fillWidth: true
        }
        Label{
            text: "mm"
        color: "#747474"
        }
    }

    RowLayout{
        KeyLabel{
            text: "内 :"
        }
        ValueLabel{
            text: "1"
            Layout.fillWidth: true
        }
        Label{
            text: "圈"
        color: "#747474"
        }
        ValueLabel{
            text: "30"
            Layout.fillWidth: true
        }
        Label{
            text: "mm"
        color: "#747474"
        }
    }
}
