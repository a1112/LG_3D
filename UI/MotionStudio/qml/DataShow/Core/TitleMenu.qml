import QtQuick
import QtQuick.Controls
import "../../Controls/Menu"
Menu {
    SwitchMenuItem{
        selectd:control.lockControl
        text:control.lockControl?"取消锁定": "锁定"
        onSelectdChanged:{
            control.lockControl=selectd
        }
    }
    Menu{
        enabled:false
        title:"布局"
        MenuItem{
            text:"上下布局"
        }
        MenuItem{
            text:"左右布局"
        }
    }


}
