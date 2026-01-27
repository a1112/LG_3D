/**
 * 数据加载优先级管理器
 * 实现分阶段加载策略：
 * 1. 优先加载大的图像（Render 图像）
 * 2. 然后是缺陷数据和缺陷图像
 * 3. 最后是 3D 数据（高度数据/点数据）
 */

export type LoadPriority = 'image' | 'defect' | '3d'
export type LoadState = 'pending' | 'loading' | 'loaded' | 'error'

export interface LoadTask {
  id: string
  priority: LoadPriority
  loadFn: () => Promise<any>
  state: LoadState
  error?: Error
}

class DataLoaderManager {
  private queue: Map<string, LoadTask> = new Map()
  private activeTasks: Set<string> = new Set()
  private currentPriority: LoadPriority | null = null
  private maxConcurrentTasks = 3

  /**
   * 添加加载任务到队列
   */
  addTask(id: string, priority: LoadPriority, loadFn: () => Promise<any>): void {
    if (this.queue.has(id)) {
      console.log(`[DataLoader] Task ${id} already exists, skipping`)
      return
    }

    this.queue.set(id, {
      id,
      priority,
      loadFn,
      state: 'pending',
    })

    console.log(`[DataLoader] Added task ${id} with priority ${priority}`)
    this.processQueue()
  }

  /**
   * 移除任务
   */
  removeTask(id: string): void {
    this.queue.delete(id)
    this.activeTasks.delete(id)
  }

  /**
   * 获取任务状态
   */
  getTaskState(id: string): LoadState | undefined {
    return this.queue.get(id)?.state
  }

  /**
   * 处理队列
   */
  private processQueue(): void {
    // 如果当前有任务在执行，且达到最大并发数，则不启动新任务
    if (this.activeTasks.size >= this.maxConcurrentTasks) {
      return
    }

    // 确定当前应该加载的优先级
    const nextPriority = this.getNextPriority()
    if (!nextPriority || nextPriority === this.currentPriority) {
      // 没有新任务或优先级未变
      if (this.activeTasks.size < this.maxConcurrentTasks && nextPriority) {
        // 还有空间，继续加载当前优先级的任务
        this.startNextTask(nextPriority)
      }
      return
    }

    // 优先级改变，切换到新优先级
    console.log(`[DataLoader] Switching priority from ${this.currentPriority} to ${nextPriority}`)
    this.currentPriority = nextPriority

    // 启动新优先级的第一个任务
    this.startNextTask(nextPriority)
  }

  /**
   * 获取下一个应该加载的优先级
   */
  private getNextPriority(): LoadPriority | null {
    // 优先级顺序: image -> defect -> 3d
    const priorities: LoadPriority[] = ['image', 'defect', '3d']

    for (const priority of priorities) {
      const hasPendingTask = Array.from(this.queue.values()).some(
        task => task.priority === priority && task.state === 'pending'
      )

      if (hasPendingTask) {
        return priority
      }
    }

    return null
  }

  /**
   * 启动下一个任务
   */
  private async startNextTask(priority: LoadPriority): Promise<void> {
    // 查找该优先级下的第一个待处理任务
    const tasks = Array.from(this.queue.values())
    const nextTask = tasks.find(
      task => task.priority === priority && task.state === 'pending'
    )

    if (!nextTask) {
      return
    }

    // 标记为加载中
    nextTask.state = 'loading'
    this.activeTasks.add(nextTask.id)
    this.queue.set(nextTask.id, nextTask)

    try {
      console.log(`[DataLoader] Starting task ${nextTask.id} (priority: ${priority})`)
      await nextTask.loadFn()

      // 加载成功
      nextTask.state = 'loaded'
      this.queue.set(nextTask.id, nextTask)
      console.log(`[DataLoader] Completed task ${nextTask.id}`)

      // 触发加载完成回调
      if (this.onTaskComplete) {
        this.onTaskComplete(nextTask)
      }
    } catch (error) {
      // 加载失败
      nextTask.state = 'error'
      nextTask.error = error as Error
      this.queue.set(nextTask.id, nextTask)
      console.error(`[DataLoader] Failed task ${nextTask.id}:`, error)

      // 触发失败回调
      if (this.onTaskError) {
        this.onTaskError(nextTask, error as Error)
      }
    } finally {
      // 从活动任务中移除
      this.activeTasks.delete(nextTask.id)

      // 继续处理队列
      this.processQueue()
    }
  }

  /**
   * 任务完成回调
   */
  onTaskComplete?: (task: LoadTask) => void

  /**
   * 任务失败回调
   */
  onTaskError?: (task: LoadTask, error: Error) => void

  /**
   * 清空所有任务
   */
  clear(): void {
    this.queue.clear()
    this.activeTasks.clear()
    this.currentPriority = null
  }
}

// 创建全局单例
export const dataLoader = new DataLoaderManager()

/**
 * React Hook - 使用数据加载器
 */
export interface UseDataLoaderOptions {
  coilId: number
  surfaceKey: string
  onImageLoaded?: () => void
  onDefectLoaded?: () => void
  on3dLoaded?: () => void
  onError?: (error: Error) => void
}

export function useDataLoader(options: UseDataLoaderOptions) {
  const {
    coilId,
    surfaceKey,
    onImageLoaded,
    onDefectLoaded,
    on3dLoaded,
    onError,
  } = options

  /**
   * 加载图像数据（最高优先级）
   */
  const loadImage = (loadFn: () => Promise<any>) => {
    const taskId = `image_${coilId}_${surfaceKey}`
    dataLoader.addTask(taskId, 'image', async () => {
      const result = await loadFn()
      onImageLoaded?.()
      return result
    })
  }

  /**
   * 加载缺陷数据（中等优先级）
   */
  const loadDefect = (loadFn: () => Promise<any>) => {
    const taskId = `defect_${coilId}_${surfaceKey}`
    dataLoader.addTask(taskId, 'defect', async () => {
      const result = await loadFn()
      onDefectLoaded?.()
      return result
    })
  }

  /**
   * 加载 3D 数据（最低优先级）
   */
  const load3d = (loadFn: () => Promise<any>) => {
    const taskId = `3d_${coilId}_${surfaceKey}`
    dataLoader.addTask(taskId, '3d', async () => {
      const result = await loadFn()
      on3dLoaded?.()
      return result
    })
  }

  /**
   * 清理当前 coil 的所有任务
   */
  const cleanup = () => {
    const imageTaskId = `image_${coilId}_${surfaceKey}`
    const defectTaskId = `defect_${coilId}_${surfaceKey}`
    const threeDTaskId = `3d_${coilId}_${surfaceKey}`

    dataLoader.removeTask(imageTaskId)
    dataLoader.removeTask(defectTaskId)
    dataLoader.removeTask(threeDTaskId)
  }

  return {
    loadImage,
    loadDefect,
    load3d,
    cleanup,
  }
}

/**
 * 配置数据加载延迟
 */
export const LOAD_DELAYS = {
  /**
   * 图像加载后的延迟（缺陷数据加载前）
   */
  imageToDefect: 1000, // 1秒后加载缺陷

  /**
   * 缺陷数据加载后的延迟（3D 数据加载前）
   */
  defectTo3d: 2000, // 2秒后加载 3D 数据
}
