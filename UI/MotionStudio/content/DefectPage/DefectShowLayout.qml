import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Head"
import "HistoryView"
import "Core"
Item {
    id:page_defect_view

    property DefectViewCore defectViewCore:DefectViewCore{}

    ColumnLayout{
        anchors.fill: parent
        // HeadView{
        //     height: 80
        //     Layout.fillWidth: true
        // }

            SplitView{
                Layout.fillWidth: true
                Layout.fillHeight: true
                LeftDataView{   // 主要界面

                }
                RightViewList{

                }
            }


    }
}
