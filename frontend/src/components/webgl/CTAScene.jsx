import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function Aurora() {
  const ref = useRef()

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uMouse: { value: new THREE.Vector2(0.5, 0.5) },
  }), [])

  const geo = useMemo(() => new THREE.PlaneGeometry(18, 10, 80, 40), [])
  const mat = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: `
      varying vec2 vUv;
      uniform float uTime;
      uniform vec2 uMouse;
      void main() {
        vUv = uv;
        vec3 pos = position;
        float dist = length(vec2(uv.x - uMouse.x, uv.y - uMouse.y));
        pos.z += sin(pos.x * 1.5 + uTime * 0.6) * 0.25;
        pos.z += cos(pos.y * 2.0 + uTime * 0.4) * 0.2;
        pos.z += sin((pos.x + pos.y) + uTime * 0.9) * 0.15;
        pos.z += exp(-dist * 3.0) * 0.4 * sin(uTime * 3.0);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform float uTime;
      uniform vec2 uMouse;
      void main() {
        float t = uTime * 0.15;
        vec3 a = vec3(0.23, 0.51, 0.96);
        vec3 b = vec3(0.55, 0.36, 0.96);
        vec3 c = vec3(0.04, 0.71, 0.84);
        float n1 = sin(vUv.x * 6.0 + vUv.y * 4.0 + t * 3.0) * 0.5 + 0.5;
        float n2 = sin(vUv.x * 3.0 - vUv.y * 5.0 + t * 2.0) * 0.5 + 0.5;
        float n = n1 * 0.6 + n2 * 0.4;
        vec3 color = mix(a, b, n);
        color = mix(color, c, sin(vUv.y * 3.0 + t) * 0.5 + 0.5);
        float md = length(vUv - uMouse);
        color += vec3(0.1, 0.15, 0.3) * exp(-md * 4.0);
        float fadeX = smoothstep(0.0, 0.25, vUv.x) * smoothstep(1.0, 0.75, vUv.x);
        float fadeY = smoothstep(0.0, 0.2, vUv.y) * smoothstep(1.0, 0.8, vUv.y);
        float alpha = fadeX * fadeY * n * 0.35;
        gl_FragColor = vec4(color, alpha);
      }
    `,
    uniforms,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [uniforms])

  useFrame(({ clock }) => { uniforms.uTime.value = clock.elapsedTime })

  return (
    <mesh
      ref={ref}
      geometry={geo}
      material={mat}
      rotation={[-0.4, 0, 0]}
      position={[0, -0.5, -2]}
      onPointerMove={(e) => { if (e.uv) uniforms.uMouse.value.set(e.uv.x, e.uv.y) }}
    />
  )
}

function RisingParticles({ count = 50 }) {
  const ref = useRef()

  const { geo, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const speeds = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 12
      positions[i * 3 + 1] = (Math.random() - 0.5) * 8
      positions[i * 3 + 2] = (Math.random() - 0.5) * 4
      const t = Math.random()
      colors[i * 3] = 0.2 + t * 0.4; colors[i * 3 + 1] = 0.4 + t * 0.3; colors[i * 3 + 2] = 0.8 + t * 0.2
      speeds[i] = 0.005 + Math.random() * 0.015
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return { geo: g, speeds }
  }, [count])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.05, vertexColors: true, transparent: true, opacity: 0.6,
    blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  }), [])

  useFrame(({ clock }) => {
    const arr = geo.attributes.position.array
    const t = clock.elapsedTime
    for (let i = 0; i < count; i++) {
      arr[i * 3 + 1] += speeds[i]
      arr[i * 3] += Math.sin(t * 0.5 + i * 0.7) * 0.003
      if (arr[i * 3 + 1] > 5) { arr[i * 3 + 1] = -5; arr[i * 3] = (Math.random() - 0.5) * 12 }
    }
    geo.attributes.position.needsUpdate = true
  })

  return <points ref={ref} geometry={geo} material={mat} />
}

export default function CTAScene() {
  return (
    <div className="absolute inset-0 overflow-hidden" style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <Aurora />
        <RisingParticles />
      </Canvas>
    </div>
  )
}
