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
        spacing: 30
        Item{
            Layout.preferredWidth: 20
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
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
            GlobalErrorView{    // 全局报警
                anchors.centerIn: parent
            }
        }
        TitleLabel{}
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }



        TopCoilTools{
        }

        Row{
            // CheckRec{
            //      checkColor: "#52FFFFFF"
            //     text: "恢复"
            // }
            spacing:10
            ToolsButton{
               height:35
               width:height
               onClicked:{
                    toolsMenu.popup()
               }

            }
                    TopWindowModelChangeButton {}
        }


}
}
