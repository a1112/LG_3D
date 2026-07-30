import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Input"

Menu {
    id: root

    required property var modelController
    required property var apiClient
    required property var popupManager

    MenuItem{
        text: root.modelController.isListRealModel
              ? qsTr(">历史模式") : qsTr(">实时模式")
        onClicked: {
            root.modelController.switchListModel()

        }
    }
    MenuItem{
        text: "查看数据源"
        onClicked: {
            Qt.openUrlExternally(root.apiClient.getLastUrlByKey("coilList"))
        }
    }

    MenuItem{
        text: "图像备份"
        onClicked: {
           root.popupManager.popupBackupDataView()
        }
    }
    MenuItem{
        text: "全部重新识别"
        onClicked: {
            root.popupManager.popupReDetectionView()
        }
    }

}
