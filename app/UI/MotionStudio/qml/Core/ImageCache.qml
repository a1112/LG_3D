pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root

    required property var settings
    readonly property bool cacheEnabled: settings.useImageCache
    readonly property int maxCache: Math.max(0, Number(settings.maxImageCache) || 0)
    readonly property int count: cacheModel.count

    function indexOfSource(source) {
        for (let index = 0; index < cacheModel.count; ++index) {
            if (cacheModel.get(index).cacheSource === source) {
                return index
            }
        }
        return -1
    }

    function trimCache() {
        if (!cacheEnabled || maxCache <= 0) {
            cacheModel.clear()
            return
        }
        while (cacheModel.count > maxCache) {
            cacheModel.remove(0)
        }
    }

    function pushCache(source) {
        let normalizedSource = String(source || "")
        if (!cacheEnabled || maxCache <= 0 || normalizedSource === "") {
            return false
        }

        let existingIndex = indexOfSource(normalizedSource)
        if (existingIndex >= 0) {
            cacheModel.remove(existingIndex)
        }
        while (cacheModel.count >= maxCache) {
            cacheModel.remove(0)
        }
        cacheModel.append({"cacheSource": normalizedSource})
        return true
    }

    onCacheEnabledChanged: trimCache()
    onMaxCacheChanged: trimCache()

    ListModel {
        id: cacheModel
    }

    Repeater {
        model: cacheModel

        delegate: Image {
            required property string cacheSource
            visible: false
            cache: true
            asynchronous: true
            source: cacheSource
        }
    }
}
