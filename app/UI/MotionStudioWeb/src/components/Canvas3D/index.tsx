import { useRef, useEffect, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import { parseHeightData, createPointCloudGeometry } from '@/utils'
import './Canvas3D.css'

interface Canvas3DProps {
  data: ArrayBuffer | null
}

// 3D点云组件
interface PointCloudProps {
  parsedData: ReturnType<typeof parseHeightData>
}

function PointCloud({ parsedData }: PointCloudProps) {
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

  return <points ref={meshRef} />
}

// 加载指示器
function LoadingSpinner() {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state, delta) => {
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
  parsedData: ReturnType<typeof parseHeightData>
  isLoading: boolean
}

function Scene({ parsedData, isLoading }: SceneProps) {
  return (
    <>
      <PerspectiveCamera makeDefault position={[10, 10, 10]} fov={50} />
      <OrbitControls
        makeDefault
        minDistance={5}
        maxDistance={50}
        maxPolarAngle={Math.PI / 2}
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
        <PointCloud parsedData={parsedData} />
      ) : (
        <EmptyScene />
      )}
    </>
  )
}

function Canvas3D({ data }: Canvas3DProps) {
  const [parsedData, setParsedData] = useState<ReturnType<typeof parseHeightData>>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (data) {
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
    } else {
      setParsedData(null)
      setIsLoading(false)
    }
  }, [data])

  return (
    <div className="canvas-3d-container">
      <Canvas dpr={[1, 2]} gl={{ antialias: true, alpha: false }}>
        <Scene parsedData={parsedData} isLoading={isLoading} />
      </Canvas>
      <div className="canvas-controls">
        <small>
          操作说明: 左键旋转 | 右键平移 | 滚轮缩放
        </small>
      </div>
    </div>
  )
}

export default Canvas3D
