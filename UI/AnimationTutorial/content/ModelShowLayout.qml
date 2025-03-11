import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "Pages/LeftPage"
import "DataShow"
import "Pages/Header"
import "Pages/Pop"
Item {
    width: 1980
    height: 1080
    anchors.fill: parent
    id:root
    ColumnLayout{
        spacing: 10
        anchors.fill: parent
        TopHeader{      // 标题界面
            Layout.fillWidth: true
            implicitHeight: coreStyle.topHeight
        }

        SplitView{
            Layout.fillWidth: true
            Layout.fillHeight: true
            LeftPageView{  // 左侧列表
                id:left
                SplitView.fillHeight: true
                SplitView.preferredWidth:coreStyle.leftWidth
                SplitView.minimumWidth: 300
                SplitView.maximumWidth: 500
            }
                DataShowLayout{    // 数据显示
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }

        }
        LeftPrePop{     //   弹出 窗口
        }
    }
}
