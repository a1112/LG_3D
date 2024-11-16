

CoreModel_Data {
    // 使用jpg 加载图像
    property bool quickLyImage: true
    // 保持最新图像
    property bool keepLatest: true
    // 保持最新图像 -> 有数据
    property bool keepLatestHasData:true

    // 保持最新图像 -> 最大时间
    property int autoKeepTimeMax : coreSetting.autoKeepTimeMax
    // 保持最新图像 -> 当前时间
    property int autoKeepTime: 0
    // 设置 刷新计时器
    function setKeepLatest(value){
        autoKeepTime = 0
        keepLatest = value
    }
    // 记录缺陷显示
    property var defectDictAll: {return {}}
    function flushDefectDictAll(){
    let temp = defectDictAll
        defectDictAll = {}
        defectDictAll = temp
    }

}
