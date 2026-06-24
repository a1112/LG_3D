import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import DiskMonitor 1.0
ItemDelegate {
    width: parent.width
    height: 30
    property string diskMountpoint: ""
    onClicked: {
        Qt.openUrlExternally("file:///"+source)
    }
    PathInfo{
        id: pathInfo
        path: source
    }
    function formatSize(bytes, precision = 2) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
        if (bytes === 0) return '0 B'
        let size = bytes
        let index = 0
        while (size >= 1024 && index < units.length - 1) {
            size /= 1024
            index++
        }
        return `${size.toFixed(precision)} ${units[index]}`
    }
    RowLayout{
        anchors.fill: parent
        anchors.verticalCenter: parent.verticalCenter
        spacing: 20
        Rectangle{
            height: parent.height*0.7
            width: height
            radius: height/2
            anchors.verticalCenter: parent.verticalCenter
            DiskLabelBase{
                text: (index+1)
                anchors.centerIn: parent
            }
            color: "#9575CD"
        }
        DiskLabelBase {
            text: source
            color: pathInfo.exists?px_id.color:"red"
        }
        Row{
            DiskLabelBase {
                id:px_id
                text: "排序"
            }
            ComboBox {
                height: 30
                width: 80
                model: sortEnumText
                currentIndex: sortEnum.indexOf(sort_type)
                font.bold: true
                font.family: "Microsoft YaHei"
                onActivated: {
                    changeMonitorValue(diskMountpoint, index, "sort_type", sortEnum[currentIndex])
                }
            }
        }
        Row{
            DiskLabelBase {
                text: "最小保留 "
            }
            DiskLabelBase {
                text: minCount
                color: "#5252FF"
            }
        }
        // Row{
        //     DiskLabelBase {
        //         text: "最大保留 "
        //     }
        //     DiskLabelBase {
        //         text: "/"
        //         color: "#5252FF"
        //     }
        // }
        Row{
            DiskLabelBase {
                text: "删除比例 "
            }
            DiskLabelBase {
                text: delete_size+"%"
                color: "#52FF52"
            }
        }
        Row{
            DiskLabelBase {
                text: "文件数量 "
                id:content_id_t
            }
            DiskLabelBase {
                text: pathInfo.content
                color: "#00E676"
                font.pixelSize: content_id_t.font.pixelSize+3
            }
        }
        Row{
            DiskLabelBase {
                text: "占用 "
            }
            DiskLabelBase {
                text:formatSize(pathInfo.size)
                color: "#F4511E"
            }
        }
        Row{
            height: parent.height
            CheckDelegate {
                height: parent.height
                text: "监听"
                font.bold: true
                checked: monitorAble
                font.family: "Microsoft YaHei"
                onToggled: {
                    changeMonitorValue(diskMountpoint, index, "monitorAble", checked)
                }
            }
        }

        DiskLabelBase{
        visible: !pathInfo.exists
        text: "⚠不存在"
        }

    }
    Rectangle {
        width: parent.width
        height: 1
        color: Material.color(Material.BlueGrey)
        anchors.bottom: parent.bottom
    }
}

