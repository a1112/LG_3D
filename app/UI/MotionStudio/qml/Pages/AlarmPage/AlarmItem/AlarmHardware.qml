import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    id:root
    property int alarmLevel: 0
    property var hardwareData:t
    property var t : {"cpu":{"key":"芯片","value":"1.4%","msg":"CPU 使用率: 1.4%"},
    "memory":{"key":"内存","value":"44.2%","msg":"内存使用率: 44.2%, 可用内存: 22754.19 MB"},
    "disk":{"key":"硬盘","value":"81.96547127091024%",
    "msg":"分区: C:\\, 总大小: 264.14 GB, 已用: 213.98 GB, 可用: 50.16 GB, 使用率: 81.0%\n分区: D:\\, 总大小: 133.03 GB, 已用: 114.51 GB, 可用: 18.52 GB, 使用率: 86.1%\n分区: E:\\, 总大小: 100.00 GB, 已用: 79.30 GB, 可用: 20.71 GB, 使用率: 79.3%\n分区: F:\\, 总大小: 182.77 GB, 已用: 174.36 GB, 可用: 8.40 GB, 使用率: 95.4%\n分区: G:\\, 总大小: 171.56 GB, 已用: 140.59 GB, 可用: 30.97 GB, 使用率: 82.0%\n分区: I:\\, 总大小: 27.37 GB, 已用: 8.75 GB, 可用: 18.62 GB, 使用率: 32.0%\n分区: P:\\, 总大小: 40.91 GB, 已用: 24.24 GB, 可用: 16.67 GB, 使用率: 59.3%\n分区: S:\\, 总大小: 11.20 GB, 已用: 7.35 GB, 可用: 3.85 GB, 使用率: 65.6%"},
  "gpu":{"key":"显卡","value":"13.0%","msg":"显卡: NVIDIA GeForce RTX 3070 Laptop GPU, 使用率: 13.00%"}}
    ListModel{
        id:hardwareModel

    }
    Timer{
        id:getHardwareTimer
        running:root.visible
        repeat:true
        interval: 2000
        onTriggered:{
            api.getHardware(
                        (res)=>{
                            hardwareData=JSON.parse(res)
                            // hardwareModel.clear()
                            let i=0
                            for(var key in hardwareData){
                                hardwareModel.set(i,hardwareData[key])
                                i++
                            }
                        },
                        (err)=>{
                        }
                        )
        }
    }

    ColumnLayout{
    anchors.fill: parent
    Label{
        text:"服务器状态"
        font.pointSize: 15
        font.bold: true
        color: Material.color(Material.Blue)
        font.family: "Microsoft YaHei"
        Layout.alignment: Qt.AlignHCenter

    }
    Item{
        id:body
        Layout.fillWidth: true
        Layout.fillHeight: true
    GridView{
        anchors.fill: parent
        model: hardwareModel
        cellWidth: parent.width / 2-1
        cellHeight: parent.height/2
        delegate: AlarmItemHardwareItem {
        width: body.width / 2-1
        height:body.height/2
        titleText: key
        valueText: value
        msg_:msg
        }
    }
    }
}

}
