#ifndef CONSOLECONTROLLER_H
#define CONSOLECONTROLLER_H

#include <QObject>
#include <cstdio>

#ifdef _WIN32
#include <windows.h>
#endif

class ConsoleController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool isShow READ isShow WRITE setIsShow NOTIFY isShowChanged)

public:
    explicit ConsoleController(QObject *parent = nullptr)
        : QObject(parent)
        , m_isShow(false)
    {
    }

    bool isShow() const
    {
        return m_isShow;
    }

    void setIsShow(bool show)
    {
        if (m_isShow == show) {
            return;
        }
        if (show) {
            showConsole();
        } else {
            hideConsole();
        }
    }

    Q_INVOKABLE void showConsole()
    {
#ifdef _WIN32
        HWND consoleWindow = GetConsoleWindow();
        if (!consoleWindow) {
            if (!AttachConsole(ATTACH_PARENT_PROCESS)) {
                AllocConsole();
            }
            freopen("CONOUT$", "w", stdout);
            freopen("CONOUT$", "w", stderr);
            consoleWindow = GetConsoleWindow();
        }
        if (consoleWindow) {
            ShowWindow(consoleWindow, SW_SHOW);
        }
#endif
        setShowState(true);
    }

    Q_INVOKABLE void hideConsole()
    {
#ifdef _WIN32
        HWND consoleWindow = GetConsoleWindow();
        if (consoleWindow) {
            ShowWindow(consoleWindow, SW_HIDE);
        }
#endif
        setShowState(false);
    }

signals:
    void isShowChanged();

private:
    void setShowState(bool show)
    {
        if (m_isShow == show) {
            return;
        }
        m_isShow = show;
        emit isShowChanged();
    }

    bool m_isShow;
};

#endif // CONSOLECONTROLLER_H
