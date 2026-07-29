/*
功能列表
    // 数据统计
    // 缺陷统计
    // 查询

*/
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "DefectInfo"
import "../Pages/LeftPage/DataList"
import "../Pages/LeftPage/SearchView"
import "../Pages/LeftPage"
SplitView{
      id: root
      required property var adaptiveMetrics
      required property var defectController
      required property var style
      required property var leftController
      required property var apiClient
      required property var modelController
      required property var popupManager
      required property var coreController

      SplitView.preferredWidth: root.adaptiveMetrics.scaleMetric(400, 320, 520)
       SplitView.fillHeight: true
       orientation: Qt.Vertical
       DefectInfoView{
       }
       DefectClassInfoView{
           viewController: root.defectController
           style: root.style
       }

       SearchView{ // 查询界面
           visible: root.leftController.searchViewShow
           adaptiveMetrics: root.adaptiveMetrics
           style: root.style
           leftController: root.leftController
           Layout.fillWidth: true
           SplitView.fillWidth: true
       }

       // FliterSelectView{

       // }

       DataListView{   // 左侧列表
           SplitView.fillWidth : true
           SplitView.fillHeight : true
           showFilterIcon : false
           id : dataList
           Layout.fillWidth : true
           Layout.fillHeight : true
           style: root.style
           coreController: root.coreController
           modelController: root.modelController
           leftController: root.leftController
           popupManager: root.popupManager
       }

       FootView{
           apiClient: root.apiClient
           style: root.style
           model: root.modelController
           popupManager: root.popupManager
           SplitView.fillWidth: true
           SplitView.preferredHeight: root.adaptiveMetrics.scaleMetric(25, 22, 34)
       }

      // Item{
      //     Layout.fillWidth: true
      //     Layout.fillHeight: true
      //     ListTabelView{}
      // }

  }
