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
        title_id.text="添加监听程序"
        let exeData = monitor.getDefault(exe)
        name_id.text=exeData.name
        exe_id.text=exeData.exe
        args_id.text=exeData.args
        delay_id.text=exeData.delay
        exeData.monitorAble
        open()
    }

    function editExe(index){
        editTpye=1
        editIndex=index
        title_id.text="编辑监听程序"
        let exeData = monitor.index(index)
        name_id.text=exeData.name
        exe_id.text=exeData.exe
        args_id.text=exeData.args
        delay_id.text=exeData.delay
        open()
    }

    ColumnLayout{
        anchors.fill: parent
        Label{
            id:title_id
            Layout.alignment: Qt.AlignHCenter
            text: "添加监听程序"
            font.pixelSize: 22
            font.bold: true
            Material.foreground: Material.Blue
        }
            Column{
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                AddItem{
                    id:name_id
                    title: "名称"
                    placeholderText:"被监听程描述"
                }
                AddItem{
                    id:exe_id
                    title:"完整路径"
                placeholderText:"EXE 文件的完整路径"
                }
                AddItem{
                    id:args_id
                    title:"运行参数"
                    placeholderText:"启动 EXE 的 额外参数"
                }
                AddItem{
                    id:delay_id
                    title:"延时"
                    placeholderText:"延时启动时间(秒)"
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
                    name:name_id.text,
                    exe:exe_id.text,
                    args:args_id.text,
                    delay:delay_id.text,
                    monitorAble:true
                }

                if (editTpye==0){
                    monitor.addApp(exeData)
                    appModel.append(exeData)
                    root.close()

                }
                else{
                    changeValue(editIndex,"name",exeData.name)
                    changeValue(editIndex,"exe",exeData.exe)
                    changeValue(editIndex,"args",exeData.args)
                    changeValue(editIndex,"delay",exeData.delay)
                    changeValue(editIndex,"monitorAble",true)

                    appModel.setProperty(editIndex,"name",exeData.name)
                    appModel.setProperty(editIndex,"exe",exeData.exe)
                    appModel.setProperty(editIndex,"args",exeData.args)
                    appModel.setProperty(editIndex,"delay",exeData.delay)
                    appModel.setProperty(editIndex,"monitorAble",true)

                }
                root.close()

            }
        }
        }

    }
    }
}
