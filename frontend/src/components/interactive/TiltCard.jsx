import { useRef, useCallback } from 'react'

/*
  Card with subtle glow that follows cursor on hover.
  No tilt/rotation — only radial glow effect.
*/
export default function TiltCard({ children, className = '', glowColor = 'rgba(59,130,246,0.15)' }) {
  const glowRef = useRef(null)

  const handleMouseMove = useCallback((e) => {
    const glow = glowRef.current
    if (!glow) return
    const rect = glow.parentElement.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    glow.style.opacity = '1'
    glow.style.background = `radial-gradient(circle at ${x}px ${y}px, ${glowColor} 0%, transparent 70%)`
  }, [glowColor])

  const handleMouseLeave = useCallback(() => {
    const glow = glowRef.current
    if (glow) glow.style.opacity = '0'
  }, [])

  return (
    <div
      className={`relative overflow-hidden ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div
        ref={glowRef}
        className="absolute inset-0 pointer-events-none z-10"
        style={{ opacity: 0, transition: 'opacity 0.3s' }}
      />
      {children}
    </div>
  )
}
