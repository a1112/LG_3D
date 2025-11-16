// ConsoleController.h

#ifndef CONSOLECONTROLLER_H
#define CONSOLECONTROLLER_H

#include <QObject>

#ifdef _WIN32
#include <windows.h>
#endif

class ConsoleController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool isShow READ isShow WRITE setIsShow NOTIFY isShowChanged)

public:

    explicit ConsoleController(QObject *parent = nullptr) : QObject(parent), m_isShow(false) {
    }

    // Getter for isShow
    bool isShow() const {
        return m_isShow;
    }

    // Setter for isShow
    void setIsShow(bool show) {
        if (m_isShow != show) {
            m_isShow = show;
            if (show) {
                showConsole();
            } else {
                hideConsole();
            }
            emit isShowChanged();
        }
    }

    Q_INVOKABLE void showConsole() {
#ifdef _WIN32
        HWND consoleWindow = GetConsoleWindow();
        if (consoleWindow) {
            ShowWindow(consoleWindow, SW_SHOW);
            setIsShow(true);  // 更新 isShow 状态
        }
#endif
    }

    Q_INVOKABLE void hideConsole() {
#ifdef _WIN32
        HWND consoleWindow = GetConsoleWindow();
        if (consoleWindow) {
            ShowWindow(consoleWindow, SW_HIDE);
            setIsShow(false);  // 更新 isShow 状态
        }
#endif
    }

signals:
    void isShowChanged();

private:
    bool m_isShow;
};

#endif // CONSOLECONTROLLER_H
