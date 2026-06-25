#include "filedownloader.h"
#include <QDir>
#include <QFileInfo>
#include <QNetworkRequest>
#include <QUrl>

FileDownloader::FileDownloader(QObject *parent) : QObject(parent), reply(nullptr), errorEmitted(false) {}

static QString buildReplyError(QNetworkReply *reply) {
    if (!reply) {
        return "Download reply is null";
    }
    const QString networkError = reply->errorString();
    const QByteArray body = reply->readAll();
    const QString bodyText = QString::fromUtf8(body).trimmed();
    if (bodyText.isEmpty()) {
        return networkError;
    }
    return networkError + "\n" + bodyText;
}

void FileDownloader::downloadFile(const QString &url, const QString &filePath) {
    clearCurrentReply();
    errorEmitted = false;
    if (!prepareFile(filePath)) {
        return;
    }

    QUrl qurl(url);
    QNetworkRequest request(qurl);
    reply = manager.get(request);

    connect(reply, &QNetworkReply::downloadProgress, this, &FileDownloader::onDownloadProgress);
    connect(reply, &QNetworkReply::readyRead, this, &FileDownloader::onReadyRead);
    connect(reply, &QNetworkReply::finished, this, &FileDownloader::onDownloadFinished);
    connect(reply, &QNetworkReply::errorOccurred, this, &FileDownloader::onErrorOccurred);
}

void FileDownloader::downloadFile(const QString &url, const QString &filePath, const QString &postData) {
    clearCurrentReply();
    errorEmitted = false;
    if (!prepareFile(filePath)) {
        return;
    }

    QUrl qurl(url);
    QNetworkRequest request(qurl);
    // 将 QString 转换为 QByteArray
    QByteArray postDataBytes = postData.toUtf8();

    // Set any headers if necessary
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");


    // Perform the POST request with data
    reply = manager.post(request, postDataBytes);

    connect(reply, &QNetworkReply::downloadProgress, this, &FileDownloader::onDownloadProgress);
    connect(reply, &QNetworkReply::readyRead, this, &FileDownloader::onReadyRead);
    connect(reply, &QNetworkReply::finished, this, &FileDownloader::onDownloadFinished);
    connect(reply, &QNetworkReply::errorOccurred, this, &FileDownloader::onErrorOccurred);

}

void FileDownloader::onDownloadProgress(qint64 bytesReceived, qint64 bytesTotal) {
    emit downloadProgress(bytesReceived, bytesTotal);
}

void FileDownloader::onReadyRead() {
    QNetworkReply *currentReply = qobject_cast<QNetworkReply *>(sender());
    if (!currentReply) {
        currentReply = reply;
    }
    if (currentReply && file.isOpen()) {
        file.write(currentReply->readAll());
    }
}

void FileDownloader::onDownloadFinished() {
    QNetworkReply *currentReply = qobject_cast<QNetworkReply *>(sender());
    if (!currentReply) {
        currentReply = reply;
    }
    if (!currentReply) {
        if (file.isOpen()) {
            file.close();
        }
        emit downloadError("Download reply was cleared before finish");
        return;
    }

    if (currentReply->error() == QNetworkReply::NoError) {
        if (file.isOpen()) {
            file.write(currentReply->readAll());
            file.close();
        }
        emit downloadFinished();
    } else {
        const QString errorString = buildReplyError(currentReply);
        closeAndRemovePartialFile();
        if (!errorEmitted) {
            errorEmitted = true;
            emit downloadError(errorString);
        }
    }
    currentReply->deleteLater();
    if (reply == currentReply) {
        reply = nullptr;
    }
}

void FileDownloader::onErrorOccurred(QNetworkReply::NetworkError code) {
    Q_UNUSED(code);
    QNetworkReply *currentReply = qobject_cast<QNetworkReply *>(sender());
    if (!currentReply) {
        currentReply = reply;
    }
    if (!currentReply) {
        emit downloadError("Download reply is null");
        return;
    }

    if (file.isOpen()) {
        closeAndRemovePartialFile();
    }
    if (!errorEmitted) {
        errorEmitted = true;
        emit downloadError(buildReplyError(currentReply));
    }
}

bool FileDownloader::prepareFile(const QString &filePath) {
    if (file.isOpen()) {
        file.close();
    }

    QFileInfo fileInfo(filePath);
    const QString folderPath = fileInfo.absolutePath();
    if (!folderPath.isEmpty() && !QDir().mkpath(folderPath)) {
        emit downloadError("Failed to create download folder: " + folderPath);
        return false;
    }

    file.setFileName(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        emit downloadError("Failed to open file for writing: " + file.errorString());
        return false;
    }
    return true;
}

void FileDownloader::clearCurrentReply() {
    if (reply) {
        disconnect(reply, nullptr, this, nullptr);
        reply->deleteLater();
        reply = nullptr;
    }
    if (file.isOpen()) {
        file.close();
    }
}

void FileDownloader::closeAndRemovePartialFile() {
    const QString failedFilePath = file.fileName();
    if (file.isOpen()) {
        file.close();
    }
    if (!failedFilePath.isEmpty()) {
        QFile::remove(failedFilePath);
    }
}
