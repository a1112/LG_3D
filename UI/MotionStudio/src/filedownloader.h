#ifndef FILEDOWNLOADER_H
#define FILEDOWNLOADER_H
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QObject>
#include <QFile>

class FileDownloader : public QObject {
    Q_OBJECT
public:
    explicit FileDownloader(QObject *parent = nullptr);
    Q_INVOKABLE void downloadFile(const QString &url, const QString &filePath);
    Q_INVOKABLE void downloadFile(const QString &url, const QString &filePath,const QString &postData);

signals:
    void downloadProgress(qint64 bytesReceived, qint64 bytesTotal);
    void downloadFinished();
    void downloadError(const QString &errorString);

private slots:
    void onDownloadProgress(qint64 bytesReceived, qint64 bytesTotal);
    void onDownloadFinished();
    void onErrorOccurred(QNetworkReply::NetworkError code);

private:
    QNetworkAccessManager manager;
    QNetworkReply *reply;
    QFile file;
};
#endif
