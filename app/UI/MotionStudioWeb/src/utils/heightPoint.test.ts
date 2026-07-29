import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  HeightPointReconnectBackoffError,
  HeightPointSupersededError,
  HeightPointWebSocketClient,
  buildHeightPointWebSocketMessage,
  parseHeightPointWebSocketMessage,
  resolveHeightPointWsUrl,
} from './heightPoint'

class FakeHeightPointWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 3

  static instances: FakeHeightPointWebSocket[] = []

  readonly sent: string[] = []
  readyState = FakeHeightPointWebSocket.CONNECTING
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(readonly url: string) {
    FakeHeightPointWebSocket.instances.push(this)
  }

  send(message: string): void {
    this.sent.push(message)
  }

  close(): void {
    this.readyState = FakeHeightPointWebSocket.CLOSED
    this.onclose?.()
  }

  open(): void {
    this.readyState = FakeHeightPointWebSocket.OPEN
    this.onopen?.()
  }

  emitMessage(message: string): void {
    this.onmessage?.({ data: message })
  }

  fail(): void {
    this.onerror?.()
  }
}

describe('heightPoint websocket helpers', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('resolves QML heightPoint websocket URLs through the Vite proxy or direct API base', () => {
    expect(resolveHeightPointWsUrl('/api', '/ws/coilData/heightPoint', 'http://127.0.0.1:3015')).toBe(
      'ws://127.0.0.1:3015/ws/coilData/heightPoint',
    )
    expect(resolveHeightPointWsUrl('http://127.0.0.1:5011', '/ws/coilData/heightPoint')).toBe(
      'ws://127.0.0.1:5011/ws/coilData/heightPoint',
    )
    expect(resolveHeightPointWsUrl('ws://127.0.0.1:5011', '/ws/coilData/heightPoint')).toBe(
      'ws://127.0.0.1:5011/ws/coilData/heightPoint',
    )
  })

  it('builds the QML websocket request payload with normalized pixel coordinates', () => {
    expect(JSON.parse(buildHeightPointWebSocketMessage({ surfaceKey: 's', coilId: 193113, x: 941.9, y: 650.2 }, 7))).toEqual({
      id: 7,
      surface_key: 'S',
      coil_id: '193113',
      x: 941,
      y: 650,
    })
  })

  it('parses value and error websocket messages from Rust/Python-compatible responses', () => {
    expect(parseHeightPointWebSocketMessage(JSON.stringify({ id: 7, value: '60371' }))).toEqual({
      id: 7,
      value: '60371',
    })
    expect(parseHeightPointWebSocketMessage(JSON.stringify({ id: 8, error: 'error' }))).toEqual({
      id: 8,
      error: 'error',
    })
    expect(parseHeightPointWebSocketMessage('not-json')).toEqual({
      id: null,
      error: 'invalid json',
    })
  })

  it('keeps one persistent websocket and resolves matching heightPoint responses', async () => {
    FakeHeightPointWebSocket.instances = []
    const client = new HeightPointWebSocketClient({
      apiBaseUrl: '/api',
      wsBaseUrl: 'ws://127.0.0.1:5011',
      wsPath: '/ws/coilData/heightPoint',
      origin: 'http://127.0.0.1:3015',
      WebSocketCtor: FakeHeightPointWebSocket,
      timeoutMs: 1000,
    })

    const first = client.request({ surfaceKey: 'S', coilId: 193113, x: 941.4, y: 650.6 })
    const second = client.request({ surfaceKey: 'L', coilId: 193113, x: 5, y: 2 })

    expect(FakeHeightPointWebSocket.instances).toHaveLength(1)
    const socket = FakeHeightPointWebSocket.instances[0]
    expect(socket.url).toBe('ws://127.0.0.1:5011/ws/coilData/heightPoint')
    expect(socket.sent).toEqual([])

    socket.open()
    expect(socket.sent.map((message) => JSON.parse(message))).toEqual([
      { id: 1, surface_key: 'S', coil_id: '193113', x: 941, y: 650 },
      { id: 2, surface_key: 'L', coil_id: '193113', x: 5, y: 2 },
    ])

    socket.emitMessage(JSON.stringify({ id: 2, value: 0 }))
    socket.emitMessage(JSON.stringify({ id: 1, value: 60371 }))

    await expect(first).resolves.toBe(60371)
    await expect(second).resolves.toBe(0)
    client.close()
  })

  it('keeps only the latest queued request for the same surface and coil', async () => {
    FakeHeightPointWebSocket.instances = []
    const client = new HeightPointWebSocketClient({
      apiBaseUrl: '/api',
      wsPath: '/ws/coilData/heightPoint',
      origin: 'http://127.0.0.1:3015',
      WebSocketCtor: FakeHeightPointWebSocket,
      timeoutMs: 1000,
    })

    const first = client.request({ surfaceKey: 'S', coilId: 193113, x: 1, y: 2 })
    const firstResult = first.catch((error: unknown) => error)
    const latest = client.request({ surfaceKey: 'S', coilId: 193113, x: 9, y: 10 })
    const socket = FakeHeightPointWebSocket.instances[0]

    socket.open()
    expect(socket.sent.map((message) => JSON.parse(message))).toEqual([
      { id: 2, surface_key: 'S', coil_id: '193113', x: 9, y: 10 },
    ])
    expect(await firstResult).toBeInstanceOf(HeightPointSupersededError)

    socket.emitMessage(JSON.stringify({ id: 2, value: 42 }))
    await expect(latest).resolves.toBe(42)
    client.close()
  })

  it('does not flush a timed-out queued request when the socket opens later', async () => {
    vi.useFakeTimers()
    FakeHeightPointWebSocket.instances = []
    const client = new HeightPointWebSocketClient({
      apiBaseUrl: '/api',
      wsPath: '/ws/coilData/heightPoint',
      origin: 'http://127.0.0.1:3015',
      WebSocketCtor: FakeHeightPointWebSocket,
      timeoutMs: 100,
    })

    const request = client.request({ surfaceKey: 'L', coilId: 193113, x: 3, y: 4 })
    const rejection = expect(request).rejects.toThrow('heightPoint websocket timeout')
    vi.advanceTimersByTime(100)
    await rejection

    const socket = FakeHeightPointWebSocket.instances[0]
    socket.open()
    expect(socket.sent).toEqual([])
    client.close()
  })

  it('applies reconnect backoff instead of opening sockets in a tight loop', async () => {
    vi.useFakeTimers()
    FakeHeightPointWebSocket.instances = []
    const client = new HeightPointWebSocketClient({
      apiBaseUrl: '/api',
      wsPath: '/ws/coilData/heightPoint',
      origin: 'http://127.0.0.1:3015',
      WebSocketCtor: FakeHeightPointWebSocket,
      timeoutMs: 1000,
    })

    const pending = client.request({ surfaceKey: 'S', coilId: 193113, x: 1, y: 1 })
    const failed = expect(pending).rejects.toThrow('heightPoint websocket error')
    FakeHeightPointWebSocket.instances[0].fail()
    await failed

    await expect(
      client.request({ surfaceKey: 'S', coilId: 193113, x: 2, y: 2 }),
    ).rejects.toBeInstanceOf(HeightPointReconnectBackoffError)
    expect(FakeHeightPointWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1000)
    const retried = client.request({ surfaceKey: 'S', coilId: 193113, x: 3, y: 3 })
    expect(FakeHeightPointWebSocket.instances).toHaveLength(2)
    const retrySocket = FakeHeightPointWebSocket.instances[1]
    retrySocket.open()
    retrySocket.emitMessage(JSON.stringify({ id: 3, value: 7 }))
    await expect(retried).resolves.toBe(7)
    client.close()
  })
})
