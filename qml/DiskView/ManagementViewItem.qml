import QtQuick 2.15
import QtQuick.Layouts
import QtQuick.Controls.Material



Column{
    width: parent.width
    id:root

    Timer{
        interval: 2000
        repeat: true
        running: true
        onTriggered: {

        }
    }

    property var test: {'C:\\':
        {'mountpoint':
            'C:\\', 'fstype': 'NTFS', 'opts': 'rw,fixed',
            'total': 499.21483993530273,
            'used': 438.9631118774414,
            'free': 60.25172805786133,
            'percentage': 87.9},
        'D:\\':
        {'mountpoint': 'D:\\',
            'fstype': 'NTFS', 'opts': 'rw,fixed',
            'total': 615.8222885131836, 'used': 585.1667861938477,
            'free': 30.655502319335938, 'percentage': 95.0},
        'E:\\': {'mountpoint': 'E:\\',
            'fstype': 'NTFS', 'opts': 'rw,fixed',
            'total': 651.2007751464844, 'used': 394.9775085449219,
            'free': 256.2232666015625, 'percentage': 60.7},
        'F:\\': {'mountpoint': 'F:\\',
            'fstype': 'NTFS', 'opts': 'rw,fixed',
            'total': 1767.4425163269043, 'used': 896.3971748352051,
            'free': 871.0453414916992, 'percentage': 50.7},
        'Z:\\': {'mountpoint': 'Z:\\', 'fstype': 'NTFS',
            'opts': 'rw,remote', 'total': 37538.880001068115,
            'used': 9315.246002197266, 'free': 28223.63399887085,
            'percentage': 24.8}}
    property int item_state: percentage>threshold?0:1


    ItemDelegate {
    width: parent.width
    height: 45
    spacing: 40
    Frame{
        anchors.fill: parent
    }
    RowLayout{
        anchors.fill: parent
        Item{
            width: 10
            height: 1
        }
        DiskItemRec{
            anchors.verticalCenter: parent.verticalCenter
        }
        Row{
            anchors.verticalCenter: parent.verticalCenter
            height: 30
            Label{
                text: "清理阈值"
                font.bold: true
                font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
            }
        SpinBox {
            anchors.verticalCenter: parent.verticalCenter
            from:0
            to:100
            width: 100
            height: parent.height
            value: threshold
            onValueChanged: {
            threshold = value
            changeValue(index,"threshold",value)
            }
        }
        Label{
            text: "%"
            font.bold: true
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
        }
        }
            Row{
                spacing: 0
                anchors.verticalCenter: parent.verticalCenter
                width: 100
                Label {
                    text: stateDict[item_state].text
                    font.pointSize: 13
                    font.bold: true
                    color: stateDict[item_state].color
                }
            }
        Label{
            anchors.verticalCenter: parent.verticalCenter
            text: index
        }
    }
}
    DiskMonItem{

    }
}
