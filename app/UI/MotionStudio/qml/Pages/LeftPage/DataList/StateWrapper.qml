import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../animation"
Row {
    id: root
    required property var summary
    // property CoilState c_state
    spacing:1

    // AnimLabel{
    //     text: "扁卷"
    //     opacity: 0.5
    //     visible: index%12==0//c_state.flatRollWarning
    //     font.pixelSize: 9
    //     font.bold: true
    //                 background:Rectangle{
    //                     radius: 3
    //                     color: Material.color(Material.DeepPurple)}
    // }
    Item{
        height:20
        width:20
    AnimErrorImage{
        running:false
        visible: root.summary.grad > 1
        width: parent.width
        height: parent.height
                    source: root.summary.level2Source(root.summary.grad)
    }
    }
    // Repeater{
    //     model:alarmNodel
    //     AnimRec{
    //         running:true
    //         width: 10
    //         height: 10
    //         radius: 10
    //         color: Material.color(Material.Pink)
    //     }
    // }

}
