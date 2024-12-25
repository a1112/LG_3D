import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
// import Qt5Compat.GraphicalEffects
// import "../../Base" as Base
import "../../btns"
// import "../../DataShow/Foot"
import "../../GlobalView"
Item {
    id:root
    width: 1080
    height: 35
            clip: false
    Pane{
        anchors.fill: parent
        Material.elevation: 5
    }
    Rectangle{
        color:"blue"
        anchors.fill: parent
        opacity:0.1
    }
    Rectangle{
        width: parent.width
        height: 1
                opacity:0.1
        color: "#FFF"
        anchors.bottom: parent.bottom
    }
    RowLayout{
        anchors.fill: parent
        spacing: 10
        Item{
            Layout.preferredWidth: 1
            Layout.preferredHeight: 1
        }
        TopIcon{}
        TopTabBar{}
        SeparatorLine{}
        TopTools{}
        TopSettingButton{}

        Item{
            implicitWidth: 50
            Layout.fillHeight: true
        }
        TopMsg{}
        FillLayout{
            GlobalErrorView{    // 全局报警
                anchors.centerIn: parent
            }
        }
        TitleLabel{}
        FillLayout{}
        GlobalServerMsg{}
        FillLayout{}
        TopCoilTools{}
        Item{
            implicitWidth: 20
            Layout.fillHeight: true
        }
        Row{
            spacing:10
            TopToolsButton{}
            TopWindowModelChangeButton {}
        }


}
}
