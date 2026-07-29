import QtQuick

Item {
    id: root

    required property var model

    property bool hasError: false
    property int errorCode: -1
    property string errorStr: ""
    property bool hasGlobalError: false
    property var errorLevelDict: ({})
    property var errorState: ({})
    property var errorDict: ({})

    function flushLevel() {
        let newLevels = {}
        let anyError = false
        let state = errorState || {}
        for (let group in state) {
            let groupLevel = 0
            let groupState = state[group] || {}
            for (let key in groupState) {
                groupLevel = Math.max(groupLevel, Number(groupState[key]) || 0)
            }
            newLevels[group] = groupLevel
            anyError = anyError || groupLevel > 0
        }
        errorLevelDict = newLevels
        hasGlobalError = anyError
    }

    function setStateLevel(group, key, level) {
        let state = errorState || {}
        let groupState = Object.assign({}, state[group] || {})
        groupState[key] = Math.max(0, Number(level) || 0)
        state[group] = groupState
        errorState = Object.assign({}, state)
        flushLevel()
    }

    function refreshPrimaryError() {
        let activeCode = -1
        let activeMessage = ""
        for (let code in errorDict) {
            let item = errorDict[code]
            if (item && item.hasError) {
                activeCode = Number(code)
                activeMessage = item.str || ""
                break
            }
        }
        errorCode = activeCode
        errorStr = activeMessage
        hasError = activeCode >= 0
    }

    function setError(code, hasErrorValue) {
        let message = ""
        if (code === 1001) {
            message = qsTr("数据服务器连接失败！")
        } else if (code === 2001) {
            message = qsTr("检测数据获取失败！")
        }
        _setGlobalError(code, message, hasErrorValue)
    }

    function _setGlobalError(code, message, hasErrorValue) {
        let errors = errorDict || {}
        errors[String(code)] = {
            code: code,
            str: message || "",
            hasError: Boolean(hasErrorValue)
        }
        errorDict = Object.assign({}, errors)
        refreshPrimaryError()
    }

    Component.onCompleted: {
        let state = {}
        for (let key in model.alarmGlobVis) {
            state[key] = {}
        }
        for (let key in model.alarmVis) {
            state[key] = {}
        }
        errorState = state
        flushLevel()
    }
}
