import QtQuick

Item {
    id: root

    property var requestLogger: null
    property int requestTimeoutMs: 12000
    property int activeRequestCount: 0
    readonly property bool busy: activeRequestCount > 0

    signal requestStarted(string method, string url)
    signal requestFinished(string method, string url, int status)

    Component {
        id: requestTimeoutTimerComponent

        Timer {
            repeat: false
        }
    }

    function logRequest(url, method) {
        if (root.requestLogger
                && typeof root.requestLogger.appendUrl === "function") {
            root.requestLogger.appendUrl(url, method)
        }
    }

    function sendRequest(method, url, data, success, failure) {
        let xhr = new XMLHttpRequest()
        let finished = false
        let timeoutTimer = requestTimeoutTimerComponent.createObject(root, {
            "interval": root.requestTimeoutMs
        })

        function destroyTimeoutTimer() {
            if (!timeoutTimer) {
                return
            }
            timeoutTimer.stop()
            timeoutTimer.destroy()
            timeoutTimer = null
        }

        function finish(status) {
            if (finished) {
                return false
            }
            finished = true
            destroyTimeoutTimer()
            root.activeRequestCount = Math.max(0, root.activeRequestCount - 1)
            root.requestFinished(method, url, status)
            return true
        }

        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE || finished) {
                return
            }
            if (finish(xhr.status)) {
                root.handleResponse(xhr, success, failure)
            }
        }

        root.activeRequestCount += 1
        root.requestStarted(method, url)
        try {
            xhr.open(method, url)
        } catch (error) {
            finish(0)
            if (typeof failure === "function") {
                failure(String(error), 0)
            }
            return null
        }

        if (method === "POST" || method === "PUT" || method === "PATCH") {
            xhr.withCredentials = true
            xhr.setRequestHeader("Content-Type", "application/json")
        }

        timeoutTimer.triggered.connect(function() {
            if (!finish(0)) {
                return
            }
            xhr.abort()
            if (typeof failure === "function") {
                failure("request timeout", 0)
            }
        })
        timeoutTimer.start()
        xhr.send(data)
        return xhr
    }

    function get(url, success, failure) {
        root.logRequest(url, "get")
        return root.sendRequest("GET", url, null, success, failure)
    }

    function post(url, arg, success, failure) {
        root.logRequest(url, "post")
        return root.sendRequest("POST", url, JSON.stringify(arg), success, failure)
    }

    function put(url, arg, success, failure) {
        root.logRequest(url, "put")
        return sendRequest("PUT", url, JSON.stringify(arg), success, failure)
    }

    function delete_(url, success, failure) {
        root.logRequest(url, "delete")
        return sendRequest("DELETE", url, null, success, failure)
    }

    function handleResponse(xhr, success, failure) {
        if (xhr.status >= 200 && xhr.status < 300) {
            if (typeof success === "function") {
                success(xhr.responseText)
            }
            return
        }
        if (typeof failure === "function") {
            failure(xhr.responseText, xhr.status)
        }
    }
}
