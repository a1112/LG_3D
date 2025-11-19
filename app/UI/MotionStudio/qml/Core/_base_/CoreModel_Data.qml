import QtQuick

Item {
    // 判断服务器是否在本地
    readonly property bool serverInLocal: api.apiConfig.hostname === "127.0.0.1"

    // 是否显示图像遮挡
    property bool imageMaskChecked: false
    // 显示区域初始状态
    property var toolDict: {
        return {
            "adjust":false,
            "defectShow":true,
            "location":true
        }
    }

    // 显示区域数据
    property var toolBarModel:ListModel{
        ListElement{
            source_icon: "qrc:/resource/icon/tool.png"
            tool_visible: false
            tipText_info: "调整"
            key: "adjust"
        }
        ListElement{
            source_icon: "qrc:/resource/icon/defectIcon.png"
            tool_visible: true
            tipText_info: "缺陷显示"
            key: "defectShow"
        }
        ListElement{
            source_icon: "qrc:/resource/icon/location.png"
            tool_visible: true
            tipText_info: "点"
            key: "location"
        }
    }

    property var alarmGlobVis: {
            "相机":false,
            "网络":false,
            "硬件":false
        }

    property var alarmVis: {
            "扁卷":false,
            "塔形":false,
            "松卷":false,
            "缺陷":false
        }

    property ListModel alarmGlobModel: ListModel{
        ListElement{
            key:"相机"
            level: 1
        }
        ListElement{
            key:"网络"
            level: 1
        }
        ListElement{
            key:"硬件"
            level: 1
        }
    }
    property ListModel alarmModel: ListModel{
        ListElement{
            key:"扁卷"
            level: 1
        }

        ListElement{
            key:"塔形"
            level: 1
        }
        ListElement{
            key:"松卷"
            level: 1
        }
        ListElement{
            key:"缺陷"
            level: 1
        }
    }
    property var allViewKeys: ["GRAY","JET"]

}
