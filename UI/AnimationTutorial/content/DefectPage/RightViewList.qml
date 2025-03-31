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
SplitView{
      SplitView.preferredWidth: 400
       SplitView.fillHeight: true
       orientation: Qt.Vertical
       DefectInfoView{
       }
       DefectClassInfoView{
       }

      AlarmButtons{
          Layout.fillWidth: true
          implicitHeight: 150
      }

      Item{
          Layout.fillWidth: true
          Layout.fillHeight: true
          ListTabelView{}
      }

  }
