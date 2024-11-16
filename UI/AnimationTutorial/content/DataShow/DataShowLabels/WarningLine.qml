import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Pages/Header"
import "Base"
import "../../Comp/Card"
CardBase{
    width:parent.width

    title:"塔形警戒"
    max_height:150
content_head_tool:
    CheckDelegate{
        text:"AUTO"
        height:30
        scale:0.85
        checked:surfaceData.error_auto
        onCheckedChanged:{
            surfaceData.error_auto = checked
        }
    }
content_body:
    ColumnLayout{
        id:column
        width:parent.width
       //  RowLayout{
       //      Item{
       //          Layout.fillWidth: true

       //      }
       //      TitleLabel{
       //          text:"塔形警戒"
       //          font.pixelSize:18
       //          color:Material.color(Material.Blue)
       //      }
       //      Item{
       //          Layout.fillWidth: true

       //      }

       //      Row{
       //          height:30
       //          CheckDelegate{
       //              text:"AUTO"
       //              height:30
       //              scale:0.85
       //              checked:surfaceData.error_auto
       //              onCheckedChanged:{
       //                  surfaceData.error_auto = checked
       //              }
       //          }
       //      }

       //  }

        RowSpinBoxItem{
            width:parent.width
            title:"上限："
            mm_label_visible:false
            from:0
            to:100
            value:surfaceData.tower_warning_threshold_up
            onValueChanged:{
                surfaceData.tower_warning_threshold_up = value
            }
        }
        RowSpinBoxItem{
            width:parent.width
            title:"下限："
            mm_label_visible:false
            from:-100
            to:0
            value: surfaceData.tower_warning_threshold_down
            onValueChanged:{
                surfaceData.tower_warning_threshold_down = value
            }
        }
        RowLayout{
            width:parent.width
            Item{
                implicitHeight:30
                Layout.fillWidth: true
                Slider{
                    width: parent.width
                    implicitHeight: 30
                    height: 30
                    from: 0
                    value: surfaceData.tower_warning_show_opacity
                    onValueChanged: {
                        surfaceData.tower_warning_show_opacity = value
                    }
                    to: 100
                }
            }
            Row{

                height:30

                CheckRec{
                    visible:!surfaceData.error_auto
                    implicitHeight:30
                    height:30
                    scale:0.7
                    text: "绘制错误"
                    typeIndex:1
                    onClicked: {
                        dataShowCore.errorDrawer()
                        checked=true
                    }
                }
            }
        }
    }
}
