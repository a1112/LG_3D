import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Input"

Menu {

    MenuItem{
        text: coreModel.isListRealModel?">历史模式":">实时模式"
        onClicked: {
            coreModel.switchListModel()

        }
    }
    MenuItem{
        text: "查看数据源"
        onClicked: {
            Qt.openUrlExternally(api.getLastUrlByKey("coilList"))
        }
    }

    MenuItem{
        text: "图像备份"
        onClicked: {
           popManage.popupBackupDataView()
        }
    }
    MenuItem{
        text: "全部重新识别"
        onClicked: {
            popManage.popupReDetectionView()
        }
    }

    MenuItem{
        text: "变化曲线"
        onClicked: {
            popManage.popupListValueChangeView()
        }
    }

}
