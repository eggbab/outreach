import { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

function NetworkGlobe({ mouse, clicked }) {
  const pointsRef = useRef()
  const linesRef = useRef()
  const count = 200
  const maxLines = 2000

  const { basePos, colors } = useMemo(() => {
    const basePos = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const palette = [
      [0.23, 0.51, 0.96], [0.42, 0.36, 0.96], [0.04, 0.71, 0.84],
      [0.06, 0.72, 0.51], [0.96, 0.62, 0.04], [0.93, 0.31, 0.47],
    ]
    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / count)
      const theta = Math.PI * (1 + Math.sqrt(5)) * i
      const r = 2.8 + (Math.random() - 0.5) * 0.5
      basePos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      basePos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      basePos[i * 3 + 2] = r * Math.cos(phi)
      const c = palette[i % palette.length]
      colors[i * 3] = c[0]; colors[i * 3 + 1] = c[1]; colors[i * 3 + 2] = c[2]
    }
    return { basePos, colors }
  }, [])

  const pointsGeo = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(basePos), 3))
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(colors), 3))
    return geo
  }, [basePos, colors])

  const lineGeo = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(maxLines * 6), 3))
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(maxLines * 6), 3))
    geo.setDrawRange(0, 0)
    return geo
  }, [])

  const pointsMat = useMemo(() => new THREE.PointsMaterial({
    size: 0.07, vertexColors: true, transparent: true, opacity: 0.9,
    sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false,
  }), [])

  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
  }), [])

  const shockwave = useRef({ active: false, time: 0, ox: 0, oy: 0 })

  useFrame(({ clock }) => {
    const pos = pointsGeo.attributes.position.array
    const t = clock.elapsedTime

    if (clicked.current) {
      shockwave.current = { active: true, time: t, ox: mouse.current.x * 4, oy: mouse.current.y * 3 }
      clicked.current = false
    }
    const sw = shockwave.current
    const swAge = sw.active ? t - sw.time : 99

    for (let i = 0; i < count; i++) {
      const angle = t * 0.08
      const ca = Math.cos(angle), sa = Math.sin(angle)
      let rx = basePos[i * 3] * ca - basePos[i * 3 + 2] * sa
      let rz = basePos[i * 3] * sa + basePos[i * 3 + 2] * ca
      let ry = basePos[i * 3 + 1]
      const b = 1 + Math.sin(t * 0.5) * 0.03
      rx *= b; ry *= b; rz *= b
      rx += Math.sin(t * 0.3 + i * 0.1) * 0.07
      ry += Math.cos(t * 0.25 + i * 0.13) * 0.07

      if (mouse.current) {
        const mx = mouse.current.x * 5, my = mouse.current.y * 3.5
        const dx = rx - mx, dy = ry - my
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 2.5 && dist > 0.01) {
          const force = (2.5 - dist) * 0.12
          rx += (dx / dist) * force; ry += (dy / dist) * force
        }
      }

      if (sw.active && swAge < 2) {
        const sdx = rx - sw.ox, sdy = ry - sw.oy
        const sd = Math.sqrt(sdx * sdx + sdy * sdy)
        const wf = swAge * 4
        if (Math.abs(sd - wf) < 0.8 && sd > 0.01) {
          const int = (1 - Math.abs(sd - wf) / 0.8) * (1 - swAge / 2) * 0.5
          rx += (sdx / sd) * int; ry += (sdy / sd) * int
        }
      }

      pos[i * 3] = rx; pos[i * 3 + 1] = ry; pos[i * 3 + 2] = rz
    }
    pointsGeo.attributes.position.needsUpdate = true

    // Lines
    const lp = lineGeo.attributes.position.array
    const lc = lineGeo.attributes.color.array
    let li = 0
    for (let i = 0; i < count && li < maxLines; i++) {
      for (let j = i + 1; j < count && li < maxLines; j++) {
        const dx = pos[i * 3] - pos[j * 3], dy = pos[i * 3 + 1] - pos[j * 3 + 1], dz = pos[i * 3 + 2] - pos[j * 3 + 2]
        const d = Math.sqrt(dx * dx + dy * dy + dz * dz)
        if (d < 1.2) {
          const a = (1 - d / 1.2) * 0.4
          lp[li * 6] = pos[i * 3]; lp[li * 6 + 1] = pos[i * 3 + 1]; lp[li * 6 + 2] = pos[i * 3 + 2]
          lp[li * 6 + 3] = pos[j * 3]; lp[li * 6 + 4] = pos[j * 3 + 1]; lp[li * 6 + 5] = pos[j * 3 + 2]
          lc[li * 6] = colors[i * 3] * a; lc[li * 6 + 1] = colors[i * 3 + 1] * a; lc[li * 6 + 2] = colors[i * 3 + 2] * a
          lc[li * 6 + 3] = colors[j * 3] * a; lc[li * 6 + 4] = colors[j * 3 + 1] * a; lc[li * 6 + 5] = colors[j * 3 + 2] * a
          li++
        }
      }
    }
    lineGeo.setDrawRange(0, li * 2)
    lineGeo.attributes.position.needsUpdate = true
    lineGeo.attributes.color.needsUpdate = true
  })

  return (
    <>
      <points ref={pointsRef} geometry={pointsGeo} material={pointsMat} />
      <lineSegments ref={linesRef} geometry={lineGeo} material={lineMat} />
    </>
  )
}

function PulseRings() {
  const groupRef = useRef()
  const rings = useMemo(() => [0, 1, 2, 3].map(() => {
    const geo = new THREE.RingGeometry(2.7, 2.85, 64)
    const mat = new THREE.MeshBasicMaterial({
      color: '#3b82f6', transparent: true, opacity: 0.15,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    })
    return new THREE.Mesh(geo, mat)
  }), [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    rings.forEach((ring, i) => {
      const t = clock.elapsedTime
      const scale = 1 + ((t * 0.4 + i * 1.5) % 3) * 1.2
      const opacity = Math.max(0, 1 - ((t * 0.4 + i * 1.5) % 3) / 3) * 0.15
      ring.scale.setScalar(scale)
      ring.material.opacity = opacity
    })
  })

  return (
    <group ref={groupRef} rotation={[Math.PI / 2, 0, 0]}>
      {rings.map((ring, i) => <primitive key={i} object={ring} />)}
    </group>
  )
}

function DataPackets({ count = 12 }) {
  const groupRef = useRef()
  const packets = useMemo(() => {
    const arr = []
    const colors = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981']
    for (let i = 0; i < count; i++) {
      const geo = new THREE.BoxGeometry(0.1, 0.05, 0.03)
      const mat = new THREE.MeshBasicMaterial({
        color: colors[i % colors.length], transparent: true, opacity: 0.7,
        blending: THREE.AdditiveBlending, depthWrite: false,
      })
      const mesh = new THREE.Mesh(geo, mat)
      arr.push({ mesh, angle: (i / count) * Math.PI * 2, radius: 3.2 + Math.random() * 0.8, speed: 0.15 + Math.random() * 0.25, y: (Math.random() - 0.5) * 2 })
    }
    return arr
  }, [count])

  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    packets.forEach((p) => {
      const a = p.angle + t * p.speed
      p.mesh.position.set(Math.cos(a) * p.radius, p.y + Math.sin(t + p.angle) * 0.3, Math.sin(a) * p.radius)
    })
  })

  return (
    <group ref={groupRef}>
      {packets.map((p, i) => <primitive key={i} object={p.mesh} />)}
    </group>
  )
}

function Scene({ mouse, clicked }) {
  const { camera } = useThree()
  useFrame(() => {
    if (mouse.current) {
      camera.position.x += (mouse.current.x * 0.8 - camera.position.x) * 0.03
      camera.position.y += (mouse.current.y * 0.5 + 0.5 - camera.position.y) * 0.03
      camera.lookAt(0, 0, 0)
    }
  })
  return (
    <>
      <NetworkGlobe mouse={mouse} clicked={clicked} />
      <PulseRings />
      <DataPackets />
    </>
  )
}

export default function HeroScene() {
  const mouse = useRef({ x: 0, y: 0 })
  const clicked = useRef(false)
  return (
    <div
      className="absolute inset-0"
      style={{ zIndex: 0 }}
      onMouseMove={(e) => {
        mouse.current = { x: (e.clientX / window.innerWidth) * 2 - 1, y: -(e.clientY / window.innerHeight) * 2 + 1 }
      }}
      onClick={() => { clicked.current = true }}
    >
      <Canvas
        camera={{ position: [0, 0.5, 7], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <Scene mouse={mouse} clicked={clicked} />
      </Canvas>
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 80% 70% at 50% 45%, transparent 25%, rgba(255,255,255,0.82) 65%, white 100%)'
      }} />
    </div>
  )
}
