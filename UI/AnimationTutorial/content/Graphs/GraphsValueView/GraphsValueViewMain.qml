import QtQuick
import QtQuick.Controls
        import QtQuick.Layouts
import "../GraphsBase"
ApplicationWindow {
        visible: false
        width: 800
        height: 600
        title: qsTr("数据曲线")

        ColumnLayout{

        HeaderView{

        }

        GraphsBaseView{
                Layout.fillWidth: true
                Layout.fillHeight: true
        }
}

}
