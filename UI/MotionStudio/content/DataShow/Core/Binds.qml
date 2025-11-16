import QtQuick
import "../../Core/Surface"
/*


*/
//绑定切换工具

Item {
    property SurfaceData surfaceData
    property AdjustConfig adjustConfig:AdjustConfig{}       // 调节功能
    property TopDataManage topDataManage:TopDataManage{}    // 数据显示切换

    property DefectManage defectManage: DefectManage{}      // 缺陷显示管理功能

}

