import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
/*


*/
import "Header"
import "DataShowRoot"
import "Foot"
import "Core"
import "../Core"
import "ShowCharts"
import "../Pages/View3D"

import "MaxMinValue"
Item{
    id:root
    property SurfaceData surfaceData
    property DataShowCore dataShowCore: DataShowCore{
    }
    visible: surfaceData.show_visible
    ColumnLayout {
        anchors.fill: parent
        spacing: 5
        StackLayout{
            SplitView.fillWidth: true
            SplitView.fillHeight: true
            currentIndex: surfaceData.rootViewIndex
            SplitView{
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                // DataShowLabelsView{
                //     visible: surfaceData.key=="L"
                //     SplitView.fillHeight: true
                //     SplitView.preferredWidth: 170
                // }
                ColumnLayout{
                    SplitView.fillWidth: true
                    SplitView.fillHeight: true
                SplitView{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: Qt.Vertical
                    Loader{
                        active: surfaceData.rootViewIndex == 0 && dataShowCore.telescopedJointView
                        SplitView.fillWidth: true
                        SplitView.preferredHeight: 240
                        asynchronous: true
                        visible: dataShowCore.telescopedJointView && dataShowCore.chartShowType==0
                        sourceComponent:
                            RowLayout{
                            Layout.fillWidth: true
                            DataShowItemSelectView{
                                Layout.fillHeight: true
                            }
                            DataShowItemCharts{  //  charts
                                clip: true
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                            }


                        }

                    }



                    Loader{
                        active: surfaceData.rootViewIndex == 0
                        SplitView.fillWidth: true
                        SplitView.fillHeight: true
                        asynchronous: true
                        sourceComponent:
                            ColumnLayout{
                            SplitView.fillWidth: true
                            SplitView.fillHeight: true
                            DataShowItemHead{
                                Layout.fillWidth: true
                            }
                            DataShowRootView{   // 2D  data
                                Layout.fillWidth: true
                                Layout.fillHeight:true
                        }
                        }

                    }
                    ShowViewListView{
                        visible: dataShowCore.viewRendererListView
                        implicitHeight: 100
                        SplitView.fillWidth: true
                    }

                    MaxMinValueShow{
                        id:showViewListView
                        visible: dataShowCore.viewRendererMaxMinValue
                        implicitHeight: 40
                        SplitView.fillWidth: true
                    }

                }
                DataShowItemFoot{
                    Layout.fillWidth: true
                     SplitView.fillWidth: true
                      SplitView.maximumHeight: 25
                      SplitView.preferredHeight: 25
                }
                }

                // DataShowLabelsView{
                //     visible: surfaceData.key=="S"
                //     SplitView.fillHeight: true
                //     SplitView.preferredWidth: 170
                // }
            }
            Loader{
                active: surfaceData.rootViewIndex == 1
                asynchronous: true
                sourceComponent: View3DRoot{
                    anchors.fill: parent
                }
            }
        }

    }
}
