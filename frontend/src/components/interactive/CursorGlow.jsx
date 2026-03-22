import { useEffect, useRef } from 'react'

/*
  Ambient cursor glow that follows mouse across the page.
  Large soft radial gradient attached to cursor position.
*/
export default function CursorGlow() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let x = 0, y = 0, targetX = 0, targetY = 0

    const onMove = (e) => {
      targetX = e.clientX
      targetY = e.clientY
    }

    const animate = () => {
      x += (targetX - x) * 0.08
      y += (targetY - y) * 0.08
      el.style.transform = `translate(${x - 300}px, ${y - 300}px)`
      requestAnimationFrame(animate)
    }

    window.addEventListener('mousemove', onMove)
    const raf = requestAnimationFrame(animate)
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div
      ref={ref}
      className="fixed top-0 left-0 pointer-events-none z-0"
      style={{
        width: 600,
        height: 600,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(59,130,246,0.06) 0%, rgba(139,92,246,0.03) 40%, transparent 70%)',
        willChange: 'transform',
      }}
    />
  )
}
