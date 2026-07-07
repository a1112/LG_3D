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
}

const OPEN_READY_STATE = 1
const CLOSED_READY_STATE = 3
const DEFAULT_TIMEOUT_MS = 1200
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
  private queue: string[] = []
  private pending = new Map<number, PendingRequest>()

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
    const message = buildHeightPointWebSocketMessage(request, id)
    this.ensureSocket(WebSocketCtor)

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error('heightPoint websocket timeout'))
      }, this.options.timeoutMs ?? DEFAULT_TIMEOUT_MS)
      this.pending.set(id, { resolve, reject, timer })
      this.sendOrQueue(message)
    })
  }

  close(): void {
    this.socket?.close()
    this.socket = null
    this.queue = []
  }

  private ensureSocket(WebSocketCtor: WebSocketConstructorLike): void {
    if (this.socket && this.socket.readyState !== CLOSED_READY_STATE) return

    const socket = new WebSocketCtor(this.url)
    socket.onopen = () => this.flushQueue()
    socket.onmessage = (event) => this.handleMessage(String(event.data))
    socket.onerror = () => this.rejectAll(new Error('heightPoint websocket error'))
    socket.onclose = () => {
      this.socket = null
      this.rejectAll(new Error('heightPoint websocket closed'))
    }
    this.socket = socket
  }

  private get url(): string {
    const baseUrl = this.options.wsBaseUrl ?? this.options.apiBaseUrl
    return resolveHeightPointWsUrl(baseUrl, this.options.wsPath, this.options.origin)
  }

  private sendOrQueue(message: string): void {
    if (this.socket?.readyState === OPEN_READY_STATE) {
      this.socket.send(message)
      return
    }
    this.queue.push(message)
  }

  private flushQueue(): void {
    const socket = this.socket
    if (!socket || socket.readyState !== OPEN_READY_STATE) return

    while (this.queue.length > 0) {
      socket.send(this.queue.shift() as string)
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
