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
            backupDataView.popup()
        }
    }
    MenuItem{
        text: "重新识别"
        onClicked: {
            reDetectonView.popup()
        }
    }

}
