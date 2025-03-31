import QtQuick.Controls
import QtQuick.Layouts
import "Pages/LeftPage"
import "DataShow"

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
