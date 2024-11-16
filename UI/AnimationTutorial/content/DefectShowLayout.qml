import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "DefectPage/Head"
import "DefectPage"
import "DefectPage/HistoryView"

Item {
    width: 1920
    height: 1080
    Rectangle{
        anchors.fill: parent
        color: "#0E1C41"
    }
    ColumnLayout{
        anchors.fill: parent
        HeadView{
            height: 80
            Layout.fillWidth: true
        }
        DefectPageView{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
