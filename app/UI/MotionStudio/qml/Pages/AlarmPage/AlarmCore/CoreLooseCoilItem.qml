import QtQuick

Item {

    property string global_key:""

    property real scaleX: 1.0
    property real scaleY: 1.0
    property real max_width_raw: 0.0
    readonly property real max_width: max_width_raw
    property bool hasData:false

    function numberValue(value, defaultValue) {
        if (value === undefined || value === null) {
            return defaultValue
        }
        let numberValue_ = Number(value)
        return isFinite(numberValue_) ? numberValue_ : defaultValue
    }

    function parseLooseData(value) {
        if (!value || typeof value !== "string") {
            return ({})
        }
        try {
            return JSON.parse(value)
        } catch (e) {
            return ({})
        }
    }

    function widthScale() {
        let xScale = Number(scaleX)
        if (isFinite(xScale) && xScale > 0) {
            return xScale
        }
        let yScale = Number(scaleY)
        if (isFinite(yScale) && yScale > 0) {
            return yScale
        }
        return 1.0
    }

    function widthFromPixel(pixelWidth) {
        return numberValue(pixelWidth, 0) * widthScale()
    }

    function itemMaxWidthMm(item) {
        let rawWidth = numberValue(item.max_width, 0)
        let detail = parseLooseData(item.data)
        let pixelWidth = numberValue(detail.max_width_px, 0)
        if (detail.max_width_unit === "px") {
            return widthFromPixel(pixelWidth > 0 ? pixelWidth : rawWidth)
        }
        if (detail.max_width_mm !== undefined && detail.max_width_mm !== null) {
            let storedMm = numberValue(detail.max_width_mm, rawWidth)
            if (detail.max_width_scale_axis === "x") {
                return storedMm
            }
            if (pixelWidth > 100 && Math.abs(storedMm - pixelWidth) < 0.001) {
                return widthFromPixel(pixelWidth)
            }
            return storedMm
        }
        if (detail.max_width_unit === "mm") {
            return rawWidth
        }
        return rawWidth > 100 ? widthFromPixel(rawWidth) : rawWidth
    }

    function init(){
        hasData=false
        max_width_raw=0
    }


    property var data
    onDataChanged:{
        init()
        if (Array.isArray(data) && data.length > 0){
            data.forEach((item)=>{
                             let itemWidth = itemMaxWidthMm(item)
                             if (itemWidth>max_width_raw){
                                 max_width_raw=itemWidth
                             }
                         }
                         )
            hasData=max_width_raw > 0
        }
        else{
            hasData=false
        }
    }
}
