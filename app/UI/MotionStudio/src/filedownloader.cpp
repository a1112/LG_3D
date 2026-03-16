#include "filedownloader.h"
#include <QNetworkRequest>
#include <QUrl>

FileDownloader::FileDownloader(QObject *parent) : QObject(parent), reply(nullptr) {}

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
    if (reply) {
        disconnect(reply, nullptr, this, nullptr);
        reply->deleteLater();
        reply = nullptr;
    }
    if (file.isOpen()) {
        file.close();
    }

    QUrl qurl(url);
    QNetworkRequest request(qurl);
    reply = manager.get(request);
    file.setFileName(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        emit downloadError("Failed to open file for writing");
        return;
    }

    connect(reply, &QNetworkReply::downloadProgress, this, &FileDownloader::onDownloadProgress);
    connect(reply, &QNetworkReply::finished, this, &FileDownloader::onDownloadFinished);
    connect(reply, &QNetworkReply::errorOccurred, this, &FileDownloader::onErrorOccurred);
}

void FileDownloader::downloadFile(const QString &url, const QString &filePath, const QString &postData) {
    if (reply) {
        disconnect(reply, nullptr, this, nullptr);
        reply->deleteLater();
        reply = nullptr;
    }
    if (file.isOpen()) {
        file.close();
    }

    QUrl qurl(url);
    QNetworkRequest request(qurl);
    // 将 QString 转换为 QByteArray
    QByteArray postDataBytes = postData.toUtf8();

    // Set any headers if necessary
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");


    // Perform the POST request with data
    reply = manager.post(request, postDataBytes);
    file.setFileName(filePath);

    if (!file.open(QIODevice::WriteOnly)) {
        emit downloadError("Failed to open file for writing");
        return;
    }

    connect(reply, &QNetworkReply::downloadProgress, this, &FileDownloader::onDownloadProgress);
    connect(reply, &QNetworkReply::finished, this, &FileDownloader::onDownloadFinished);
    connect(reply, &QNetworkReply::errorOccurred, this, &FileDownloader::onErrorOccurred);

}

void FileDownloader::onDownloadProgress(qint64 bytesReceived, qint64 bytesTotal) {
    emit downloadProgress(bytesReceived, bytesTotal);
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
        file.write(currentReply->readAll());
        file.close();
        emit downloadFinished();
    } else {
        if (file.isOpen()) {
            file.close();
        }
        emit downloadError(buildReplyError(currentReply));
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
        file.close();
    }
    emit downloadError(buildReplyError(currentReply));
}
