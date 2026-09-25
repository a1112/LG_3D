.pragma library

function parse(value, fallbackValue, context) {
    if (value === undefined || value === null || value === "") {
        return fallbackValue
    }
    if (typeof value !== "string") {
        return value
    }
    try {
        return JSON.parse(value)
    } catch (error) {
        console.warn((context || "JSON") + " parse failed:", error)
        return fallbackValue
    }
}
