/*
  Soft animated mesh gradient — pure CSS.
  Uses filter: blur on colored divs for smooth organic shapes.
*/
export default function HeroBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }}>
      <div className="absolute inset-0" style={{ filter: 'blur(80px)' }}>
        <div className="absolute w-[500px] h-[500px] rounded-full opacity-[0.15] bg-blue-400" style={{ left: '15%', top: '10%', animation: 'hbFloat1 20s ease-in-out infinite' }} />
        <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.12] bg-violet-400" style={{ right: '10%', top: '5%', animation: 'hbFloat2 24s ease-in-out infinite' }} />
        <div className="absolute w-[450px] h-[450px] rounded-full opacity-[0.08] bg-cyan-400" style={{ left: '35%', bottom: '5%', animation: 'hbFloat3 22s ease-in-out infinite' }} />
      </div>
      <style>{`
        @keyframes hbFloat1 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(30px,-40px)} }
        @keyframes hbFloat2 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-25px,35px)} }
        @keyframes hbFloat3 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(20px,-30px)} }
      `}</style>
    </div>
  )
}
