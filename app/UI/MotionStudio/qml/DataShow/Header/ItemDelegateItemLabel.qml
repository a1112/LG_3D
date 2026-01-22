import QtQuick
import "../Foot"
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
    property bool has_data: coreModel && coreModel.has_data && surfaceData && surfaceData.key ? coreModel.has_data[surfaceData.key][key] || false : false
    // Rectangle{
    //     visible: has_data
    //     border.color: "gray"
    //     border.width: 1
    //     anchors.fill: parent
    //     color: "#00000000"
    // }
}
