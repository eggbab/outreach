import { useRef, useMemo, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const STAGES = [
  { name: '수집', x: -4, color: [0.42, 0.45, 0.50], width: 2.4 },
  { name: '발송', x: -2, color: [0.23, 0.51, 0.96], width: 2.0 },
  { name: '분석', x: 0, color: [0.55, 0.36, 0.96], width: 1.6 },
  { name: '제안', x: 2, color: [0.96, 0.62, 0.04], width: 1.2 },
  { name: '성사', x: 4, color: [0.02, 0.71, 0.39], width: 0.8 },
]

function Particles({ count = 250, hoveredStage, clickedStage }) {
  const ref = useRef()

  const stageIdx = useMemo(() => new Int32Array(count), [count])
  const speeds = useMemo(() => {
    const s = new Float32Array(count)
    for (let i = 0; i < count; i++) s[i] = 0.003 + Math.random() * 0.008
    return s
  }, [count])

  const geo = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const si = Math.floor(Math.random() * 5)
      stageIdx[i] = si
      const s = STAGES[si]
      positions[i * 3] = s.x + (Math.random() - 0.5) * 1.5
      positions[i * 3 + 1] = (Math.random() - 0.5) * s.width
      positions[i * 3 + 2] = (Math.random() - 0.5) * 1.5
      colors[i * 3] = s.color[0]; colors[i * 3 + 1] = s.color[1]; colors[i * 3 + 2] = s.color[2]
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [count, stageIdx])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.09, vertexColors: true, transparent: true, opacity: 0.85,
    sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false,
  }), [])

  const burst = useRef({ active: false, time: 0, stage: -1 })

  useFrame(({ clock }) => {
    const pos = geo.attributes.position.array
    const col = geo.attributes.color.array
    const t = clock.elapsedTime

    if (clickedStage.current >= 0) {
      burst.current = { active: true, time: t, stage: clickedStage.current }
      clickedStage.current = -1
    }
    const b = burst.current
    const bAge = b.active ? t - b.time : 99

    for (let i = 0; i < count; i++) {
      const si = stageIdx[i]
      const s = STAGES[si]
      pos[i * 3] += speeds[i]
      pos[i * 3 + 1] += Math.sin(t + i * 0.5) * 0.002

      if (hoveredStage.current === si) {
        pos[i * 3 + 1] += Math.sin(t * 3 + i) * 0.003
        col[i * 3] = Math.min(s.color[0] + 0.3, 1)
        col[i * 3 + 1] = Math.min(s.color[1] + 0.3, 1)
        col[i * 3 + 2] = Math.min(s.color[2] + 0.3, 1)
      } else {
        col[i * 3] += (s.color[0] - col[i * 3]) * 0.05
        col[i * 3 + 1] += (s.color[1] - col[i * 3 + 1]) * 0.05
        col[i * 3 + 2] += (s.color[2] - col[i * 3 + 2]) * 0.05
      }

      if (b.active && b.stage === si && bAge < 1.5) {
        const dx = pos[i * 3] - s.x, dy = pos[i * 3 + 1]
        const d = Math.sqrt(dx * dx + dy * dy) + 0.1
        const force = (1 - bAge / 1.5) * 0.08
        pos[i * 3] += (dx / d) * force; pos[i * 3 + 1] += (dy / d) * force
      }

      if (pos[i * 3] > s.x + 1) {
        const nsi = (si + 1) % 5
        stageIdx[i] = nsi
        const ns = STAGES[nsi]
        pos[i * 3] = ns.x - 0.8
        pos[i * 3 + 1] = (Math.random() - 0.5) * ns.width
        pos[i * 3 + 2] = (Math.random() - 0.5) * 1.5
      }
    }
    geo.attributes.position.needsUpdate = true
    geo.attributes.color.needsUpdate = true
  })

  return <points ref={ref} geometry={geo} material={mat} />
}

function StageZones({ onHover, onClick }) {
  const zones = useMemo(() => STAGES.map((s) => {
    const geo = new THREE.PlaneGeometry(1.8, s.width * 1.2)
    const mat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.set(s.x, 0, 0)
    return mesh
  }), [])

  return (
    <group>
      {zones.map((mesh, i) => (
        <primitive
          key={i}
          object={mesh}
          onPointerEnter={() => onHover(i)}
          onPointerLeave={() => onHover(-1)}
          onClick={() => onClick(i)}
        />
      ))}
    </group>
  )
}

function FunnelOutline() {
  const geo = useMemo(() => {
    const pts = [
      ...STAGES.map(s => new THREE.Vector3(s.x, s.width / 2, 0)),
      ...STAGES.map(s => new THREE.Vector3(s.x, -s.width / 2, 0)).reverse(),
    ]
    pts.push(pts[0].clone())
    return new THREE.BufferGeometry().setFromPoints(pts)
  }, [])
  const mat = useMemo(() => new THREE.LineBasicMaterial({ color: '#d1d5db', transparent: true, opacity: 0.3 }), [])
  return <line geometry={geo} material={mat} />
}

export default function PipelineScene() {
  const hoveredStage = useRef(-1)
  const clickedStage = useRef(-1)
  const [hoverLabel, setHoverLabel] = useState(-1)

  return (
    <div className="relative w-full h-56 sm:h-72">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <Particles count={250} hoveredStage={hoveredStage} clickedStage={clickedStage} />
        <FunnelOutline />
        <StageZones
          onHover={(i) => { hoveredStage.current = i; setHoverLabel(i) }}
          onClick={(i) => { clickedStage.current = i }}
        />
      </Canvas>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between px-[8%] sm:px-[10%] pb-2 pointer-events-none">
        {STAGES.map((s, i) => (
          <span key={s.name} className={`text-[11px] font-medium transition-all duration-300 ${hoverLabel === i ? 'text-gray-900 scale-110' : 'text-gray-400'}`}>
            {s.name}
          </span>
        ))}
      </div>
      {hoverLabel >= 0 && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg pointer-events-none">
          클릭해서 {STAGES[hoverLabel].name} 단계를 터뜨려보세요
        </div>
      )}
    </div>
  )
}
