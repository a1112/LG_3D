import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

GroupBox {
    id: root
    title: qsTr("软件更新")
    Layout.fillWidth: true
    Layout.preferredHeight: content.implicitHeight + 48
    contentHeight: content.implicitHeight

    readonly property int idleState: 0
    readonly property int checkingState: 1
    readonly property int latestState: 2
    readonly property int downloadingState: 3
    readonly property int finishedState: 4
    readonly property int errorState: 5

    property int updateState: idleState
    property real progress: 0
    property string latestVersion: ""
    property string downloadUrl: ""
    property string fileName: ""
    property string releaseNotes: ""
    property string errorText: ""
    property string savePath: ""
    property string statusText: qsTr("未检查")
    property string downloadFolder: defaultDownloadFolder()

    readonly property bool busy: updateState === checkingState || updateState === downloadingState
    readonly property bool hasDownloadUrl: resolvedDownloadUrl().length > 0
    readonly property bool updateAvailable: latestVersion.length > 0 && compareVersions(latestVersion, currentVersion()) > 0

    function stringValue(value) {
        if (value === undefined || value === null) {
            return ""
        }
        return String(value).trim()
    }

    function currentVersion() {
        return stringValue(app && app.coreInfo ? app.coreInfo.serverVersion : "")
    }

    function defaultManifestUrl() {
        return api.apiConfig.serverUrl + "/software_update/manifest"
    }

    function defaultDownloadFolder() {
        let folder = pathFromUrl(StandardPaths.writableLocation(StandardPaths.DownloadLocation))
        if (folder.length > 0) {
            return folder
        }
        return pathFromUrl(StandardPaths.writableLocation(StandardPaths.DesktopLocation))
    }

    function manifestUrl() {
        let url = stringValue(coreSetting.softwareUpdateManifestUrl)
        return url.length > 0 ? url : defaultManifestUrl()
    }

    function resolvedDownloadUrl() {
        let manualUrl = stringValue(coreSetting.softwareUpdatePackageUrl)
        if (manualUrl.length > 0) {
            return manualUrl
        }
        return downloadUrl.length > 0 ? resolveUrl(downloadUrl, manifestUrl()) : ""
    }

    function pathFromUrl(url) {
        let text = stringValue(url)
        if (text.indexOf("file:///") === 0) {
            return decodeURIComponent(text.substring(8))
        }
        if (text.indexOf("file://") === 0) {
            return decodeURIComponent(text.substring(7))
        }
        return text
    }

    function fileUrl(path) {
        let normalized = stringValue(path).replace(/\\/g, "/")
        return normalized.length > 0 ? "file:///" + normalized : ""
    }

    function joinPath(folder, name) {
        let normalizedFolder = stringValue(folder).replace(/\\/g, "/")
        if (normalizedFolder.endsWith("/")) {
            return normalizedFolder + name
        }
        return normalizedFolder + "/" + name
    }

    function sanitizeFileName(name) {
        let text = stringValue(name)
        text = text.substring(Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\")) + 1)
        return text.replace(/[\\/:*?"<>|]/g, "_")
    }

    function fileNameFromUrl(url) {
        let cleanUrl = stringValue(url).split("?")[0].split("#")[0]
        let name = cleanUrl.substring(cleanUrl.lastIndexOf("/") + 1)
        try {
            name = decodeURIComponent(name)
        } catch (e) {
            console.log("decode file name error", e)
        }
        return sanitizeFileName(name)
    }

    function downloadFileName() {
        let name = sanitizeFileName(fileName)
        if (name.length > 0) {
            return name
        }
        name = fileNameFromUrl(resolvedDownloadUrl())
        if (name.length > 0) {
            return name
        }
        return "MotionStudioUpdate_" + Qt.formatDateTime(new Date(), "yyyyMMdd_hhmmss") + ".exe"
    }

    function versionNumbers(version) {
        let matches = stringValue(version).match(/\d+/g)
        if (!matches) {
            return []
        }
        let result = []
        for (let i = 0; i < matches.length; i++) {
            result.push(parseInt(matches[i]))
        }
        return result
    }

    function compareVersions(left, right) {
        let leftNums = versionNumbers(left)
        let rightNums = versionNumbers(right)
        let count = Math.max(leftNums.length, rightNums.length)
        for (let i = 0; i < count; i++) {
            let leftValue = i < leftNums.length ? leftNums[i] : 0
            let rightValue = i < rightNums.length ? rightNums[i] : 0
            if (leftValue > rightValue) {
                return 1
            }
            if (leftValue < rightValue) {
                return -1
            }
        }
        return 0
    }

    function firstValue(data, keys) {
        for (let i = 0; i < keys.length; i++) {
            let key = keys[i]
            if (data && data[key] !== undefined && data[key] !== null) {
                return stringValue(data[key])
            }
        }
        return ""
    }

    function resolveUrl(url, baseUrl) {
        let target = stringValue(url)
        if (target.length === 0 || /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target)) {
            return target
        }

        let base = stringValue(baseUrl)
        let originMatch = base.match(/^([a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^/]+)/)
        if (target.charAt(0) === "/" && originMatch) {
            return originMatch[1] + target
        }

        let slashIndex = base.lastIndexOf("/")
        let baseFolder = slashIndex >= 0 ? base.substring(0, slashIndex + 1) : base
        return baseFolder + target
    }

    function setError(message) {
        errorText = stringValue(message)
        statusText = errorText.length > 0 ? errorText : qsTr("操作失败")
        updateState = errorState
    }

    function setManifest(data) {
        let payload = data && data.data ? data.data : data
        latestVersion = firstValue(payload, ["version", "latest_version", "latestVersion", "app_version", "appVersion"])
        downloadUrl = firstValue(payload, ["download_url", "downloadUrl", "package_url", "packageUrl", "url"])
        fileName = firstValue(payload, ["file_name", "fileName", "filename", "name"])
        releaseNotes = firstValue(payload, ["notes", "release_notes", "releaseNotes", "description", "changelog"])

        if (fileName.length === 0 && downloadUrl.length > 0) {
            fileName = fileNameFromUrl(downloadUrl)
        }

        if (latestVersion.length === 0 && downloadUrl.length === 0) {
            setError(qsTr("更新清单缺少 version 或下载地址"))
            return
        }

        errorText = ""
        progress = 0
        if (updateAvailable) {
            statusText = qsTr("发现新版本 ") + latestVersion
        } else if (latestVersion.length > 0) {
            statusText = qsTr("当前已是最新版本")
            updateState = latestState
            return
        } else {
            statusText = qsTr("已读取安装包信息")
        }
        updateState = latestState
    }

    function checkUpdate() {
        updateState = checkingState
        statusText = qsTr("正在检查更新...")
        errorText = ""
        progress = 0

        api.loadJsonData(manifestUrl(), function(result) {
            try {
                setManifest(JSON.parse(result))
            } catch (e) {
                setError(qsTr("更新清单解析失败: ") + e)
            }
        }, function(error, status) {
            let fallbackUrl = stringValue(coreSetting.softwareUpdatePackageUrl)
            if (fallbackUrl.length > 0) {
                downloadUrl = fallbackUrl
                fileName = fileNameFromUrl(fallbackUrl)
                latestVersion = ""
                releaseNotes = ""
                updateState = latestState
                statusText = qsTr("检查失败，已使用手动安装包地址")
                errorText = stringValue(error)
                return
            }
            setError(qsTr("检查更新失败(") + status + "): " + error)
        })
    }

    function startDownload() {
        let url = resolvedDownloadUrl()
        if (url.length === 0) {
            setError(qsTr("请先检查更新或填写安装包地址"))
            return
        }

        savePath = joinPath(downloadFolder, downloadFileName())
        progress = 0
        errorText = ""
        statusText = qsTr("正在下载更新包...")
        updateState = downloadingState
        fileDownloader.downloadFile(url, savePath, "")
    }

    function openDownloadedFile() {
        if (savePath.length > 0) {
            Qt.openUrlExternally(fileUrl(savePath))
        }
    }

    function openDownloadFolder() {
        Qt.openUrlExternally(fileUrl(downloadFolder))
    }

    function installAndQuit() {
        openDownloadedFile()
        Qt.quit()
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Image {
                source: coreStyle.getIcon("upApp")
                sourceSize.width: 32
                sourceSize.height: 32
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Label {
                    text: qsTr("当前版本: ") + (currentVersion() || qsTr("未知"))
                    color: coreStyle.titleColor
                    font.pixelSize: 15
                    font.bold: true
                }

                Label {
                    text: statusText
                    color: updateState === errorState ? Material.color(Material.Red) : coreStyle.labelColor
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: qsTr("更新清单")
                Layout.preferredWidth: 72
            }

            TextField {
                id: manifestInput
                text: coreSetting.softwareUpdateManifestUrl
                placeholderText: defaultManifestUrl()
                selectByMouse: true
                enabled: !busy
                Layout.fillWidth: true
                onEditingFinished: coreSetting.softwareUpdateManifestUrl = text.trim()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: qsTr("安装包")
                Layout.preferredWidth: 72
            }

            TextField {
                id: packageInput
                text: coreSetting.softwareUpdatePackageUrl
                placeholderText: qsTr("可选：直接填写 exe/msi/zip 下载地址")
                selectByMouse: true
                enabled: !busy
                Layout.fillWidth: true
                onEditingFinished: {
                    coreSetting.softwareUpdatePackageUrl = text.trim()
                    if (text.trim().length > 0) {
                        fileName = fileNameFromUrl(text)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: qsTr("最新版本")
                Layout.preferredWidth: 72
            }

            Label {
                text: latestVersion.length > 0 ? latestVersion : qsTr("未获取")
                color: updateAvailable ? Material.color(Material.Green) : coreStyle.labelColor
                Layout.preferredWidth: 120
            }

            Label {
                text: qsTr("保存到")
            }

            Label {
                text: downloadFolder
                color: coreStyle.labelColor
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }

        ProgressBar {
            visible: updateState === downloadingState || updateState === finishedState
            Layout.fillWidth: true
            from: 0
            to: 1
            value: progress
            indeterminate: updateState === downloadingState && progress <= 0
        }

        Label {
            visible: releaseNotes.length > 0
            text: releaseNotes
            color: coreStyle.labelColor
            wrapMode: Text.WrapAnywhere
            maximumLineCount: 4
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: busy && updateState === checkingState ? qsTr("检查中...") : qsTr("检查更新")
                enabled: !busy
                onClicked: checkUpdate()
            }

            Button {
                text: busy && updateState === downloadingState ? qsTr("下载中...") : qsTr("下载更新")
                enabled: !busy && hasDownloadUrl
                highlighted: updateAvailable || (latestVersion.length === 0 && hasDownloadUrl)
                onClicked: startDownload()
            }

            CheckBox {
                text: qsTr("完成后打开")
                checked: coreSetting.softwareUpdateAutoOpen
                enabled: !busy
                onCheckedChanged: coreSetting.softwareUpdateAutoOpen = checked
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: qsTr("打开目录")
                enabled: !busy
                onClicked: openDownloadFolder()
            }

            Button {
                text: qsTr("打开安装包")
                enabled: updateState === finishedState && savePath.length > 0
                onClicked: openDownloadedFile()
            }

            Button {
                text: qsTr("退出并安装")
                enabled: updateState === finishedState && savePath.length > 0
                onClicked: installAndQuit()
            }
        }
    }

    Connections {
        target: fileDownloader

        function onDownloadProgress(bytesReceived, bytesTotal) {
            if (root.updateState !== root.downloadingState) {
                return
            }
            root.progress = bytesTotal > 0 ? bytesReceived / bytesTotal : 0
        }

        function onDownloadFinished() {
            if (root.updateState !== root.downloadingState) {
                return
            }
            root.progress = 1
            root.updateState = root.finishedState
            root.statusText = qsTr("更新包下载完成")
            if (coreSetting.softwareUpdateAutoOpen) {
                root.openDownloadedFile()
            }
        }

        function onDownloadError(errorString) {
            if (root.updateState !== root.downloadingState) {
                return
            }
            root.setError(qsTr("下载更新失败: ") + errorString)
        }
    }
}
