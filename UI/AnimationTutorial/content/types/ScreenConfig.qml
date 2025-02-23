import QtQuick
import QtQuick.Window

QtObject {

    property int width :Screen.width

    property int height :Screen.height

    // 获取屏幕的可用宽度（不包括任务栏等系统保留区域）
    property int desktopAvailableWidth: Screen.desktopAvailableWidth

    // 获取屏幕的可用高度（不包括任务栏等系统保留区域）
    property int desktopAvailableHeight: Screen.desktopAvailableHeight

    // 获取屏幕的总宽度（包括任务栏等系统保留区域）
    property int screenWidth: Screen.width

    // 获取屏幕的总高度（包括任务栏等系统保留区域）
    property int screenHeight: Screen.height

    // 获取屏幕的逻辑像素密度（每英寸像素数）
    property real pixelDensity: Screen.pixelDensity

    // 获取屏幕的设备像素比（通常用于高DPI屏幕）
    property real devicePixelRatio: Screen.devicePixelRatio

    // 获取屏幕的名称（例如显示器名称）
    property string screenName: Screen.name

    // 获取屏幕的原始方向（例如 Portrait、Landscape 等）
    property int screenOrientation: Screen.primaryOrientation

    // 打印屏幕信息（调试用）
    Component.onCompleted: {
        console.log("Available Width:", desktopAvailableWidth);
        console.log("Available Height:", desktopAvailableHeight);
        console.log("Screen Width:", screenWidth);
        console.log("Screen Height:", screenHeight);
        console.log("Pixel Density:", pixelDensity);
        console.log("Device Pixel Ratio:", devicePixelRatio);
        console.log("Screen Name:", screenName);
        console.log("Screen Orientation:", screenOrientation);
    }
}
