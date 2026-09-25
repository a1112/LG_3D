/****************************************************************************
**
** Copyright (C) 2021 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
** This file is part of Qt Quick Studio Components.
**
** $QT_BEGIN_LICENSE:GPL$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** GNU General Public License Usage
** Alternatively, this file may be used under the terms of the GNU
** General Public License version 3 or (at your option) any later version
** approved by the KDE Free Qt Foundation. The licenses are as published by
** the Free Software Foundation and appearing in the file LICENSE.GPL3
** included in the packaging of this file. Please review the following
** information to ensure the GNU General Public License requirements will
** be met: https://www.gnu.org/licenses/gpl-3.0.html.
**
** $QT_END_LICENSE$
**
****************************************************************************/

#include "scriptlauncher.h"
#include "clipboard.h"
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>

#include "app_environment.h"
#include "import_qml_components_plugins.h"
#include "import_qml_plugins.h"
#include "filedownloader.h"
#include "consolecontroller.h"
#include <QSurfaceFormat>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QMutex>
#include <QMutexLocker>
#include <cstdio>

namespace {

constexpr qint64 kMotionStudioLogMaxBytes = 20LL * 1024LL * 1024LL;
constexpr int kMotionStudioLogBackups = 3;

bool rotateMotionStudioLog(const QString &logPath)
{
    const QFileInfo currentLog(logPath);
    if (!currentLog.exists() || currentLog.size() < kMotionStudioLogMaxBytes) {
        return true;
    }

    QFile::remove(logPath + QStringLiteral(".%1").arg(kMotionStudioLogBackups));
    for (int index = kMotionStudioLogBackups - 1; index >= 1; --index) {
        const QString source = logPath + QStringLiteral(".%1").arg(index);
        if (!QFile::exists(source)) {
            continue;
        }
        const QString destination = logPath + QStringLiteral(".%1").arg(index + 1);
        QFile::remove(destination);
        QFile::rename(source, destination);
    }

    const QString firstBackup = logPath + QStringLiteral(".1");
    QFile::remove(firstBackup);
    return QFile::rename(logPath, firstBackup);
}

} // namespace

static void motionStudioMessageHandler(QtMsgType type, const QMessageLogContext &context, const QString &msg)
{
    static QMutex mutex;
    static QFile logFile;
    static QString logPath;
    static qint64 logBytesWritten = 0;
    static bool logInitialized = false;
    QMutexLocker locker(&mutex);

    const char *level = "DEBUG";
    switch (type) {
    case QtInfoMsg: level = "INFO"; break;
    case QtWarningMsg: level = "WARN"; break;
    case QtCriticalMsg: level = "CRITICAL"; break;
    case QtFatalMsg: level = "FATAL"; break;
    default: break;
    }

    QString line = QDateTime::currentDateTime().toString(Qt::ISODateWithMs)
                   + " [" + QString::fromLatin1(level) + "] " + msg;
    if (context.file) {
        line += QStringLiteral(" (%1:%2)").arg(QString::fromUtf8(context.file)).arg(context.line);
    }
    const QString lineWithNewline = line + QLatin1Char('\n');

    fprintf(stderr, "%s", lineWithNewline.toLocal8Bit().constData());
    fflush(stderr);

#ifdef _WIN32
    const std::wstring debugLine = lineWithNewline.toStdWString();
    OutputDebugStringW(debugLine.c_str());
#endif

    if (!logInitialized) {
        QDir logDir(QCoreApplication::applicationDirPath());
        for (int i = 0; i < 5; ++i) {
            logDir.cdUp();
        }
        if (logDir.mkpath("debug_log/MotionStudio")) {
            logPath = logDir.filePath("debug_log/MotionStudio/qml.log");
            const bool rotationSucceeded = rotateMotionStudioLog(logPath);
            logFile.setFileName(logPath);
            if (logFile.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
                // If a transient file lock prevented rotation, count only new
                // bytes before retrying. This avoids a rotation attempt for
                // every debug message while still retrying after another cap.
                logBytesWritten = rotationSucceeded ? logFile.size() : 0;
            }
        }
        logInitialized = true;
    }

    const QByteArray encodedLine = lineWithNewline.toUtf8();
    if (logFile.isOpen()
        && logBytesWritten + encodedLine.size() > kMotionStudioLogMaxBytes) {
        logFile.flush();
        logFile.close();
        const bool rotationSucceeded = rotateMotionStudioLog(logPath);
        logFile.setFileName(logPath);
        if (logFile.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
            logBytesWritten = rotationSucceeded ? logFile.size() : 0;
        }
    }
    if (logFile.isOpen()) {
        const qint64 written = logFile.write(encodedLine);
        if (written > 0) {
            logBytesWritten += written;
        }
        if (type != QtDebugMsg) {
            logFile.flush();
        }
    }

    if (type == QtFatalMsg) {
        abort();
    }
}

std::string getComputerName() {
    QSurfaceFormat format;
    format.setDepthBufferSize(24);
    format.setStencilBufferSize(8);
    // 尝试设置更大的纹理尺寸限制
    format.setOption(QSurfaceFormat::ResetNotification);
    format.setVersion(4, 1); // 使用较新的OpenGL版本

    QSurfaceFormat::setDefaultFormat(format);

    char computerName[MAX_COMPUTERNAME_LENGTH + 1];
    DWORD size = sizeof(computerName) / sizeof(computerName[0]);

    if (GetComputerNameA(computerName, &size)) {
        return computerName;
    } else {
        return "Unknown";
    }
}

int main(int argc, char *argv[])
{

    QCoreApplication::setOrganizationName("北京科技大学设计研究院有限公司");
    QCoreApplication::setOrganizationDomain("1");
    set_qt_environment();

    QApplication app(argc, argv);
    qInstallMessageHandler(motionStudioMessageHandler);
    qInfo() << "MotionStudio starting, appDir=" << QCoreApplication::applicationDirPath();

    QQmlApplicationEngine engine;
    #ifdef _WIN32
        // 仅在 Windows 系统上启用控制台
    std::string computerName = getComputerName();
    //  將下述PC保留控制台

    std::vector <std::string> args {"DESKTOP-94ADH1G","LCX_ACE","DESKTOP-TEM8G6F","DESKTOP-V9D92AP","MS-LGKRSZGOVODD","DESKTOP-3VCH6DO"};
    if (std::find(args.begin(), args.end(), computerName) == args.end()) {

        AllocConsole();
        freopen("CONOUT$", "w", stdout);
        freopen("CONOUT$", "w", stderr);
        ConsoleController consoleController;
        consoleController.hideConsole();
    }
    qDebug() << "Computer name: " << getComputerName();
    #endif


    ScriptLauncher  launcher;
    engine.rootContext()->setContextProperty("ScriptLauncher", &launcher);

    FileDownloader downloader;
    engine.rootContext()->setContextProperty("fileDownloader", &downloader);


    qmlRegisterType<Clipboard>("Clipboard",1,0,"Clipboard");
    qmlRegisterType<ConsoleController>("ConsoleController", 1, 0, "ConsoleController");

    // qmlRegisterType<FileDownloader>("FileDownloader",1,0,"FileDownloader");

    const QUrl url(QStringLiteral("qrc:/qml/main.qml"));
    QObject::connect(
                &engine, &QQmlApplicationEngine::objectCreated, &app,
                [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    },
    Qt::QueuedConnection);

    engine.addImportPath(QCoreApplication::applicationDirPath() + "/qml");
    engine.addImportPath(":/");

    qInfo() << "Loading QML" << url;
    engine.load(url);
    qInfo() << "QML loaded, rootObjects=" << engine.rootObjects().size();

    if (engine.rootObjects().isEmpty()) {
        return -1;
    }

    return app.exec();
}
