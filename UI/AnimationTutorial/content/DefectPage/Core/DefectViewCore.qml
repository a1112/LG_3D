import QtQuick
// 主要的 缺陷 Core
import "../../Model/server"
Item {
    property DefectClassItemModel globalDefectClassItemModel : DefectClassItemModel{}

    property FilterCore filterCore : FilterCore{}

    property DefectCoreModel defectCoreModel : DefectCoreModel{}  //  模型数据

    property ControlCore controlCore : ControlCore{}
}
