pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "DataShowItem"
Loader{
    id: root

    required property var surfaceData
    required property var controller
    required property var style

    // 头部信息显示
    asynchronous: true
    sourceComponent:RowLayout{
        Layout.fillWidth: true
        DataShowItemSelectView{
            Layout.fillHeight: true
        }
        StackLayout{
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.controller.topDataManage.currentShowModel
            DataShowItemDefects{  // 缺陷显示 界面
            }

            DataShowItemInfos{      // 数据信息
            }

            DataShowItemCharts{  //  charts
                surfaceData: root.surfaceData
                controller: root.controller
                style: root.style
            }

        }
    }
}
