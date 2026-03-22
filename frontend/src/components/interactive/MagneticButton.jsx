import { useRef, useState } from 'react'

/*
  Button that magnetically pulls toward cursor on hover.
  Snaps back on mouse leave with spring easing.
*/
export default function MagneticButton({ children, className = '', strength = 0.3, ...props }) {
  const ref = useRef(null)
  const [offset, setOffset] = useState({ x: 0, y: 0 })

  const handleMouseMove = (e) => {
    const rect = ref.current.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    setOffset({
      x: (e.clientX - cx) * strength,
      y: (e.clientY - cy) * strength,
    })
  }

  const handleMouseLeave = () => {
    setOffset({ x: 0, y: 0 })
  }

  return (
    <button
      ref={ref}
      className={className}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: `translate(${offset.x}px, ${offset.y}px)`,
        transition: offset.x === 0 ? 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)' : 'transform 0.15s ease-out',
      }}
      {...props}
    >
      {children}
    </button>
  )
}
