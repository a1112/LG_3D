import QtQuick
import QtQuick.Controls
Menu{
    id: defectMenu
    Repeater{
        model : global.defectClassProperty.defectDictModel

        DefectSelectMenuItem{
        }
    }
}
