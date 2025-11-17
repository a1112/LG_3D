import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../AlarmCore"
import "../AlarmSimple"
Item {
    property CoreFlatRollItem coreFlatRollItem
    id:root
    width:parent.width
    height:col.height


    Frame{
        anchors.fill: parent
    }
    Row{
        id:row
        width:parent.width

        spacing: 10
        HovValueTextLabel{
            id:titleLabel
            text:coreFlatRollItem.global_key
            font.pointSize: 14
            font.bold: true
            color: Material.color(Material.Yellow)
            font.family: "Microsoft YaHei"
            anchors.verticalCenter: col.verticalCenter
            toolTipText:"扁卷检测\n"+
                        "外圈圆心 x:"+coreFlatRollItem.out_circle_center_x+" y:"+coreFlatRollItem.out_circle_center_y+"\n"+
                        "外椭圆宽高 旋转角度: "+coreFlatRollItem.out_circle_width+" "+coreFlatRollItem.out_circle_height+" "+coreFlatRollItem.out_circle_radius+"\n"+
                        "内圈圆心 x:"+coreFlatRollItem.inner_circle_center_x+" y:"+coreFlatRollItem.inner_circle_center_y+"\n"+
                        "内椭圆宽高 旋转角度: "+coreFlatRollItem.inner_circle_width+" "+coreFlatRollItem.inner_circle_height+" "+coreFlatRollItem.inner_circle_radius
        }
        Column{
            id:col
            width:root.width-titleLabel.width
            SimpleWidVelue{
                title:"内径"
                value_1:coreFlatRollItem.inner_circle_width
                value_2:coreFlatRollItem.inner_circle_width-core.currentCoilModel.coilInside
            }

            SimpleWidVelue{
                width:col.width
                title:"外径"
                value_1:coreFlatRollItem.out_circle_width
                value_2:coreFlatRollItem.out_circle_width-core.currentCoilModel.coilDia
                height: 30
            }
            SimpleRatioVelue{
                width:col.width
                title:"椭圆拟合"
                value_1:coreFlatRollItem.inner_circle_width
                value_2:coreFlatRollItem.inner_circle_height
                height: 30
            }
        }


    }



}
