import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function DotGrid({ rows = 25, cols = 40 }) {
  const ref = useRef()
  const count = rows * cols
  const mouse = useRef({ x: 999, y: 999 })

  const basePositions = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        const idx = (i * cols + j) * 3
        arr[idx] = (j - cols / 2) * 0.4
        arr[idx + 1] = (i - rows / 2) * 0.4
        arr[idx + 2] = 0
      }
    }
    return arr
  }, [rows, cols, count])

  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(basePositions), 3))
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(count * 3).fill(0.8), 3))
    return g
  }, [basePositions, count])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.04, vertexColors: true, transparent: true, opacity: 0.7, sizeAttenuation: true, depthWrite: false,
  }), [])

  useFrame(({ clock }) => {
    const pos = geo.attributes.position.array
    const col = geo.attributes.color.array
    const t = clock.elapsedTime
    const mx = mouse.current.x, my = mouse.current.y

    for (let i = 0; i < count; i++) {
      const bx = basePositions[i * 3], by = basePositions[i * 3 + 1]
      let z = Math.sin(bx * 0.6 + t * 0.4) * Math.cos(by * 0.5 + t * 0.3) * 0.25

      const dx = bx - mx, dy = by - my
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 4) {
        z += Math.sin(dist * 3 - t * 4) * (1 - dist / 4) * 0.4
        const intensity = 1 - dist / 4
        col[i * 3] = 0.78 - intensity * 0.55
        col[i * 3 + 1] = 0.8 - intensity * 0.3
        col[i * 3 + 2] = 0.84 + intensity * 0.16
      } else {
        col[i * 3] += (0.78 - col[i * 3]) * 0.02
        col[i * 3 + 1] += (0.8 - col[i * 3 + 1]) * 0.02
        col[i * 3 + 2] += (0.84 - col[i * 3 + 2]) * 0.02
      }
      pos[i * 3 + 2] = z
    }
    geo.attributes.position.needsUpdate = true
    geo.attributes.color.needsUpdate = true
  })

  // Invisible hit plane for pointer events
  const hitGeo = useMemo(() => new THREE.PlaneGeometry(20, 12), [])
  const hitMat = useMemo(() => new THREE.MeshBasicMaterial({ transparent: true, opacity: 0 }), [])

  return (
    <>
      <points ref={ref} geometry={geo} material={mat} />
      <mesh
        geometry={hitGeo}
        material={hitMat}
        position={[0, 0, -0.1]}
        onPointerMove={(e) => { if (e.point) mouse.current = { x: e.point.x, y: e.point.y } }}
        onPointerLeave={() => { mouse.current = { x: 999, y: 999 } }}
      />
    </>
  )
}

export default function FloatingGrid() {
  return (
    <div className="absolute inset-0 overflow-hidden" style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 7], fov: 40 }}
        dpr={[1, 1.5]}
        gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <DotGrid />
      </Canvas>
    </div>
  )
}
