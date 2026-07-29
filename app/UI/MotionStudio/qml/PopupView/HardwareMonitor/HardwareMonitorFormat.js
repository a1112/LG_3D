.pragma library

function numberValue(value) {
    var result = Number(value)
    return isFinite(result) ? result : 0
}

function formatAge(value) {
    if (value === undefined || value === null) {
        return "-"
    }
    var age = Number(value)
    return isFinite(age) ? age.toFixed(1) + " s" : "-"
}

function formatRate(value) {
    var bytes = numberValue(value)
    if (bytes >= 1073741824) {
        return (bytes / 1073741824).toFixed(1) + " GB/s"
    }
    if (bytes >= 1048576) {
        return (bytes / 1048576).toFixed(1) + " MB/s"
    }
    if (bytes >= 1024) {
        return (bytes / 1024).toFixed(1) + " KB/s"
    }
    return bytes.toFixed(0) + " B/s"
}

function formatBytes(value) {
    var bytes = numberValue(value)
    if (bytes >= 1073741824) {
        return (bytes / 1073741824).toFixed(1) + " GB"
    }
    if (bytes >= 1048576) {
        return (bytes / 1048576).toFixed(0) + " MB"
    }
    if (bytes >= 1024) {
        return (bytes / 1024).toFixed(0) + " KB"
    }
    return bytes.toFixed(0) + " B"
}

function formatDuration(value) {
    var seconds = Math.max(numberValue(value), 0)
    var days = Math.floor(seconds / 86400)
    var hours = Math.floor((seconds % 86400) / 3600)
    var minutes = Math.floor((seconds % 3600) / 60)
    if (days > 0) {
        return days + "天 " + hours + "小时"
    }
    if (hours > 0) {
        return hours + "小时 " + minutes + "分"
    }
    return minutes + "分"
}

function formatTemperature(available, value, stale) {
    if (!available || value === null || value === undefined) {
        return "-- °C"
    }
    return Number(value).toFixed(1) + " °C" + (stale ? " 旧" : "")
}

function temperatureAvailabilityText(error) {
    if (!error) {
        return ""
    }
    if (error.indexOf("0x80000106") >= 0
            || error.indexOf("0x80000100") >= 0) {
        return "设备未提供可读温度节点"
    }
    return error
}

function networkControlReason(reason) {
    if (reason === "loopback adapter cannot be controlled") {
        return "回环网卡不可控制"
    }
    if (reason === "network adapter control is only supported on Windows") {
        return "仅 Windows 支持网卡控制"
    }
    return reason
}

function temperatureColor(style, available, value, stale) {
    if (!available || stale) {
        return style.statusInactiveColor
    }
    var temperature = numberValue(value)
    if (temperature >= 70) {
        return style.statusErrorColor
    }
    if (temperature >= 55) {
        return style.statusWarningColor
    }
    return style.statusSuccessColor
}
