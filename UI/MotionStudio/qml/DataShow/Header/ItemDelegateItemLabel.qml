import QtQuick
import "../Foot"
import "../../icons"
ItemDelegateItem {
    property string key:""

    // Image {
    //     height: parent.height
    //     width: height
    //     id: name
    //     fillMode:Image.PreserveAspectFit
    //     source: "../../icons/warning_1.png"
    //     anchors.top: parent.bottom
    // }
    enabled: has_data
    property bool has_data: coreModel.has_data[surfaceData.key][key]
    // Rectangle{
    //     visible: has_data
    //     border.color: "gray"
    //     border.width: 1
    //     anchors.fill: parent
    //     color: "#00000000"
    // }
}
