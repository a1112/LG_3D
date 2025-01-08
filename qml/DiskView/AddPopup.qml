import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Popup {
    id:root
    anchors.centerIn: parent
    width: 400
    height: 300
    dim:true

    property int editTpye: 0
    property int editIndex: 0

    function initExe(exe){
        editTpye=0
        title_id.text="添加文件夹监听"
        let exeData = monitor.getDefault(exe)
        exe_id.text=exeData.source
        minSize_id.text=exeData.minCount
        del_id.text =exeData.delete_size
        open()
    }

    function editExe(index){
        editTpye=1
        editIndex=index
        title_id.text="编辑文件夹监听"
        let exeData = monitor.index(index)
        exe_id.text=exeData.source
        minSize_id.text=exeData.minCount
        del_id.text =exeData.delete_size
        open()
    }

    ColumnLayout{
        anchors.fill: parent
        Label{
            id:title_id
            Layout.alignment: Qt.AlignHCenter
            text: ""
            font.pixelSize: 22
            font.bold: true
            Material.foreground: Material.Blue
        }
            Column{
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                AddItem{
                    id:exe_id
                    title:"路径"
                placeholderText:"EXE 文件的完整路径"
                }
                AddItem{
                    id:minSize_id
                    title:"最小保留"
                    placeholderText:"最小保留数量"
                }
                AddItem{
                    id:del_id
                    title:"删除比例"
                    placeholderText:"删除比例%"
                }
            }
        Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
        }
    Item{
        Layout.fillWidth: true
        height: 40
        Row{
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        Button{
            text: "取消"
            onClicked: root.close()
        }
        Button{
            text: "提交"
            Material.foreground: Material.Blue
            onClicked: {
                let exeData = {
                    source:exe_id.text,
                    del_size:del_id.text,
                    sort: "time",
                    monitorAble:true
                }
                if (editTpye==0){
                    monitor.addApp(exeData)
                    appModel.set(editIndex, exeData)
                    root.close()
                }
                else{
                    changeValue(editIndex,"args",exeData.args)
                    changeValue(editIndex,"monitorAble",true)
                    appModel.setProperty(editIndex,"monitorAble",true)
                }
                root.close()

            }
        }
        }

    }
    }
}
