#ifndef SCRIPTLAUNCHER_H
#define SCRIPTLAUNCHER_H

#include <QFileInfo>
#include <QObject>
#include <QProcess>

class ScriptLauncher : public QObject
{

    Q_OBJECT
public:
    explicit ScriptLauncher(QObject *parent = 0);
    Q_INVOKABLE void launchScript(QString text);
    Q_INVOKABLE void launchScriptExplorer(QString text);
    Q_INVOKABLE bool fileExists(QString filePath) ;

private:
    QProcess *m_process;
};

#endif // SCRIPTLAUNCHER_H
