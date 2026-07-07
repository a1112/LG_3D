export interface ClipboardCopyOptions {
  writeText?: (text: string) => Promise<void>
  fallbackCopy?: (text: string) => boolean
  timeoutMs?: number
}

function copyWithTextArea(text: string): boolean {
  if (typeof document === 'undefined' || !document.body) return false

  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '0'
  document.body.appendChild(textArea)
  textArea.select()

  try {
    return document.execCommand('copy')
  } finally {
    document.body.removeChild(textArea)
  }
}

async function withTimeout(promise: Promise<void>, timeoutMs: number): Promise<void> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<void>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error('Clipboard write timed out')), timeoutMs)
  })

  try {
    await Promise.race([promise, timeout])
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId)
  }
}

export async function copyTextToClipboard(text: string, options: ClipboardCopyOptions = {}): Promise<boolean> {
  const nativeClipboard = typeof navigator === 'undefined' ? undefined : navigator.clipboard
  const writeText = options.writeText ?? nativeClipboard?.writeText?.bind(nativeClipboard)
  const fallbackCopy = options.fallbackCopy ?? copyWithTextArea
  const timeoutMs = options.timeoutMs ?? 800
  const tryFallback = () => {
    try {
      return fallbackCopy(text)
    } catch {
      return false
    }
  }

  if (writeText) {
    try {
      await withTimeout(writeText(text), timeoutMs)
      return true
    } catch {
      return tryFallback()
    }
  }

  return tryFallback()
}
