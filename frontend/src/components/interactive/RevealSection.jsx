import { useScrollReveal } from './hooks'

/*
  Wrapper that fades+slides children in when scrolled into view.
  delay: stagger delay in ms (for lists)
  direction: 'up' | 'down' | 'left' | 'right'
*/
export default function RevealSection({ children, className = '', delay = 0, direction = 'up' }) {
  const { ref, isVisible } = useScrollReveal({ threshold: 0.1 })

  const offsets = {
    up: 'translate3d(0, 40px, 0)',
    down: 'translate3d(0, -40px, 0)',
    left: 'translate3d(40px, 0, 0)',
    right: 'translate3d(-40px, 0, 0)',
  }

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translate3d(0, 0, 0)' : offsets[direction],
        transition: `opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms, transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
        willChange: 'opacity, transform',
      }}
    >
      {children}
    </div>
  )
}
