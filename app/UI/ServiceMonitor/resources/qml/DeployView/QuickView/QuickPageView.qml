import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
// 快速的流程图
ScrollView {
    id:root
    width:parent.width
    height:parent.height
    contentHeight: col.height
    contentWidth: col.width
    ScrollBar.vertical: ScrollBar{
        anchors.right: parent.right
        height: parent.height
    }
    Column{
        id:col
        width: root.width

        // 1.开始
        ItemDelegateBase{
            cmd:"control powercfg.cpl"
            title: "打开电源选项设置 - 更改电源高性能 "
        }

        ItemDelegateBase{
            cmd:"powercfg -change -monitor-timeout-ac 0"
            title: "电源选项设置 - 不休眠 "
        }

        ItemDelegateBase{
            cmd:"control firewall.cpl"
            title: "防火墙 - 防火墙设置"
        }

        ItemDelegateBase{
            cmd:"netsh advfirewall set allprofiles state off"
            title: "防火墙 - 关闭防火墙"
        }

        ItemDelegateBase{
            cmd:"control /name Microsoft.NetworkAndSharingCenter"
            title: "网络和共享中心"
        }

        ItemDelegateBase{
            cmd:"ncpa.cpl"
            title: "网络适配器"
        }

        ItemDelegateBase{
            cmd:"control userpasswords2"
            title: "账户设置"
        }

        ItemDelegateBase{
            cmd:"explorer.exe ms-settings:remotedesktop"
            title: "远程桌面设置"
        }
        ItemDelegateBase{
            cmd:"mstsc"
            title: "远程桌面"
        }

        ItemDelegateBase{
            cmd:"devmgmt.msc"
            title: "设备管理器"
        }
        ItemDelegateBase{
            cmd:"services.msc"
            title: "打开服务"
        }

        ItemDelegateBase{
            cmd:"appwiz.cpl"
            title: "卸载程序"
        }
        ItemDelegateBase{
            cmd:"netplwiz"
            title: "自动登录设置"
        }
        ItemDelegateBase{
            cmd:"regedit"
            title: "注册表"
        }
       }


}

