import QtQuick
import QtQuick.Layouts
import "DataShowItem"
Loader{

    asynchronous: true
    sourceComponent:RowLayout{
        Layout.fillWidth: true
        DataShowItemSelectView{
            Layout.fillHeight: true
        }
        StackLayout{
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: dataShowCore.topDataManage.currentShowModel
            DataShowItemDefects{  // 缺陷显示
            }
            DataShowItemInfos{
            }
            DataShowItemCharts{  //  charts
            }
        }
    }
}
