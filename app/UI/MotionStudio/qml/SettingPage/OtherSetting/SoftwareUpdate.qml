import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Core/JsonUtils.js" as JsonUtils

GroupBox {
    id: root
    required property var apiClient
    required property var style
    required property var settings
    required property var appInfo
    required property var downloadClient
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
        return stringValue(root.appInfo ? root.appInfo.serverVersion : "")
    }

    function defaultManifestUrl() {
        return root.apiClient.apiConfig.serverUrl + "/software_update/manifest"
    }

    function defaultDownloadFolder() {
        let folder = pathFromUrl(StandardPaths.writableLocation(StandardPaths.DownloadLocation))
        if (folder.length > 0) {
            return folder
        }
        return pathFromUrl(StandardPaths.writableLocation(StandardPaths.DesktopLocation))
    }

    function manifestUrl() {
        let url = stringValue(root.settings.softwareUpdateManifestUrl)
        return url.length > 0 ? url : defaultManifestUrl()
    }

    function resolvedDownloadUrl() {
        let manualUrl = stringValue(root.settings.softwareUpdatePackageUrl)
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

        root.apiClient.loadJsonData(root.manifestUrl(), function(result) {
            let manifest = JsonUtils.parse(
                    result, null, "software update manifest")
            if (!manifest) {
                root.setError(qsTr("更新清单解析失败"))
                return
            }
            root.setManifest(manifest)
        }, function(error, status) {
            let fallbackUrl = root.stringValue(
                        root.settings.softwareUpdatePackageUrl)
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
        root.downloadClient.downloadFile(url, root.savePath, "")
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
                source: root.style.getIcon("upApp")
                sourceSize.width: 32
                sourceSize.height: 32
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Label {
                    text: qsTr("当前版本: ")
                          + (root.currentVersion() || qsTr("未知"))
                    color: root.style.titleColor
                    font.pixelSize: 15
                    font.bold: true
                }

                Label {
                    text: root.statusText
                    color: root.updateState === root.errorState
                           ? root.style.statusErrorColor
                           : root.style.labelColor
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
                text: root.settings.softwareUpdateManifestUrl
                placeholderText: root.defaultManifestUrl()
                selectByMouse: true
                enabled: !root.busy
                Layout.fillWidth: true
                onEditingFinished:
                    root.settings.softwareUpdateManifestUrl =
                        manifestInput.text.trim()
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
                text: root.settings.softwareUpdatePackageUrl
                placeholderText: qsTr("可选：直接填写 exe/msi/zip 下载地址")
                selectByMouse: true
                enabled: !root.busy
                Layout.fillWidth: true
                onEditingFinished: {
                    root.settings.softwareUpdatePackageUrl =
                        packageInput.text.trim()
                    if (packageInput.text.trim().length > 0) {
                        root.fileName =
                            root.fileNameFromUrl(packageInput.text)
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
                text: root.latestVersion.length > 0
                      ? root.latestVersion : qsTr("未获取")
                color: root.updateAvailable
                       ? root.style.statusSuccessColor
                       : root.style.labelColor
                Layout.preferredWidth: 120
            }

            Label {
                text: qsTr("保存到")
            }

            Label {
                text: root.downloadFolder
                color: root.style.labelColor
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }

        ProgressBar {
            visible: root.updateState === root.downloadingState
                     || root.updateState === root.finishedState
            Layout.fillWidth: true
            from: 0
            to: 1
            value: root.progress
            indeterminate: root.updateState === root.downloadingState
                           && root.progress <= 0
        }

        Label {
            visible: root.releaseNotes.length > 0
            text: root.releaseNotes
            color: root.style.labelColor
            wrapMode: Text.WrapAnywhere
            maximumLineCount: 4
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: root.busy && root.updateState === root.checkingState
                      ? qsTr("检查中...") : qsTr("检查更新")
                enabled: !root.busy
                onClicked: root.checkUpdate()
            }

            Button {
                text: root.busy && root.updateState === root.downloadingState
                      ? qsTr("下载中...") : qsTr("下载更新")
                enabled: !root.busy && root.hasDownloadUrl
                highlighted: root.updateAvailable
                             || (root.latestVersion.length === 0
                                 && root.hasDownloadUrl)
                onClicked: root.startDownload()
            }

            CheckBox {
                id: autoOpenCheckBox
                text: qsTr("完成后打开")
                checked: root.settings.softwareUpdateAutoOpen
                enabled: !root.busy
                onCheckedChanged:
                    root.settings.softwareUpdateAutoOpen =
                        autoOpenCheckBox.checked
            }

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: qsTr("打开目录")
                enabled: !root.busy
                onClicked: root.openDownloadFolder()
            }

            Button {
                text: qsTr("打开安装包")
                enabled: root.updateState === root.finishedState
                         && root.savePath.length > 0
                onClicked: root.openDownloadedFile()
            }

            Button {
                text: qsTr("退出并安装")
                enabled: root.updateState === root.finishedState
                         && root.savePath.length > 0
                onClicked: root.installAndQuit()
            }
        }
    }

    Connections {
        target: root.downloadClient

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
            if (root.settings.softwareUpdateAutoOpen) {
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
