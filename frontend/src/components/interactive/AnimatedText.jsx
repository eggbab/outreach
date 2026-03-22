import { useState, useRef, useEffect } from 'react'
import { useScrollReveal } from './hooks'

/*
  Text that reveals word-by-word on scroll.
*/
export function WordReveal({ text, className = '', tag: Tag = 'h2' }) {
  const { ref, isVisible } = useScrollReveal({ threshold: 0.2 })
  const words = text.split(' ')

  return (
    <Tag ref={ref} className={className}>
      {words.map((word, i) => (
        <span key={i} className="inline-block overflow-hidden mr-[0.3em]">
          <span
            className="inline-block"
            style={{
              transform: isVisible ? 'translateY(0)' : 'translateY(110%)',
              opacity: isVisible ? 1 : 0,
              transition: `transform 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${i * 60}ms, opacity 0.6s ease ${i * 60}ms`,
            }}
          >
            {word}
          </span>
        </span>
      ))}
    </Tag>
  )
}

/*
  Number counter that animates when scrolled into view
*/
export function AnimatedCounter({ value, suffix = '', prefix = '', className = '', duration = 2000 }) {
  const { ref, isVisible } = useScrollReveal({ threshold: 0.3 })
  const numericValue = typeof value === 'number' ? value : parseFloat(String(value).replace(/[^0-9.]/g, ''))
  const isFloat = String(value).includes('.')

  return (
    <span ref={ref} className={className}>
      {isVisible ? (
        <CountUp target={numericValue} duration={duration} isFloat={isFloat} prefix={prefix} suffix={suffix} />
      ) : (
        <span>{prefix}0{suffix}</span>
      )}
    </span>
  )
}

function CountUp({ target, duration, isFloat, prefix, suffix }) {
  const [count, setCount] = useState(0)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const start = performance.now()
    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(isFloat ? eased * target : Math.floor(eased * target))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [target, duration, isFloat])

  return <span>{prefix}{isFloat ? count.toFixed(1) : count.toLocaleString()}{suffix}</span>
}

/*
  Gradient text that animates color on scroll
*/
export function GradientText({ children, className = '' }) {
  return (
    <span
      className={`bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-purple-600 to-cyan-500 ${className}`}
      style={{
        backgroundSize: '200% 100%',
        animation: 'gradientShift 4s ease infinite',
      }}
    >
      {children}
      <style>{`
        @keyframes gradientShift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
      `}</style>
    </span>
  )
}
