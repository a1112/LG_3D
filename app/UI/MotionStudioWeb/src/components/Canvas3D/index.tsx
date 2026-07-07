import { useRef, useEffect, useMemo, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import {
  canvas3DDataSourceLabel,
  createPointCloudGeometry,
  parseHeightData,
  resolveCanvas3DDataSource,
  type PointCloudData,
} from '@/utils'
import {
  normalizeCanvas3DZScale,
  orbitControlFlagsForMode,
  shouldResetOrbitControls,
  type Canvas3DControlMode,
} from './utils'
import './Canvas3D.css'

interface Canvas3DProps {
  data: ArrayBuffer | null
  heightLineSegments?: unknown
  errorOverlayUrl?: string
  showErrorOverlay?: boolean
  errorOverlayOpacity?: number
  resetSignal?: number
  zScale?: number
  controlMode?: Canvas3DControlMode
  thumbnail?: boolean
}

// 3D点云组件
interface PointCloudProps {
  parsedData: PointCloudData
  zScale: number
}

function PointCloud({ parsedData, zScale }: PointCloudProps) {
  const meshRef = useRef<THREE.Points>(null)

  useEffect(() => {
    if (meshRef.current && parsedData) {
      const geometry = createPointCloudGeometry(
        parsedData.positions,
        parsedData.colors
      )

      const material = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        sizeAttenuation: true,
      })

      meshRef.current.geometry.dispose()
      meshRef.current.geometry = geometry
      meshRef.current.material = material
    }
  }, [parsedData])

  return (
    <group scale={[1, 1, zScale]}>
      <points ref={meshRef} />
    </group>
  )
}

// 加载指示器
function LoadingSpinner() {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((_state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta
      meshRef.current.rotation.y += delta
    }
  })

  return (
    <>
      <mesh ref={meshRef}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#1890ff" wireframe />
      </mesh>
      <Grid args={[10, 10]} cellColor="#ccc" sectionColor="#999" fadeDistance={30} />
    </>
  )
}

// 空数据提示场景
function EmptyScene() {
  return (
    <>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[2, 2, 2]} />
        <meshStandardMaterial color="#1890ff" opacity={0.5} transparent />
      </mesh>
      <Grid args={[20, 20]} cellColor="#6f6f6f" sectionColor="#9d4b4b" />
    </>
  )
}

// 主3D场景
interface SceneProps {
  parsedData: PointCloudData | null
  isLoading: boolean
  resetSignal?: number
  zScale: number
  controlMode: Canvas3DControlMode
}

function Scene({ parsedData, isLoading, resetSignal, zScale, controlMode }: SceneProps) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  const previousResetSignalRef = useRef<number | undefined>(resetSignal)
  const orbitFlags = orbitControlFlagsForMode(controlMode)

  useEffect(() => {
    if (shouldResetOrbitControls(previousResetSignalRef.current, resetSignal)) {
      controlsRef.current?.reset()
    }
    previousResetSignalRef.current = resetSignal
  }, [resetSignal])

  return (
    <>
      <PerspectiveCamera makeDefault position={[10, 10, 10]} fov={50} />
      <OrbitControls
        ref={controlsRef}
        makeDefault
        minDistance={5}
        maxDistance={50}
        maxPolarAngle={Math.PI / 2}
        enableRotate={orbitFlags.enableRotate}
        enablePan={orbitFlags.enablePan}
        enableDamping
        dampingFactor={0.05}
      />
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} color="#ff4444" intensity={0.5} />
      <directionalLight position={[5, 10, 5]} intensity={0.8} />

      {isLoading ? (
        <LoadingSpinner />
      ) : parsedData ? (
        <PointCloud parsedData={parsedData} zScale={zScale} />
      ) : (
        <EmptyScene />
      )}
    </>
  )
}

function Canvas3D({
  data,
  heightLineSegments,
  errorOverlayUrl = '',
  showErrorOverlay = false,
  errorOverlayOpacity = 0.5,
  resetSignal,
  zScale = 0.5,
  controlMode = 'rotate',
  thumbnail = false,
}: Canvas3DProps) {
  const normalizedZScale = normalizeCanvas3DZScale(zScale)
  const Container = thumbnail ? 'span' : 'div'
  const dataSource = useMemo(
    () => resolveCanvas3DDataSource(data, heightLineSegments),
    [data, heightLineSegments],
  )
  const dataSourceLabel = canvas3DDataSourceLabel(dataSource)
  const [parsedData, setParsedData] = useState<PointCloudData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  useEffect(() => {
    setImageUrl((currentUrl) => {
      if (currentUrl) URL.revokeObjectURL(currentUrl)
      return null
    })

    if (dataSource.kind === 'buffer') {
      const data = dataSource.data
      const bytes = new Uint8Array(data)
      const isJpeg = bytes[0] === 0xff && bytes[1] === 0xd8
      const isPng =
        bytes[0] === 0x89 &&
        bytes[1] === 0x50 &&
        bytes[2] === 0x4e &&
        bytes[3] === 0x47

      if (isJpeg || isPng) {
        const blob = new Blob([data], { type: isJpeg ? 'image/jpeg' : 'image/png' })
        const nextImageUrl = URL.createObjectURL(blob)
        setImageUrl(nextImageUrl)
        setParsedData(null)
        setIsLoading(false)
        return () => URL.revokeObjectURL(nextImageUrl)
      }

      setIsLoading(true)

      // 使用 requestAnimationFrame 避免阻塞 UI
      requestAnimationFrame(() => {
        try {
          const parsed = parseHeightData(data)
          setParsedData(parsed)
        } catch (error) {
          console.error('Failed to parse 3D data:', error)
          setParsedData(null)
        } finally {
          setIsLoading(false)
        }
      })
    } else if (dataSource.kind === 'pointCloud') {
      setParsedData(dataSource.pointCloud)
      setIsLoading(false)
    } else {
      setParsedData(null)
      setIsLoading(false)
    }

    return () => {
      setImageUrl((currentUrl) => {
        if (currentUrl) URL.revokeObjectURL(currentUrl)
        return null
      })
    }
  }, [dataSource])

  if (imageUrl) {
    const shouldShowErrorOverlay = showErrorOverlay && errorOverlayUrl.trim() !== ''

    return (
      <Container
        className="canvas-3d-container"
        data-error-overlay={shouldShowErrorOverlay ? 'true' : 'false'}
        data-error-overlay-url={errorOverlayUrl}
        data-error-overlay-opacity={String(errorOverlayOpacity)}
        data-canvas-3d-z-scale={normalizedZScale.toFixed(2)}
        data-canvas-3d-control-mode={controlMode}
        data-canvas-3d-thumbnail={thumbnail ? 'true' : 'false'}
      >
        <img className="canvas-3d-image" src={imageUrl} alt="3D height render" />
        {shouldShowErrorOverlay ? (
          <img
            className="canvas-3d-error-overlay"
            src={errorOverlayUrl}
            alt="3D error overlay"
            style={{ opacity: errorOverlayOpacity }}
          />
        ) : null}
        {!thumbnail ? (
          <div className="canvas-controls">
            <small>{shouldShowErrorOverlay ? `${dataSourceLabel} / Error叠加` : dataSourceLabel}</small>
          </div>
        ) : null}
      </Container>
    )
  }

  return (
    <Container
      className="canvas-3d-container"
      data-canvas-3d-z-scale={normalizedZScale.toFixed(2)}
      data-canvas-3d-control-mode={controlMode}
      data-canvas-3d-thumbnail={thumbnail ? 'true' : 'false'}
    >
      <Canvas dpr={[1, 2]} gl={{ antialias: true, alpha: false }}>
        <Scene
          parsedData={parsedData}
          isLoading={isLoading}
          resetSignal={resetSignal}
          zScale={normalizedZScale}
          controlMode={controlMode}
        />
      </Canvas>
      {!thumbnail ? (
        <div className="canvas-controls">
          <small>
            {dataSourceLabel}: 左键旋转 | 右键平移 | 滚轮缩放
          </small>
        </div>
      ) : null}
    </Container>
  )
}

export default Canvas3D
