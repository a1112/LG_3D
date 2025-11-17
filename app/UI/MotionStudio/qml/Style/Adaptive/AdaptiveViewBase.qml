import QtQuick
import "../../Base"
Item {
    id:root
    property string adaptive_name:""
    property int mask_tool_width :220

    SettingsBase{
        category:"adaptive_"+root.adaptive_name

    }

}
