import { useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function GradientWave() {
  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), [])

  const geo = useMemo(() => new THREE.PlaneGeometry(20, 12, 40, 20), [])
  const mat = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: `
      varying vec2 vUv;
      uniform float uTime;
      void main() {
        vUv = uv;
        vec3 pos = position;
        pos.z = sin(pos.x * 1.2 + uTime * 0.3) * cos(pos.y * 0.8 + uTime * 0.2) * 0.3;
        pos.z += sin(pos.x * 0.5 + pos.y * 0.7 + uTime * 0.5) * 0.2;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform float uTime;
      void main() {
        vec3 c1 = vec3(0.96, 0.96, 0.97);
        vec3 c2 = vec3(0.92, 0.94, 0.98);
        vec3 c3 = vec3(0.94, 0.92, 0.98);
        float n = sin(vUv.x * 3.0 + uTime * 0.2) * 0.5 + 0.5;
        vec3 color = mix(c1, c2, n);
        color = mix(color, c3, sin(vUv.y * 2.0 + uTime * 0.15) * 0.5 + 0.5);
        gl_FragColor = vec4(color, 0.6);
      }
    `,
    uniforms,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false,
  }), [uniforms])

  useFrame(({ clock }) => { uniforms.uTime.value = clock.elapsedTime })

  return <mesh geometry={geo} material={mat} rotation={[-0.5, 0, 0]} position={[0, -1, -2]} />
}

export default function WaveScene() {
  return (
    <div className="absolute inset-0 overflow-hidden" style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <GradientWave />
      </Canvas>
    </div>
  )
}
