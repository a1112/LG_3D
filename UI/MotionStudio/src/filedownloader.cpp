#include "filedownloader.h"
#include <QNetworkRequest>
#include <QUrl>

FileDownloader::FileDownloader(QObject *parent) : QObject(parent), reply(nullptr) {}

void FileDownloader::downloadFile(const QString &url, const QString &filePath) {
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
    if (reply->error() == QNetworkReply::NoError) {
        file.write(reply->readAll());
        file.close();
        emit downloadFinished();
    } else {
        emit downloadError(reply->errorString());
    }
    reply->deleteLater();
    reply = nullptr;
}

void FileDownloader::onErrorOccurred(QNetworkReply::NetworkError code) {
    emit downloadError(reply->errorString());
    reply->deleteLater();
    reply = nullptr;
}
