export interface HeightPointWebSocketRequest {
  surfaceKey: string
  coilId: number | string
  x: number
  y: number
}

export interface HeightPointWebSocketMessage {
  id: number | null
  value?: number | string
  error?: string
}

interface WebSocketLike {
  readyState: number
  onopen: (() => void) | null
  onmessage: ((event: { data: string }) => void) | null
  onerror: (() => void) | null
  onclose: (() => void) | null
  send: (message: string) => void
  close: () => void
}

interface WebSocketConstructorLike {
  new (url: string): WebSocketLike
}

export interface HeightPointWebSocketClientOptions {
  apiBaseUrl: string
  wsBaseUrl?: string
  wsPath: string
  origin?: string
  timeoutMs?: number
  WebSocketCtor?: WebSocketConstructorLike
}

interface PendingRequest {
  resolve: (value: number | string) => void
  reject: (error: Error) => void
  timer: ReturnType<typeof setTimeout>
  requestKey: string
}

interface QueuedRequest {
  id: number
  requestKey: string
  message: string
}

export class HeightPointSupersededError extends Error {
  constructor() {
    super('heightPoint request superseded')
    this.name = 'HeightPointSupersededError'
  }
}

export class HeightPointReconnectBackoffError extends Error {
  constructor() {
    super('heightPoint websocket reconnect backoff')
    this.name = 'HeightPointReconnectBackoffError'
  }
}

export function isHeightPointSupersededError(error: unknown): error is HeightPointSupersededError {
  return error instanceof HeightPointSupersededError
}

export function isHeightPointReconnectBackoffError(error: unknown): error is HeightPointReconnectBackoffError {
  return error instanceof HeightPointReconnectBackoffError
}

const OPEN_READY_STATE = 1
const CLOSED_READY_STATE = 3
const DEFAULT_TIMEOUT_MS = 1200
const RECONNECT_BASE_DELAY_MS = 1000
const RECONNECT_MAX_DELAY_MS = 30000
const defaultClientByUrl = new Map<string, HeightPointWebSocketClient>()

function normalizeSurfaceKey(surfaceKey: string): string {
  return surfaceKey.trim().toUpperCase() === 'L' ? 'L' : 'S'
}

function normalizePixelCoord(value: unknown): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 0
  return Math.max(0, Math.trunc(numberValue))
}

function normalizedOrigin(): string {
  if (typeof window !== 'undefined') return window.location.origin
  return 'http://127.0.0.1'
}

function defaultWebSocketCtor(): WebSocketConstructorLike | undefined {
  if (typeof WebSocket === 'undefined') return undefined
  return WebSocket as unknown as WebSocketConstructorLike
}

export function resolveHeightPointWsUrl(
  apiBaseUrl: string,
  wsPath: string,
  origin = normalizedOrigin(),
): string {
  const normalizedPath = wsPath.startsWith('/') ? wsPath : `/${wsPath}`
  if (/^https?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  if (/^wss?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  const url = new URL(normalizedPath, origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

export function buildHeightPointWebSocketMessage(request: HeightPointWebSocketRequest, id: number): string {
  return JSON.stringify({
    id,
    surface_key: normalizeSurfaceKey(request.surfaceKey),
    coil_id: String(request.coilId),
    x: normalizePixelCoord(request.x),
    y: normalizePixelCoord(request.y),
  })
}

export function parseHeightPointWebSocketMessage(message: string): HeightPointWebSocketMessage {
  let parsed: unknown
  try {
    parsed = JSON.parse(message)
  } catch {
    return { id: null, error: 'invalid json' }
  }

  const record = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {}
  const idValue = Number(record.id)
  const id = Number.isFinite(idValue) ? idValue : null

  if (record.error !== undefined) {
    return { id, error: String(record.error) }
  }

  const value = record.value
  if (Number.isFinite(Number(value))) {
    return {
      id,
      value: typeof value === 'number' ? value : String(value),
    }
  }

  return { id, error: 'ws no value' }
}

export class HeightPointWebSocketClient {
  private readonly options: HeightPointWebSocketClientOptions
  private socket: WebSocketLike | null = null
  private nextId = 0
  private queue: QueuedRequest[] = []
  private pending = new Map<number, PendingRequest>()
  private reconnectFailures = 0
  private nextConnectAt = 0

  constructor(options: HeightPointWebSocketClientOptions) {
    this.options = options
  }

  request(request: HeightPointWebSocketRequest): Promise<number | string> {
    const WebSocketCtor = this.options.WebSocketCtor ?? defaultWebSocketCtor()
    if (!WebSocketCtor) {
      return Promise.reject(new Error('websocket unavailable'))
    }

    const id = this.nextId + 1
    this.nextId = id
    const requestKey = `${normalizeSurfaceKey(request.surfaceKey)}:${String(request.coilId)}`
    const message = buildHeightPointWebSocketMessage(request, id)
    this.supersedePending(requestKey)
    if (!this.ensureSocket(WebSocketCtor)) {
      return Promise.reject(new HeightPointReconnectBackoffError())
    }

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        this.removeQueued(id)
        reject(new Error('heightPoint websocket timeout'))
      }, this.options.timeoutMs ?? DEFAULT_TIMEOUT_MS)
      this.pending.set(id, { resolve, reject, timer, requestKey })
      this.sendOrQueue({ id, requestKey, message })
    })
  }

  close(): void {
    const socket = this.socket
    this.socket = null
    this.rejectAll(new Error('heightPoint websocket closed'))
    socket?.close()
  }

  private ensureSocket(WebSocketCtor: WebSocketConstructorLike): boolean {
    if (this.socket && this.socket.readyState !== CLOSED_READY_STATE) return true
    this.socket = null
    if (Date.now() < this.nextConnectAt) return false

    const socket = new WebSocketCtor(this.url)
    socket.onopen = () => {
      if (this.socket !== socket) return
      this.reconnectFailures = 0
      this.nextConnectAt = 0
      this.flushQueue()
    }
    socket.onmessage = (event) => this.handleMessage(String(event.data))
    socket.onerror = () => this.failSocket(socket, new Error('heightPoint websocket error'))
    socket.onclose = () => this.failSocket(socket, new Error('heightPoint websocket closed'))
    this.socket = socket
    return true
  }

  private get url(): string {
    const baseUrl = this.options.wsBaseUrl ?? this.options.apiBaseUrl
    return resolveHeightPointWsUrl(baseUrl, this.options.wsPath, this.options.origin)
  }

  private sendOrQueue(request: QueuedRequest): void {
    if (this.socket?.readyState === OPEN_READY_STATE) {
      this.socket.send(request.message)
      return
    }
    this.queue.push(request)
  }

  private flushQueue(): void {
    const socket = this.socket
    if (!socket || socket.readyState !== OPEN_READY_STATE) return

    while (this.queue.length > 0) {
      const request = this.queue.shift() as QueuedRequest
      if (this.pending.has(request.id)) {
        socket.send(request.message)
      }
    }
  }

  private handleMessage(message: string): void {
    const parsed = parseHeightPointWebSocketMessage(message)
    if (parsed.id === null) return

    const pending = this.pending.get(parsed.id)
    if (!pending) return

    clearTimeout(pending.timer)
    this.pending.delete(parsed.id)
    if (parsed.error !== undefined) {
      pending.reject(new Error(parsed.error))
      return
    }
    pending.resolve(parsed.value as number | string)
  }

  private rejectAll(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer)
      pending.reject(error)
    }
    this.pending.clear()
    this.queue = []
  }

  private supersedePending(requestKey: string): void {
    for (const [id, pending] of this.pending.entries()) {
      if (pending.requestKey !== requestKey) continue
      clearTimeout(pending.timer)
      this.pending.delete(id)
      pending.reject(new HeightPointSupersededError())
    }
    this.queue = this.queue.filter((request) => request.requestKey !== requestKey)
  }

  private removeQueued(id: number): void {
    this.queue = this.queue.filter((request) => request.id !== id)
  }

  private failSocket(socket: WebSocketLike, error: Error): void {
    if (this.socket !== socket) return
    this.socket = null
    this.reconnectFailures += 1
    const retryDelay = Math.min(
      RECONNECT_MAX_DELAY_MS,
      RECONNECT_BASE_DELAY_MS * (2 ** Math.max(0, this.reconnectFailures - 1)),
    )
    this.nextConnectAt = Date.now() + retryDelay
    this.rejectAll(error)
    if (socket.readyState !== CLOSED_READY_STATE) {
      socket.close()
    }
  }
}

export function requestHeightPointByWebSocket(
  request: HeightPointWebSocketRequest,
  options: Omit<HeightPointWebSocketClientOptions, 'WebSocketCtor'>,
): Promise<number | string> {
  const baseUrl = options.wsBaseUrl ?? options.apiBaseUrl
  const url = resolveHeightPointWsUrl(baseUrl, options.wsPath, options.origin)
  let client = defaultClientByUrl.get(url)
  if (!client) {
    client = new HeightPointWebSocketClient(options)
    defaultClientByUrl.set(url, client)
  }
  return client.request(request)
}
