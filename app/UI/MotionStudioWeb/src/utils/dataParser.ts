/**
 * 3D数据解析工具
 * 用于解析从后端API获取的3D卷材数据
 */

import * as THREE from 'three'

/**
 * 解析ArrayBuffer格式的3D数据
 * @param buffer - 从API获取的ArrayBuffer数据
 * @returns 解析后的点云数据
 */
export function parseHeightData(buffer: ArrayBuffer): {
  positions: Float32Array
  colors: Float32Array
  count: number
} | null {
  try {
    // TODO: 根据实际后端数据格式实现解析逻辑
    // 这里需要参考 app/Server/api/ApiDataServer.py 中的数据格式

    // 示例：假设数据格式为每4个float表示一个点(x, y, z, color)
    const dataView = new DataView(buffer)
    const floatSize = 4 // float32 size
    const pointStride = 4 // x, y, z, color

    const count = buffer.byteLength / (floatSize * pointStride)
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      const offset = i * pointStride * floatSize

      const x = dataView.getFloat32(offset, true) // little-endian
      const y = dataView.getFloat32(offset + floatSize, true)
      const z = dataView.getFloat32(offset + floatSize * 2, true)
      const colorValue = dataView.getFloat32(offset + floatSize * 3, true)

      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z

      // 将高度值映射到颜色
      const color = heightToColor(z)
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    return { positions, colors, count }
  } catch (error) {
    console.error('Failed to parse height data:', error)
    return null
  }
}

/**
 * 将高度值映射到颜色
 * @param height - 高度值
 * @returns RGB颜色值 (0-1)
 */
export function heightToColor(height: number): { r: number; g: number; b: number } {
  // 定义高度范围（根据实际情况调整）
  const minHeight = -10
  const maxHeight = 10

  // 归一化到 0-1
  const normalized = (height - minHeight) / (maxHeight - minHeight)
  const clamped = Math.max(0, Math.min(1, normalized))

  // 使用热力图颜色方案：蓝 -> 绿 -> 黄 -> 红
  if (clamped < 0.25) {
    // 蓝到绿
    const t = clamped / 0.25
    return { r: 0, g: t, b: 1 - t }
  } else if (clamped < 0.5) {
    // 绿到黄
    const t = (clamped - 0.25) / 0.25
    return { r: t, g: 1, b: 0 }
  } else if (clamped < 0.75) {
    // 黄到红
    const t = (clamped - 0.5) / 0.25
    return { r: 1, g: 1 - t, b: 0 }
  } else {
    // 红到紫
    const t = (clamped - 0.75) / 0.25
    return { r: 1, g: 0, b: t }
  }
}

/**
 * 创建3D点云几何体
 * @param positions - 位置数组
 * @param colors - 颜色数组
 * @returns THREE.BufferGeometry
 */
export function createPointCloudGeometry(
  positions: Float32Array,
  colors: Float32Array
): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry()

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

  geometry.computeBoundingSphere()
  geometry.computeBoundingBox()

  return geometry
}

/**
 * 从图像数据创建高度图
 * @param imageElement - 图像元素
 * @returns 高度数据数组
 */
export async function imageToHeightMap(
  imageElement: HTMLImageElement
): Promise<Float32Array> {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')!

    canvas.width = imageElement.width
    canvas.height = imageElement.height

    ctx.drawImage(imageElement, 0, 0)

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const pixels = imageData.data

    const heightMap = new Float32Array(canvas.width * canvas.height)

    // 使用亮度值作为高度
    for (let i = 0; i < heightMap.length; i++) {
      const r = pixels[i * 4]
      const g = pixels[i * 4 + 1]
      const b = pixels[i * 4 + 2]

      // 转换为灰度值
      heightMap[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    }

    resolve(heightMap)
  })
}

/**
 * 从高度图创建3D点云
 * @param heightMap - 高度图数据
 * @param width - 宽度
 * @param height - 高度
 * @param scale - 缩放因子
 */
export function heightMapToPointCloud(
  heightMap: Float32Array,
  width: number,
  height: number,
  scale: { x: number; y: number; z: number } = { x: 1, y: 1, z: 1 }
): {
  positions: Float32Array
  colors: Float32Array
  count: number
} {
  const positions = new Float32Array(width * height * 3)
  const colors = new Float32Array(width * height * 3)

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x
      const heightValue = heightMap[i]

      // 位置坐标（以中心为原点）
      positions[i * 3] = (x - width / 2) * scale.x
      positions[i * 3 + 1] = (y - height / 2) * scale.y
      positions[i * 3 + 2] = heightValue * scale.z

      // 颜色
      const color = heightToColor(heightValue)
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }
  }

  return {
    positions,
    colors,
    count: width * height,
  }
}
