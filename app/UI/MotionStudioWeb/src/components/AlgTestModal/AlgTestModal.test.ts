import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import algTestModalSource from './index.tsx?raw'

const cssSource = readFileSync(fileURLToPath(new URL('./AlgTestModal.css', import.meta.url)), 'utf8')
const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/AlgTest/AlgTestDialog.qml', import.meta.url)),
  'utf8',
)

describe('AlgTestModal QML websocket progress parity', () => {
  it('logs an unexpected progress websocket close only while the test is running', () => {
    expect(algTestModalSource).toContain('const runningRef = useRef(false)')
    expect(algTestModalSource).toContain('runningRef.current = running')
    expect(algTestModalSource).toMatch(/socket\.onclose = \(\) => \{[\s\S]*if \(runningRef\.current\) \{[\s\S]*addLog\('进度连接已关闭'\)/)
  })

  it('logs QML-style start and stop failure details', () => {
    expect(algTestModalSource).toContain('formatAlgTestFailureLog')
    expect(algTestModalSource).toMatch(/catch \(error\) \{[\s\S]*addLog\(formatAlgTestFailureLog\('启动失败', error\)\)/)
    expect(algTestModalSource).toMatch(/catch \(error\) \{[\s\S]*addLog\(formatAlgTestFailureLog\('停止失败', error\)\)/)
  })

  it('logs QML-style progress websocket error details when available', () => {
    expect(qmlSource).toContain('appendLog(qsTr("进度连接错误: %1").arg(errorString))')
    expect(algTestModalSource).toContain('formatAlgProgressSocketErrorLog')
    expect(algTestModalSource).toMatch(/socket\.onerror = \(event\) => \{[\s\S]*addLog\(formatAlgProgressSocketErrorLog\(event\)\)/)
  })

  it('only appends the QML completion log when the websocket finished payload has a summary', () => {
    const finishedBranchStart = algTestModalSource.indexOf('if (progress.finished)')
    const finishedBranchEnd = algTestModalSource.indexOf('socket.close()', finishedBranchStart)
    const finishedBranch = algTestModalSource.slice(finishedBranchStart, finishedBranchEnd)

    expect(qmlSource).toContain('if (js.finished)')
    expect(qmlSource).toContain('if (js.summary)')
    expect(finishedBranch).toContain('if (progress.summary)')
    expect(finishedBranch).toContain("addLog('任务完成')")
    expect(finishedBranch.trim()).not.toBe("if (progress.finished) {\n        runningRef.current = false\n        setRunning(false)\n        socket.close()\n        addLog('任务完成')\n      }")
  })
})

describe('AlgTestModal QML AlgTestDialog shell parity', () => {
  it('mirrors the QML fixed window and inner title instead of using an AntD title bar', () => {
    expect(qmlSource).toContain('width: 900')
    expect(qmlSource).toContain('height: 640')
    expect(qmlSource).toContain('text: qsTr("算法测试")')
    expect(qmlSource).toContain('font.bold: true')
    expect(qmlSource).toContain('font.pointSize: 20')
    expect(qmlSource).toContain('Layout.alignment: Qt.AlignHCenter')

    expect(algTestModalSource).toContain('title={null}')
    expect(algTestModalSource).not.toContain('title="算法测试"')
    expect(algTestModalSource).toContain('className="alg-test-modal-window"')
    expect(algTestModalSource).toContain('width={900}')
    expect(algTestModalSource).toContain('data-qml-alg-test-dialog')
    expect(algTestModalSource).toContain('data-qml-alg-test-title')
    expect(algTestModalSource).toMatch(
      /<div className="alg-test-modal"[\s\S]*data-qml-alg-test-dialog[\s\S]*<h3[\s\S]*data-qml-alg-test-title[\s\S]*算法测试[\s\S]*<div className="alg-test-grid">/,
    )

    expect(cssSource).toContain('.alg-test-title')
    expect(cssSource).toContain('font-size: 20pt;')
    expect(cssSource).toContain('font-weight: 700;')
    expect(cssSource).toContain('text-align: center;')
    expect(cssSource).toContain('.alg-test-modal-window .ant-modal-content')
    expect(cssSource).toContain('background: #0f1820;')
    expect(cssSource).toContain('min-height: min(640px, calc(100vh - 32px));')
    expect(cssSource).toContain('height: min(640px, calc(100vh - 32px));')
    expect(cssSource).toContain('max-height: min(640px, calc(100vh - 32px));')
    expect(cssSource).toContain('.alg-test-modal-window .ant-modal-body')
    expect(cssSource).toContain('height: calc(min(640px, calc(100vh - 32px)) - 48px);')
    expect(cssSource).toContain('overflow: hidden;')
    expect(cssSource).toContain('height: 100%;')
    expect(cssSource).toContain('min-height: 0;')
    expect(cssSource).toContain('flex: 1 1 auto;')
    expect(cssSource).not.toContain('height: 210px;')
  })
})
