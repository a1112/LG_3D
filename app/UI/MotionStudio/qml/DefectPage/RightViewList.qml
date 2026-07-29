/*
功能列表
    // 数据统计
    // 缺陷统计
    // 查询

*/
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "Alarm"
import "HistoryView"
import "DefectInfo"
import "../Pages/Card"
import "../Pages/AlarmPage"
import "../Pages/AlarmPage/AlarmItemSimple"
import "../Pages/AlarmPage/AlarmCheckInfo"
import "../Pages/LeftPage/DataList"
import "../Pages/LeftPage/SearchView"
import "../Pages/LeftPage/FliterSelect"
import "../Pages/LeftPage"
SplitView{
      SplitView.preferredWidth: adaptive.scaleMetric(400, 320, 520)
       SplitView.fillHeight: true
       orientation: Qt.Vertical
       DefectInfoView{
       }
       DefectClassInfoView{
       }

       SearchView{ // 查询界面
           visible: leftCore.searchViewShow
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
       }

       FootView{
           apiClient: api
           style: coreStyle
           model: coreModel
           popupManager: popManage
           SplitView.fillWidth: true
           SplitView.preferredHeight: adaptive.scaleMetric(25, 22, 34)
       }

      // Item{
      //     Layout.fillWidth: true
      //     Layout.fillHeight: true
      //     ListTabelView{}
      // }

  }
