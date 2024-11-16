import QtQuick 2.15

Item {
        property bool cacheAbel: coreSetting.useImageCache
    property int maxCache: coreSetting.maxImageCache


    function pushCache(source) {

        if(!cacheAbel) {
            return
        }

        if(cacheModel.count >= maxCache) {
            cacheModel.remove(0)
        }
        cacheModel.append({"cacheSource":source})
    }

    Repeater {
        model: ListModel{
                id:cacheModel
        }
        Image {
            cache: true
            asynchronous: true
            id: name
            source: cacheSource
        }
    }

}
