import QtQuick

Item {
    id: root

    required property var apiClient
    required property var model
    required property var appContext

    property bool loading: false
    property bool loaded: false
    property int generation: 0
    property int pendingRequests: 0
    property string lastError: ""

    signal refreshed()

    function _beginRequest() {
        pendingRequests += 1
    }

    function _finishRequest(requestGeneration, errorMessage) {
        if (requestGeneration !== generation) {
            return
        }
        if (errorMessage) {
            lastError = errorMessage
        }
        pendingRequests = Math.max(0, pendingRequests - 1)
        if (pendingRequests === 0) {
            loading = false
            loaded = true
            refreshed()
        }
    }

    function _parseObject(result, requestName) {
        try {
            var parsed = JSON.parse(result)
            return parsed && typeof parsed === "object" ? parsed : {}
        } catch (error) {
            lastError = requestName + ": " + error
            return null
        }
    }

    function _applyAppInfo(data) {
        if (!data) {
            return
        }
        model.errorMap = data.ErrorMap || {}
        model.rendererList = data.RendererList || []
        model.colorMaps = data.ColorMaps || {}
        model.saveImageType = data.SaveImageType || "png"
        model.previewSize = data.PreviewSize || [512, 512]
        model.surfaceS.initData(data.surfaceS || {})
        model.surfaceL.initData(data.surfaceL || {})

        if (!appContext || !appContext.coreInfo) {
            return
        }
        var surfaceS = data.surfaceS || {}
        var surfaceL = data.surfaceL || {}
        appContext.coreInfo.saveImageFolderS = surfaceS.saveFolder || ""
        appContext.coreInfo.saveImageFolderL = surfaceL.saveFolder || ""
        appContext.coreInfo.originalImageFolderS = _joinSources(surfaceS)
        appContext.coreInfo.originalImageFolderL = _joinSources(surfaceL)
    }

    function _joinSources(surface) {
        if (!surface || !Array.isArray(surface.folderList)) {
            return ""
        }
        var sources = []
        for (var index = 0; index < surface.folderList.length; index++) {
            var item = surface.folderList[index]
            if (item && item.source) {
                sources.push(item.source)
            }
        }
        return sources.join("\n")
    }

    function refresh(force) {
        if (loading || (loaded && !force)) {
            return false
        }

        generation += 1
        var requestGeneration = generation
        loading = true
        loaded = false
        lastError = ""
        pendingRequests = 4

        apiClient.getInfo(function(result) {
            var data = _parseObject(result, "app info")
            if (data) {
                _applyAppInfo(data)
            }
            _finishRequest(requestGeneration, data ? "" : lastError)
        }, function(error) {
            _finishRequest(requestGeneration, "app info: " + error)
        })

        apiClient.getRuntimeInfo(function(result) {
            var data = _parseObject(result, "runtime info")
            if (data && appContext && appContext.coreInfo) {
                appContext.coreInfo.pythonVersion = data.python_version || ""
                appContext.coreInfo.cacheMode = data.cache_mode || ""
                appContext.coreInfo.cpuModel = data.cpu_model || ""
                appContext.coreInfo.gpuModels = Array.isArray(data.gpus) ? data.gpus.join("\n") : ""
            }
            _finishRequest(requestGeneration, data ? "" : lastError)
        }, function(error) {
            _finishRequest(requestGeneration, "runtime info: " + error)
        })

        apiClient.getDatabaseInfo(function(result) {
            var data = _parseObject(result, "database info")
            if (data && appContext && appContext.coreInfo) {
                appContext.coreInfo.databaseUrl = data.url || ""
            }
            _finishRequest(requestGeneration, data ? "" : lastError)
        }, function(error) {
            _finishRequest(requestGeneration, "database info: " + error)
        })

        apiClient.getServerVersion(function(result) {
            if (appContext && appContext.coreInfo) {
                appContext.coreInfo.serverVersion = String(result || "")
            }
            _finishRequest(requestGeneration, "")
        }, function(error) {
            _finishRequest(requestGeneration, "server version: " + error)
        })
        return true
    }
}
