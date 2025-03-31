import QtQuick

import QtQuick.Layouts

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
        StackLayout{
            currentIndex:app_core.appIndex
            Layout.fillWidth: true
            Layout.fillHeight: true
        DataShowRoot{}  // 主 界面

        DefectShowRoot{} // 缺陷 界面

        }
        LeftPrePop{     //   弹出 窗口
        }
    }
}
