pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
Menu{
    id: root

    required property var defect
    required property var defectClassController

    Repeater{
        model: root.defectClassController.defectDictModel

        DefectSelectMenuItem{
            defect: root.defect
            defectClassController: root.defectClassController
        }
    }
}
