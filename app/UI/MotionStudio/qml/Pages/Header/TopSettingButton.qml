
import "../../btns"
SettingButton{
    id: root

    required property var style
    required property var popupManager

    height: root.style.topHeight
    width: height
    source: root.style.getIcon("setting")
    onClicked: root.popupManager.openSettingPageView()
}
