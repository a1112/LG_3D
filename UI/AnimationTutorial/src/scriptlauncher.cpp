#include "scriptlauncher.h"
#include <iostream>
#include <QMessageLogger>
#include <qlogging.h>
#include <QtCore/QDebug>
ScriptLauncher::ScriptLauncher(QObject *parent) :
    QObject(parent),
m_process(new QProcess(this))
{

}

void ScriptLauncher::launchScript(QString text)
{
qDebug()<<"hello qt!";
    // m_process->start("cmd.exe");
QProcess *process = new QProcess();

// start cmd and start mstsc app with /wait key to wait till RDP session is closed.
process->start("cmd", QStringList() << text);
// returns true if process started successfully
process->waitForStarted(-1);
}
void ScriptLauncher::launchScriptExplorer(QString text)
{
    qDebug()<<"hello qt!";
        // m_process->start("cmd.exe");
    QProcess *process = new QProcess();

    // start cmd and start mstsc app with /wait key to wait till RDP session is closed.
    process->start("explorer", QStringList() << text);
    // returns true if process started successfully
    process->waitForStarted(-1);
}
