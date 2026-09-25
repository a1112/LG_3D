pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "DataShowItem"
Loader{
    id: root

    required property var surfaceData
    required property var controller
    required property var areaController
    required property var style
    required property var alarmInfo
    required property var apiClient
    required property var globalContext

    // 头部信息显示
    asynchronous: true
    sourceComponent:RowLayout{
        Layout.fillWidth: true
        DataShowItemSelectView{
            Layout.fillHeight: true
            controller: root.controller
            style: root.style
            apiClient: root.apiClient
        }
        StackLayout{
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.controller.topDataManage.currentShowModel
            DataShowItemDefects{  // 缺陷显示 界面
                surfaceData: root.surfaceData
                controller: root.controller
                areaController: root.areaController
                style: root.style
                apiClient: root.apiClient
                globalContext: root.globalContext
            }

            DataShowItemInfos{      // 数据信息
                alarmInfo: root.alarmInfo
            }

            DataShowItemCharts{  //  charts
                surfaceData: root.surfaceData
                controller: root.controller
                style: root.style
            }

        }
    }
}
