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
    property string editMountpoint: ""

    function initExe(exe){
        editTpye=0
        title_id.text="添加文件夹监听"
        let exeData = monitor.getDefault(exe)
        exe_id.text=exeData.source
        minSize_id.text=exeData.minCount
        del_id.text =exeData.delete_size
        open()
    }

    function editExe(mountpoint, index){
        editTpye=1
        editIndex=index
        editMountpoint=mountpoint
        title_id.text="编辑文件夹监听"
        let exeData = monitor.index(mountpoint, index)
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
                    delete_size:parseInt(del_id.text),
                    delete_type:"%",
                    sort_type: "time",
                    minCount:parseInt(minSize_id.text),
                    monitorAble:true
                }
                if (editTpye==0){
                    monitor.addApp(exeData)
                    initMonitor()
                    root.close()
                }
                else{
                    changeMonitorValue(editMountpoint, editIndex, "source", exeData.source)
                    changeMonitorValue(editMountpoint, editIndex, "delete_size", exeData.delete_size)
                    changeMonitorValue(editMountpoint, editIndex, "minCount", exeData.minCount)
                    changeMonitorValue(editMountpoint, editIndex, "sort_type", exeData.sort_type)
                    changeMonitorValue(editMountpoint, editIndex, "monitorAble", true)
                    initMonitor()
                }
                root.close()

            }
        }
        }

    }
    }
}
