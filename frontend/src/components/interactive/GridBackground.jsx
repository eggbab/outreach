/*
  CSS-only dot grid. No canvas, no per-frame loop.
  Uses a repeating SVG pattern background with CSS animation.
*/
export default function GridBackground({ spacing = 28 }) {
  const dotSvg = `url("data:image/svg+xml,%3Csvg width='${spacing}' height='${spacing}' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='${spacing/2}' cy='${spacing/2}' r='1' fill='rgba(0,0,0,0.07)'/%3E%3C/svg%3E")`

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{
        zIndex: 0,
        backgroundImage: dotSvg,
        backgroundSize: `${spacing}px ${spacing}px`,
        maskImage: 'radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 70%)',
        WebkitMaskImage: 'radial-gradient(ellipse 70% 60% at 50% 50%, black 30%, transparent 70%)',
      }}
    />
  )
}
