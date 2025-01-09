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

std::string getComputerName() {
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
    set_qt_environment();

    QApplication app(argc, argv);

    QQmlApplicationEngine engine;
    #ifdef _WIN32
        // 仅在 Windows 系统上启用控制台
    std::string computerName = getComputerName();
    //  將下述PC保留控制台
    std::vector <std::string> args {"DESKTOP-94ADH1G","LCX_ACE","DESKTOP-TEM8G6F","DESKTOP-V9D92AP"};
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

    const QUrl url(u"qrc:Main/App.qml"_qs);
    QObject::connect(
                &engine, &QQmlApplicationEngine::objectCreated, &app,
                [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    },
    Qt::QueuedConnection);

    engine.addImportPath(QCoreApplication::applicationDirPath() + "/qml");
    engine.addImportPath(":/");

    engine.load(url);

    if (engine.rootObjects().isEmpty()) {
        return -1;
    }

    return app.exec();
}
