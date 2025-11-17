import QtQuick.Controls
import QtQuick.Layouts
import "Pages/LeftPage"
import "DataShow"
/*
    图像显示主界面


*/
SplitView{
    Layout.fillWidth: true
    Layout.fillHeight: true
    LeftPageView{  // 左侧列表
        id:left
        SplitView.fillHeight: true
        SplitView.preferredWidth:coreStyle.leftWidth
        SplitView.minimumWidth: 330
        SplitView.maximumWidth: 550
    }
    DataShowLayout{    // 数据显示
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
}
