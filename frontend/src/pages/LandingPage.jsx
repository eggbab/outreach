import { lazy, Suspense, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { ArrowRight, Mail, MessageCircle, BarChart3, Kanban, Phone, FileCheck, Calendar, Users, Key, Shield, Tag, Download } from 'lucide-react'
import Logo from '../components/Logo'
import CursorGlow from '../components/interactive/CursorGlow'
import RevealSection from '../components/interactive/RevealSection'
import TiltCard from '../components/interactive/TiltCard'
import MagneticButton from '../components/interactive/MagneticButton'
import GridBackground from '../components/interactive/GridBackground'
import HeroBackground from '../components/interactive/HeroBackground'
import { WordReveal, AnimatedCounter, GradientText } from '../components/interactive/AnimatedText'

const PipelineScene = lazy(() => import('../components/webgl/PipelineScene'))
const CTAScene = lazy(() => import('../components/webgl/CTAScene'))

const WebGL = ({ children }) => <Suspense fallback={null}>{children}</Suspense>

export default function LandingPage() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-white text-gray-900 overflow-x-hidden">
      <CursorGlow />

      {/* ─── Nav ─── */}
      <nav className="fixed top-0 w-full z-50 bg-white/60 backdrop-blur-md border-b border-gray-100/50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <Logo size={22} />
            <span className="font-semibold group-hover:text-blue-600 transition-colors">Outreach</span>
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <a href="#features" className="text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">기능</a>
            <a href="#pipeline" className="text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">CRM</a>
            <a href="#pricing" className="text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">요금제</a>
            {user ? (
              <Link to="/dashboard" className="text-gray-500 hover:text-gray-900 transition-colors">대시보드</Link>
            ) : (
              <>
                <Link to="/login" className="text-gray-500 hover:text-gray-900 transition-colors">로그인</Link>
                <MagneticButton strength={0.2}>
                  <Link to="/signup" className="px-4 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-all hover:shadow-lg hover:shadow-blue-600/25 text-sm inline-block">시작하기</Link>
                </MagneticButton>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="relative min-h-[92vh] flex flex-col justify-center px-6 overflow-hidden">
        <HeroBackground />
        <div className="max-w-3xl mx-auto text-center relative z-10">
          <RevealSection delay={0}>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50/80 backdrop-blur text-blue-700 text-xs font-medium mb-8 border border-blue-100">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              14일 Pro 무료 체험 — 카드 등록 없이 시작
            </div>
          </RevealSection>

          <WordReveal
            text="수집부터 계약까지,"
            tag="h1"
            className="text-[2.75rem] sm:text-[3.5rem] lg:text-[4rem] font-semibold leading-[1.1] tracking-tight"
          />
          <RevealSection delay={400}>
            <span className="text-[2.75rem] sm:text-[3.5rem] lg:text-[4rem] font-semibold leading-[1.1] tracking-tight block mt-1">
              <GradientText>영업 전체를 자동화</GradientText>
            </span>
          </RevealSection>

          <RevealSection delay={600}>
            <p className="mt-6 text-lg sm:text-xl text-gray-500 leading-relaxed max-w-2xl mx-auto">
              키워드 하나로 잠재고객을 수집하고, 이메일 시퀀스와 DM을 자동 발송하고,
              파이프라인으로 딜을 클로징하세요.
            </p>
          </RevealSection>

          <RevealSection delay={800}>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <MagneticButton strength={0.25}>
                <Link
                  to="/signup"
                  className="inline-flex items-center gap-2 px-7 py-3.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20 hover:shadow-xl hover:shadow-blue-600/30 hover:-translate-y-0.5"
                >
                  무료로 시작하기 <ArrowRight className="w-4 h-4" />
                </Link>
              </MagneticButton>
              <a
                href="#features"
                className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors group"
              >
                기능 살펴보기
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </a>
            </div>
          </RevealSection>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10">
          <div className="w-5 h-8 rounded-full border-2 border-gray-300 flex items-start justify-center p-1">
            <div className="w-1 h-2 bg-gray-400 rounded-full animate-bounce" />
          </div>
        </div>
      </section>

      {/* ─── Hero metrics ─── */}
      <section className="px-6 py-12 border-t border-gray-100">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-center gap-8 sm:gap-20">
            {[
              { value: 5, suffix: '개', label: '수집 소스' },
              { value: 3, suffix: '채널', label: '발송 채널' },
              { value: 80, suffix: '%', label: '시간 절약' },
              { value: 3, suffix: 'x', label: '응답률 향상' },
            ].map((m, i) => (
              <RevealSection key={m.label} delay={i * 150}>
                <div className="text-center">
                  <p className="text-3xl sm:text-4xl font-semibold text-gray-900">
                    <AnimatedCounter value={m.value} suffix={m.suffix} duration={1500} />
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{m.label}</p>
                </div>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Interactive Product Demo ─── */}
      <section className="px-6 pb-24">
        <RevealSection>
          <div className="max-w-5xl mx-auto">
            <p className="text-center text-sm text-gray-500 mb-4">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                왼쪽 메뉴를 클릭해서 각 기능을 체험해보세요
              </span>
            </p>
            <InteractiveDemo />
          </div>
        </RevealSection>
      </section>

      {/* ─── Workflow ─── */}
      <section className="relative py-24 px-6 border-t border-gray-100 overflow-hidden">
        <GridBackground spacing={32} />
        <div className="max-w-5xl mx-auto relative z-10">
          <div className="text-center mb-8">
            <WordReveal text="영업의 시작부터 끝까지, 하나의 도구로" className="text-3xl font-semibold mb-3" />
            <RevealSection delay={300}>
              <p className="text-gray-500 max-w-xl mx-auto">
                수집 → 발송 → 후속 → 미팅 → 계약. 흩어진 영업 프로세스를 하나의 플랫폼에서 관리하세요.
              </p>
            </RevealSection>
          </div>

          <RevealSection delay={200}>
            <div className="mb-8 rounded-xl overflow-hidden bg-white/60 backdrop-blur ring-1 ring-gray-200">
              <WebGL><PipelineScene /></WebGL>
            </div>
          </RevealSection>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { step: '01', title: '수집', desc: '5개 소스에서 키워드 기반 잠재고객 자동 수집', color: 'border-blue-200 bg-blue-50/50', hover: 'hover:border-blue-400 hover:bg-blue-50' },
              { step: '02', title: '발송', desc: '이메일 시퀀스 + 인스타 DM 멀티채널 아웃리치', color: 'border-purple-200 bg-purple-50/50', hover: 'hover:border-purple-400 hover:bg-purple-50' },
              { step: '03', title: '분석', desc: '열람/클릭 트래킹, 스코어링, A/B 테스트', color: 'border-green-200 bg-green-50/50', hover: 'hover:border-green-400 hover:bg-green-50' },
              { step: '04', title: '클로징', desc: '파이프라인, 제안서, 미팅 예약으로 딜 성사', color: 'border-orange-200 bg-orange-50/50', hover: 'hover:border-orange-400 hover:bg-orange-50' },
            ].map((item, i) => (
              <RevealSection key={item.step} delay={i * 120 + 400}>
                <TiltCard className={`rounded-xl border p-5 transition-all duration-300 ${item.color} ${item.hover}`} glowColor="rgba(59,130,246,0.08)">
                  <span className="text-xs font-mono text-gray-400">{item.step}</span>
                  <h3 className="text-lg font-semibold text-gray-900 mt-2 mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed relative z-20">{item.desc}</p>
                </TiltCard>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section id="features" className="py-24 px-6 border-t border-gray-100">
        <div className="max-w-5xl mx-auto">
          <RevealSection>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-12">수집 & 발송</h2>
          </RevealSection>

          <div className="space-y-28">
            {/* Feature 1 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <RevealSection direction="left">
                <div>
                  <h3 className="text-2xl font-semibold mb-4">5개 소스에서 자동 수집</h3>
                  <p className="text-gray-500 leading-relaxed mb-6">
                    네이버 검색, 구글, 인스타그램, 네이버쇼핑, 네이버지도에서 업종 키워드 기반으로 업체 정보를 수집합니다.
                  </p>
                  <ul className="space-y-2">
                    {['플랜별 일일 수집 한도 관리', 'AI 스코어링으로 유망 고객 우선순위화', '태그 분류 + CSV 내보내기'].map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="w-1 h-1 rounded-full bg-blue-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              </RevealSection>
              <RevealSection direction="right" delay={200}>
                <TiltCard className="bg-gray-50 rounded-xl border border-gray-200 p-6" glowColor="rgba(59,130,246,0.1)">
                  <div className="space-y-3">
                    {['네이버 검색', '구글', '인스타그램', '네이버쇼핑', '네이버지도'].map((s, i) => (
                      <BarItem key={s} label={s} value={[245, 189, 156, 210, 132][i]} max={245} delay={i * 100} />
                    ))}
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
                    <span className="text-xs text-gray-500">총 수집</span>
                    <span className="text-sm font-semibold text-gray-900">
                      <AnimatedCounter value={932} suffix="건" />
                    </span>
                  </div>
                </TiltCard>
              </RevealSection>
            </div>

            {/* Feature 2 — Sequence */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <RevealSection direction="left" delay={100} className="order-2 md:order-1">
                <TiltCard className="bg-gray-50 rounded-xl border border-gray-200 p-6" glowColor="rgba(139,92,246,0.1)">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-xs font-semibold text-gray-700">후속 이메일 시퀀스</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium animate-pulse">실행중</span>
                  </div>
                  {[
                    { step: 1, title: '첫 인사', delay: '즉시', sent: 847, opened: 356 },
                    { step: 2, title: '가치 제안', delay: '3일 후', sent: 491, opened: 198 },
                    { step: 3, title: '사례 공유', delay: '5일 후', sent: 293, opened: 142 },
                    { step: 4, title: '마지막 제안', delay: '7일 후', sent: 151, opened: 89 },
                  ].map((s, i) => (
                    <RevealSection key={s.step} delay={i * 150 + 300} direction="left">
                      <div className="flex items-start gap-3 py-3 group">
                        <div className="flex flex-col items-center">
                          <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">{s.step}</div>
                          {i < 3 && <div className="w-px h-6 bg-gray-200" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">{s.title}</span>
                            <span className="text-[10px] text-gray-400">{s.delay}</span>
                          </div>
                          <div className="flex gap-3 mt-1 text-[10px] text-gray-500">
                            <span>발송 <AnimatedCounter value={s.sent} duration={1200} /></span>
                            <span>열람 <AnimatedCounter value={s.opened} duration={1200} /></span>
                          </div>
                        </div>
                      </div>
                    </RevealSection>
                  ))}
                </TiltCard>
              </RevealSection>
              <RevealSection direction="right" className="order-1 md:order-2">
                <div>
                  <h3 className="text-2xl font-semibold mb-4">자동 후속 이메일 시퀀스</h3>
                  <p className="text-gray-500 leading-relaxed mb-6">
                    한 번 설정하면 조건에 따라 후속 이메일이 자동 발송됩니다.
                    미열람·미클릭 고객에게만 보내는 조건 분기로 응답률을 극대화하세요.
                  </p>
                  <ul className="space-y-2">
                    {['단계별 대기 일수 + 발송 조건 설정', 'A/B 변형 테스트로 최적 제목 찾기', '발송 건강도 스코어로 스팸 방지'].map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="w-1 h-1 rounded-full bg-purple-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              </RevealSection>
            </div>

            {/* Feature 3 — Tracking */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <RevealSection direction="left">
                <div>
                  <h3 className="text-2xl font-semibold mb-4">실시간 트래킹 & 분석</h3>
                  <p className="text-gray-500 leading-relaxed mb-6">
                    이메일 열람·클릭을 실시간으로 추적하고, 전환 퍼널과 일별 통계를 한눈에 확인하세요.
                  </p>
                  <ul className="space-y-2">
                    {['오픈/클릭 실시간 알림', '일별·주별 발송 성과 차트', '퍼널: 수집 → 승인 → 발송 → 열람 → 클릭'].map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="w-1 h-1 rounded-full bg-green-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              </RevealSection>
              <RevealSection direction="right" delay={200}>
                <TiltCard className="bg-gray-50 rounded-xl border border-gray-200 p-6" glowColor="rgba(16,185,129,0.1)">
                  <div className="grid grid-cols-3 gap-3 mb-5">
                    {[
                      { label: '열람률', value: 42.3, suffix: '%', color: 'text-green-600' },
                      { label: '클릭률', value: 18.7, suffix: '%', color: 'text-blue-600' },
                      { label: '응답률', value: 8.2, suffix: '%', color: 'text-purple-600' },
                    ].map((s) => (
                      <div key={s.label} className="text-center">
                        <p className={`text-xl font-semibold ${s.color}`}>
                          <AnimatedCounter value={s.value} suffix={s.suffix} duration={1800} />
                        </p>
                        <p className="text-[10px] text-gray-400 mt-0.5">{s.label}</p>
                      </div>
                    ))}
                  </div>
                  <LiveFeed />
                </TiltCard>
              </RevealSection>
            </div>

            {/* Feature 4 — DM */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <RevealSection direction="left" delay={100} className="order-2 md:order-1">
                <TiltCard className="bg-gray-50 rounded-xl border border-gray-200 p-6" glowColor="rgba(236,72,153,0.1)">
                  <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-200">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">@outreach_official</p>
                      <p className="text-[10px] text-gray-400">Instagram Direct</p>
                    </div>
                  </div>
                  <ChatBubbles />
                </TiltCard>
              </RevealSection>
              <RevealSection direction="right" className="order-1 md:order-2">
                <div>
                  <h3 className="text-2xl font-semibold mb-4">인스타그램 DM 자동화</h3>
                  <p className="text-gray-500 leading-relaxed mb-6">
                    크롬 확장프로그램으로 인스타그램 DM을 자동 발송합니다.
                    로그인된 세션을 활용하기 때문에 별도 인증 없이 스팸 감지를 자동으로 회피합니다.
                  </p>
                  <ul className="space-y-2">
                    {['플랜별 일일 DM 한도 관리', '회사명 변수로 개인화 메시지', '발송 대기열 + 결과 로그 확인'].map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="w-1 h-1 rounded-full bg-pink-500" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              </RevealSection>
            </div>
          </div>
        </div>
      </section>

      {/* ─── CRM ─── */}
      <section id="pipeline" className="relative py-24 px-6 border-t border-gray-100 overflow-hidden">
        <GridBackground spacing={36} />
        <div className="max-w-5xl mx-auto relative z-10">
          <RevealSection>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-12">CRM & 영업 관리</h2>
          </RevealSection>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start mb-16">
            <RevealSection direction="left">
              <div>
                <h3 className="text-2xl font-semibold mb-4">드래그앤드롭 영업 파이프라인</h3>
                <p className="text-gray-500 leading-relaxed mb-6">
                  리드부터 계약 성사까지 칸반 보드로 딜을 관리하세요.
                  스테이지별 금액 합계와 성사율을 한눈에 파악할 수 있습니다.
                </p>
                <ul className="space-y-2">
                  {['커스텀 스테이지 (리드→컨택→미팅→제안→계약→성사)', '딜 금액 추적 + 성사/실패 통계', '잠재고객별 통합 활동 타임라인'].map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                      <span className="w-1 h-1 rounded-full bg-orange-500" />{f}
                    </li>
                  ))}
                </ul>
              </div>
            </RevealSection>
            <RevealSection direction="right" delay={200}>
              <TiltCard className="bg-white rounded-xl border border-gray-200 p-5" glowColor="rgba(245,158,11,0.08)">
                <KanbanMock />
              </TiltCard>
            </RevealSection>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { title: '통화 기록', desc: '발신/수신/부재중 기록, 콜백 리마인더', icon: '📞', glow: 'rgba(16,185,129,0.12)' },
              { title: '제안서', desc: '제안서 작성 → 발송 → 열람 트래킹', icon: '📄', glow: 'rgba(59,130,246,0.12)' },
              { title: '미팅 예약', desc: '가용시간 설정, 공개 예약 링크', icon: '📅', glow: 'rgba(139,92,246,0.12)' },
              { title: '팀 협업', desc: '팀 생성, 멤버 초대, 프로젝트 공유', icon: '👥', glow: 'rgba(245,158,11,0.12)' },
            ].map((f, i) => (
              <RevealSection key={f.title} delay={i * 100}>
                <TiltCard className="bg-white rounded-xl border border-gray-200 p-5 h-full hover:border-gray-300 transition-colors" glowColor={f.glow}>
                  <span className="text-2xl">{f.icon}</span>
                  <h4 className="text-sm font-semibold text-gray-900 mt-3 mb-1.5 relative z-20">{f.title}</h4>
                  <p className="text-xs text-gray-500 leading-relaxed relative z-20">{f.desc}</p>
                </TiltCard>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── More features ─── */}
      <section className="py-24 px-6 border-t border-gray-100">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <WordReveal text="파워유저를 위한 기능" className="text-3xl font-semibold mb-3" />
            <RevealSection delay={200}>
              <p className="text-gray-500">성장하는 비즈니스에 필요한 모든 도구</p>
            </RevealSection>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { title: '이메일 템플릿', desc: '재사용 가능한 템플릿 라이브러리. A/B 변형으로 최적의 제목과 본문을 찾으세요.' },
              { title: '발송 건강도 체크', desc: '스팸 키워드, 제목 길이, 수신거부 포함 여부를 자동으로 점검합니다.' },
              { title: '잠재고객 스코어링', desc: '연락처 보유 여부, 이메일 열람, 클릭 등을 기반으로 유망도를 자동 계산합니다.' },
              { title: '태그 & 메모', desc: '잠재고객에 태그를 붙이고 메모를 남겨 체계적으로 관리하세요.' },
              { title: 'CSV 내보내기', desc: '수집된 잠재고객 데이터를 한글 Excel 호환 CSV로 내보낼 수 있습니다.' },
              { title: 'API 키 연동', desc: 'REST API로 외부 시스템과 연동하세요. 키 생성/폐기를 UI에서 관리합니다.' },
            ].map((f, i) => (
              <RevealSection key={f.title} delay={i * 80}>
                <TiltCard className="rounded-xl border border-gray-200 p-5 h-full hover:border-blue-200 transition-colors" glowColor="rgba(59,130,246,0.08)">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2 relative z-20">{f.title}</h4>
                  <p className="text-xs text-gray-500 leading-relaxed relative z-20">{f.desc}</p>
                </TiltCard>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Testimonials ─── */}
      <section className="py-24 px-6 border-t border-gray-100 bg-gray-50/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <WordReveal text="고객 후기" className="text-3xl font-semibold mb-3" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: '김영수', role: '마트마트 대표', text: '수작업으로 하루 종일 걸리던 잠재고객 수집이 30분이면 끝납니다. 파이프라인까지 한 곳에서 관리하니 영업 효율이 5배 이상 늘었어요.' },
              { name: '이지현', role: '디자인 에이전시', text: '시퀀스 기능이 압도적입니다. 미열람 고객에게만 후속 메일이 가니까 스팸 걱정 없이 응답률이 올라갔어요.' },
              { name: '박준호', role: 'B2B SaaS 영업', text: '인스타 DM + 이메일 + 통화 기록이 한 곳에 모여있으니 고객과의 히스토리를 한눈에 볼 수 있습니다.' },
            ].map((t, i) => (
              <RevealSection key={t.name} delay={i * 150}>
                <TiltCard className="bg-white rounded-xl ring-1 ring-gray-200 p-6 h-full" glowColor="rgba(59,130,246,0.06)">
                  <p className="text-gray-600 text-sm leading-relaxed mb-4 relative z-20">"{t.text}"</p>
                  <div className="flex items-center gap-3 relative z-20">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-medium text-xs">{t.name.charAt(0)}</div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{t.name}</p>
                      <p className="text-xs text-gray-500">{t.role}</p>
                    </div>
                  </div>
                </TiltCard>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── ROI ─── */}
      <section className="py-24 px-6 border-t border-gray-100">
        <div className="max-w-3xl mx-auto text-center">
          <WordReveal text="도입 효과" className="text-3xl font-semibold mb-10" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { label: '수작업 시간 절약', value: 80, suffix: '%' },
              { label: '응답률 향상', value: 3, suffix: 'x' },
              { label: '월 비용', prefix: '₩', value: 29, suffix: 'K' },
            ].map((item, i) => (
              <RevealSection key={item.label} delay={i * 150}>
                <div className="bg-gray-50 rounded-xl ring-1 ring-gray-200 p-6 hover:ring-blue-200 transition-colors">
                  <p className="text-3xl font-bold text-blue-600 mb-2">
                    <AnimatedCounter value={item.value} prefix={item.prefix} suffix={item.suffix} duration={1500} />
                  </p>
                  <p className="text-sm font-medium text-gray-900">{item.label}</p>
                </div>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Pricing ─── */}
      <section id="pricing" className="py-24 px-6 border-t border-gray-100 bg-gray-50/50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <WordReveal text="요금제" className="text-3xl font-semibold mb-3" />
            <RevealSection delay={200}>
              <p className="text-gray-500">14일 Pro 무료 체험. 카드 등록 없이 시작하세요.</p>
            </RevealSection>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: '무료', price: '0', desc: '기능 체험용', features: ['프로젝트 1개', '이메일 3건/일', 'DM 2건/일'], highlight: false },
              { name: '프로', price: '29,000', desc: '본격 영업 자동화', features: ['프로젝트 10개', '이메일 100건/일', 'DM 30건/일', '시퀀스 + CRM', '초과 시 건당 과금'], highlight: true },
              { name: '에이전시', price: '79,000', desc: '대규모 팀 운영', features: ['프로젝트 무제한', '이메일 500건/일', 'DM 100건/일', '팀 협업 + API', '우선 지원'], highlight: false },
            ].map((plan, i) => (
              <RevealSection key={plan.name} delay={i * 120}>
                <TiltCard
                  className={`rounded-xl p-6 h-full ${plan.highlight ? 'bg-gray-900 text-white ring-1 ring-gray-900' : 'bg-white ring-1 ring-gray-200'}`}
                  glowColor={plan.highlight ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.08)'}
                >
                  <p className={`text-sm font-medium mb-4 relative z-20 ${plan.highlight ? 'text-gray-400' : 'text-gray-500'}`}>{plan.name}</p>
                  <p className="mb-1 relative z-20">
                    <span className={`text-3xl font-semibold ${plan.highlight ? 'text-white' : 'text-gray-900'}`}>
                      {plan.price === '0' ? '무료' : `${plan.price}원`}
                    </span>
                    {plan.price !== '0' && <span className={`text-sm ml-1 ${plan.highlight ? 'text-gray-400' : 'text-gray-500'}`}>/월</span>}
                  </p>
                  <p className={`text-sm mb-6 relative z-20 ${plan.highlight ? 'text-gray-400' : 'text-gray-500'}`}>{plan.desc}</p>
                  <MagneticButton strength={0.15} className="w-full">
                    <Link to="/signup" className={`block w-full py-2.5 rounded-md text-sm font-medium text-center transition-all relative z-20 ${
                      plan.highlight ? 'bg-white text-gray-900 hover:bg-gray-100' : 'bg-gray-900 text-white hover:bg-gray-800'
                    }`}>
                      {plan.highlight ? '14일 무료 체험' : '시작하기'}
                    </Link>
                  </MagneticButton>
                  <ul className="space-y-2.5 mt-6 relative z-20">
                    {plan.features.map((f) => (
                      <li key={f} className={`text-sm flex items-center gap-2 ${plan.highlight ? 'text-gray-300' : 'text-gray-600'}`}>
                        <span className={`w-1 h-1 rounded-full ${plan.highlight ? 'bg-gray-500' : 'bg-gray-300'}`} />{f}
                      </li>
                    ))}
                  </ul>
                </TiltCard>
              </RevealSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="relative py-28 px-6 border-t border-gray-100 overflow-hidden">
        <WebGL><CTAScene /></WebGL>
        <div className="max-w-2xl mx-auto text-center relative z-10">
          <WordReveal text="영업의 모든 과정을 자동화하세요" className="text-3xl font-semibold mb-4" />
          <RevealSection delay={300}>
            <p className="text-gray-500 mb-8">
              잠재고객 수집, 이메일 시퀀스, DM 발송, 파이프라인 관리, 제안서, 미팅 예약까지.<br />
              반복 작업은 Outreach가 처리합니다.
            </p>
          </RevealSection>
          <RevealSection delay={500}>
            <MagneticButton strength={0.25}>
              <Link to="/signup" className="inline-flex items-center gap-2 px-7 py-3.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20 hover:shadow-xl hover:shadow-blue-600/30 hover:-translate-y-0.5">
                14일 무료로 시작하기 <ArrowRight className="w-4 h-4" />
              </Link>
            </MagneticButton>
            <p className="text-xs text-gray-400 mt-4">카드 등록 없이 · Pro 플랜 14일 체험 · 언제든 해지</p>
          </RevealSection>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="bg-gray-950 text-gray-400 pt-16 pb-8 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Top grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
            {/* Brand */}
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <Logo size={22} />
                <span className="text-white font-semibold">Outreach</span>
              </div>
              <p className="text-sm leading-relaxed text-gray-500">
                B2B 영업 자동화 플랫폼.<br />
                수집부터 계약까지 한 곳에서.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="text-white text-xs font-semibold uppercase tracking-wider mb-4">제품</h4>
              <ul className="space-y-2.5">
                {[
                  { label: '잠재고객 수집', href: '#features' },
                  { label: '이메일 시퀀스', href: '#features' },
                  { label: 'DM 자동화', href: '#features' },
                  { label: '분석 & 트래킹', href: '#features' },
                ].map((item) => (
                  <li key={item.label}>
                    <a href={item.href} className="text-sm hover:text-white transition-colors">{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* CRM */}
            <div>
              <h4 className="text-white text-xs font-semibold uppercase tracking-wider mb-4">CRM</h4>
              <ul className="space-y-2.5">
                {[
                  { label: '파이프라인', href: '#pipeline' },
                  { label: '통화 기록', href: '#pipeline' },
                  { label: '제안서', href: '#pipeline' },
                  { label: '미팅 예약', href: '#pipeline' },
                ].map((item) => (
                  <li key={item.label}>
                    <a href={item.href} className="text-sm hover:text-white transition-colors">{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="text-white text-xs font-semibold uppercase tracking-wider mb-4">회사</h4>
              <ul className="space-y-2.5">
                {[
                  { label: '요금제', href: '#pricing' },
                  { label: '블로그', href: '#' },
                  { label: '이용약관', href: '#' },
                  { label: '개인정보처리방침', href: '#' },
                ].map((item) => (
                  <li key={item.label}>
                    <a href={item.href} className="text-sm hover:text-white transition-colors">{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Support */}
            <div>
              <h4 className="text-white text-xs font-semibold uppercase tracking-wider mb-4">지원</h4>
              <ul className="space-y-2.5">
                {[
                  { label: '도움말', href: '#' },
                  { label: 'API 문서', href: '#' },
                  { label: '문의하기', href: '#' },
                  { label: '서비스 상태', href: '#' },
                ].map((item) => (
                  <li key={item.label}>
                    <a href={item.href} className="text-sm hover:text-white transition-colors">{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Newsletter / CTA bar */}
          <div className="border-t border-gray-800 pt-8 mb-8">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
              <div>
                <h4 className="text-white text-sm font-semibold mb-1">영업 자동화 소식 받기</h4>
                <p className="text-xs text-gray-500">활용 팁, 업데이트, 성공 사례를 이메일로 보내드립니다.</p>
              </div>
              <div className="flex gap-2 w-full sm:w-auto">
                <input
                  type="email"
                  placeholder="이메일 주소"
                  className="flex-1 sm:w-56 px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
                />
                <MagneticButton strength={0.15}>
                  <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap cursor-pointer">
                    구독
                  </button>
                </MagneticButton>
              </div>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="border-t border-gray-800 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-600">
              &copy; 2026 Outreach. All rights reserved.
            </p>
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-xs hover:text-white transition-colors">로그인</Link>
              <Link to="/signup" className="text-xs text-blue-500 hover:text-blue-400 transition-colors font-medium">무료로 시작하기</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

/* ─── Interactive Demo ─── */

const DEMO_PAGES = {
  '대시보드': DashboardMock,
  '파이프라인': PipelineMock,
  '시퀀스': SequenceMock,
  '분석': AnalyticsMock,
  '제안서': ProposalMock,
  '미팅': MeetingMock,
}
const DEMO_MENU = Object.keys(DEMO_PAGES)

function InteractiveDemo() {
  const [activePage, setActivePage] = useState('대시보드')
  const [hasClicked, setHasClicked] = useState(false)
  const ActiveContent = DEMO_PAGES[activePage]

  const handleClick = (item) => {
    setActivePage(item)
    setHasClicked(true)
  }

  return (
    <TiltCard className="rounded-xl border border-gray-200 bg-gray-50 overflow-hidden shadow-sm" glowColor="rgba(59,130,246,0.06)">
      {/* Browser bar */}
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-gray-200 bg-white">
        <div className="w-2.5 h-2.5 rounded-full bg-red-300" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-300" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-300" />
        <div className="ml-3 flex-1 max-w-xs h-5 rounded bg-gray-100 flex items-center px-3">
          <span className="text-[10px] text-gray-400">app.outreach.kr/{activePage === '대시보드' ? 'dashboard' : activePage}</span>
        </div>
      </div>
      <div className="flex" style={{ minHeight: 340 }}>
        {/* Sidebar */}
        <div className="w-44 bg-white border-r border-gray-200 p-3 hidden md:flex flex-col">
          <div className="flex items-center gap-2 mb-5 px-1">
            <div className="w-5 h-5 rounded bg-blue-600" />
            <span className="text-xs font-semibold text-gray-900">Outreach</span>
          </div>
          {DEMO_MENU.map((item, i) => (
            <button
              key={item}
              onClick={() => handleClick(item)}
              className={`text-left text-[11px] py-1.5 px-2 rounded mb-0.5 transition-all cursor-pointer ${
                activePage === item
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }`}
              style={!hasClicked && i === 1 ? { animation: 'menuHint 2s ease-in-out infinite' } : {}}
            >
              {item}
            </button>
          ))}
          {!hasClicked && (
            <p className="text-[9px] text-blue-500 mt-3 px-1 animate-pulse">
              ↑ 메뉴를 클릭해보세요
            </p>
          )}
        </div>
        {/* Mobile tabs */}
        <div className="md:hidden flex border-b border-gray-200 bg-white overflow-x-auto">
          {DEMO_MENU.map((item) => (
            <button
              key={item}
              onClick={() => handleClick(item)}
              className={`text-[11px] px-3 py-2 whitespace-nowrap cursor-pointer transition-colors ${
                activePage === item ? 'text-blue-700 border-b-2 border-blue-600 font-medium' : 'text-gray-500'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
        {/* Content */}
        <div className="flex-1 p-5 sm:p-6 overflow-hidden">
          <div key={activePage} style={{ animation: 'demoFadeIn 0.3s ease' }}>
            <ActiveContent />
          </div>
        </div>
      </div>
      <style>{`
        @keyframes demoFadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes menuHint { 0%,100%{background:transparent} 50%{background:rgba(59,130,246,0.08)} }
      `}</style>
    </TiltCard>
  )
}

function DashboardMock() {
  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {[
          { label: '잠재고객', value: '1,247', change: '+89' },
          { label: '이메일 발송', value: '512', change: '+34' },
          { label: '열람률', value: '42.3%', change: '+2.1%' },
          { label: '파이프라인', value: '₩15.8M', change: '+₩2.3M' },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border border-gray-200 p-3 hover:border-blue-200 transition-colors">
            <p className="text-[10px] text-gray-400 mb-1">{s.label}</p>
            <div className="flex items-baseline gap-1.5">
              <span className="text-base font-semibold text-gray-900">{s.value}</span>
              <span className="text-[10px] text-green-600 font-medium">{s.change}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-2 border-b border-gray-100 flex justify-between">
          <span className="text-[11px] font-semibold text-gray-900">최근 수집된 잠재고객</span>
          <span className="text-[10px] text-blue-600 font-medium">CSV 내보내기</span>
        </div>
        {[
          { name: '삼성전자서비스', score: 85, status: '승인', color: 'bg-green-50 text-green-700' },
          { name: '현대리바트', score: 62, status: '수집', color: 'bg-gray-100 text-gray-600' },
          { name: '쿠팡 물류센터', score: 91, status: '발송완료', color: 'bg-blue-50 text-blue-700' },
          { name: '오늘의집 입점사', score: 48, status: '시퀀스', color: 'bg-purple-50 text-purple-700' },
        ].map((r) => (
          <div key={r.name} className="px-4 py-2 border-b border-gray-50 last:border-0 flex items-center text-[11px] hover:bg-blue-50/30 transition-colors">
            <span className="flex-1 font-medium text-gray-900">{r.name}</span>
            <span className={`w-6 text-center text-[10px] font-semibold ${r.score >= 70 ? 'text-green-600' : 'text-yellow-600'}`}>{r.score}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ml-2 ${r.color}`}>{r.status}</span>
          </div>
        ))}
      </div>
    </>
  )
}

function PipelineMock() {
  return <KanbanMock />
}

function SequenceMock() {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[11px] font-semibold text-gray-900">초기 영업 시퀀스</span>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">실행중</span>
        <span className="text-[10px] text-gray-400 ml-auto">등록 847명</span>
      </div>
      {[
        { n: 1, title: '첫 인사 이메일', delay: '즉시', cond: '항상', sent: 847, rate: '42%' },
        { n: 2, title: '가치 제안', delay: '3일 후', cond: '미열람시', sent: 491, rate: '40%' },
        { n: 3, title: '사례 공유', delay: '5일 후', cond: '미클릭시', sent: 293, rate: '48%' },
        { n: 4, title: '마지막 제안', delay: '7일 후', cond: '미열람시', sent: 151, rate: '59%' },
      ].map((s, i) => (
        <div key={s.n} className="flex items-start gap-3 py-2.5">
          <div className="flex flex-col items-center">
            <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[9px] font-bold flex items-center justify-center">{s.n}</div>
            {i < 3 && <div className="w-px h-5 bg-gray-200 mt-0.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-[11px]">
              <span className="font-medium text-gray-900">{s.title}</span>
              <span className="text-gray-400">{s.delay}</span>
              <span className="text-gray-400 ml-auto hidden sm:inline">{s.cond}</span>
            </div>
            <div className="flex gap-3 mt-0.5 text-[10px] text-gray-500">
              <span>발송 {s.sent}</span>
              <span>열람 {s.rate}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function AnalyticsMock() {
  const bars = [12, 18, 25, 22, 30, 28, 35, 32, 40, 38, 45, 42, 48, 44]
  return (
    <div>
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: '총 발송', value: '512', color: 'text-gray-900' },
          { label: '열람률', value: '42.3%', color: 'text-green-600' },
          { label: '클릭률', value: '18.7%', color: 'text-blue-600' },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border border-gray-200 p-3 text-center">
            <p className={`text-lg font-semibold ${s.color}`}>{s.value}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-[11px] font-semibold text-gray-900 mb-3">일별 발송</p>
        <div className="flex items-end gap-1.5 h-24">
          {bars.map((v, i) => (
            <div key={i} className="flex-1 bg-blue-500 rounded-sm hover:bg-blue-600 transition-colors" style={{ height: `${(v / 48) * 100}%` }} title={`${v}건`} />
          ))}
        </div>
        <div className="flex justify-between mt-1.5 text-[9px] text-gray-400">
          <span>3/8</span><span>3/22</span>
        </div>
      </div>
    </div>
  )
}

function ProposalMock() {
  return (
    <div className="space-y-3">
      {[
        { title: '프레시마켓 광고 파트너십', amount: '₩3,200,000', status: '열람', statusColor: 'bg-green-100 text-green-700', viewed: '2시간 전' },
        { title: '디자인랩 커뮤니티 홍보', amount: '₩1,500,000', status: '발송', statusColor: 'bg-blue-100 text-blue-700', viewed: null },
        { title: '테크솔루션 연간 계약', amount: '₩5,000,000', status: '초안', statusColor: 'bg-gray-100 text-gray-600', viewed: null },
      ].map((p) => (
        <div key={p.title} className="bg-white rounded-lg border border-gray-200 p-3 hover:border-blue-200 transition-colors">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-gray-900">{p.title}</span>
            <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${p.statusColor}`}>{p.status}</span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-gray-500">
            <span>{p.amount}</span>
            {p.viewed && <span className="text-green-600">열람: {p.viewed}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

function MeetingMock() {
  return (
    <div className="space-y-3">
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <p className="text-[11px] font-semibold text-gray-900 mb-2">이번 주 미팅</p>
        {[
          { title: '프레시마켓 — 파트너십 논의', time: '3/24 (월) 14:00', status: '예정' },
          { title: '테크솔루션 — 제안 발표', time: '3/25 (화) 10:00', status: '예정' },
          { title: '쿠팡 물류 — 계약 검토', time: '3/26 (수) 15:30', status: '예정' },
        ].map((m) => (
          <div key={m.title} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium text-gray-900 truncate">{m.title}</p>
              <p className="text-[10px] text-gray-400">{m.time}</p>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">{m.status}</span>
          </div>
        ))}
      </div>
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-3">
        <p className="text-[10px] text-blue-700 font-medium">공개 예약 링크가 활성화되어 있습니다</p>
        <p className="text-[10px] text-blue-500 mt-0.5 font-mono">outreach.kr/book/김우진</p>
      </div>
    </div>
  )
}

/* ─── Sub-components ─── */

function BarItem({ label, value, max, delay = 0 }) {
  const barRef = useRef(null)
  const observerRef = useRef(null)
  const [visible, setVisible] = useState(false)
  const width = (value / max) * 80

  const setRef = (el) => {
    barRef.current = el
    if (el && !visible && !observerRef.current) {
      observerRef.current = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observerRef.current?.disconnect()
        }
      }, { threshold: 0.2 })
      observerRef.current.observe(el)
    }
  }

  return (
    <div ref={setRef} className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-900 font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full"
            style={{
              width: visible ? `${width}%` : '0%',
              transition: `width 1s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
            }}
          />
        </div>
        <span className="text-xs text-gray-400 w-8 text-right">{visible ? value : 0}</span>
      </div>
    </div>
  )
}

function LiveFeed() {
  const [items] = useState([
    { to: 'partner@foodtech.kr', status: 'clicked', time: '2초 전' },
    { to: 'ceo@smartstore.com', status: 'opened', time: '1분 전' },
    { to: 'contact@designlab.kr', status: 'clicked', time: '3분 전' },
    { to: 'info@freshmarket.co', status: 'delivered', time: '5분 전' },
    { to: 'biz@techsolution.kr', status: 'opened', time: '8분 전' },
  ])
  return (
    <div className="space-y-2">
      {items.map((log, i) => (
        <div
          key={log.to}
          className="flex items-center gap-3 py-1.5 hover:bg-white/50 rounded px-2 -mx-2 transition-colors"
          style={{ animation: `fadeSlideIn 0.5s ease ${i * 100}ms both` }}
        >
          <div className={`w-1.5 h-1.5 rounded-full ${log.status === 'clicked' ? 'bg-blue-500' : log.status === 'opened' ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
          <span className="text-xs text-gray-900 flex-1 font-mono">{log.to}</span>
          <span className="text-[10px] text-gray-400">{log.time}</span>
        </div>
      ))}
      <style>{`@keyframes fadeSlideIn { from { opacity:0; transform:translateX(-10px); } to { opacity:1; transform:translateX(0); } }`}</style>
    </div>
  )
}

function ChatBubbles() {
  const msgs = [
    { sent: true, text: '안녕하세요! 업소용 식자재 업종에서 활동하시는 것을 보고 연락드립니다.' },
    { sent: false, text: '관심있습니다! 자세한 조건 알려주실 수 있나요?' },
    { sent: true, text: '네! 제안서 보내드릴게요. 미팅 가능하신 시간 알려주시면 감사하겠습니다.' },
  ]
  return (
    <div className="space-y-3">
      {msgs.map((m, i) => (
        <div
          key={i}
          className={m.sent ? 'ml-auto max-w-[80%]' : 'max-w-[65%]'}
          style={{ animation: `fadeSlideIn 0.5s ease ${i * 300 + 200}ms both` }}
        >
          <div className={`text-sm rounded-2xl px-4 py-2.5 ${m.sent ? 'bg-blue-600 text-white rounded-br-md' : 'bg-gray-100 text-gray-900 rounded-bl-md'}`}>
            {m.text}
          </div>
        </div>
      ))}
      <style>{`@keyframes fadeSlideIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }`}</style>
    </div>
  )
}

function KanbanMock() {
  const [draggedItem, setDraggedItem] = useState(null)
  const [hasDragged, setHasDragged] = useState(false)
  const [stages, setStages] = useState([
    { name: '리드', color: '#6B7280', items: ['프레시마켓\n₩3.2M', '디자인랩\n₩1.5M'] },
    { name: '미팅', color: '#8B5CF6', items: ['테크솔루션\n₩5.0M'] },
    { name: '제안', color: '#F59E0B', items: ['스마트스토어\n₩2.8M'] },
    { name: '성사', color: '#059669', items: ['쿠팡 물류\n₩8.5M'] },
  ])

  return (
    <div>
      {!hasDragged && (
        <p className="text-[10px] text-blue-600 font-medium mb-2 flex items-center gap-1">
          <span className="animate-pulse">👆</span> 카드를 드래그해서 스테이지를 이동해보세요
        </p>
      )}
      <div className="flex gap-3">
        {stages.map((stage, si) => (
          <div
            key={stage.name}
            className="flex-1 min-w-0"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              if (!draggedItem) return
              const newStages = stages.map((s, i) => ({
                ...s,
                items: s.items.filter((item) => item !== draggedItem),
              }))
              newStages[si].items.push(draggedItem)
              setStages(newStages)
              setDraggedItem(null)
              setHasDragged(true)
            }}
          >
            <div className="flex items-center gap-1.5 mb-2 pb-2 border-b border-gray-100">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: stage.color }} />
              <span className="text-[11px] font-semibold text-gray-700">{stage.name}</span>
            </div>
            <div className="space-y-2 min-h-[60px]">
              {stage.items.map((item) => {
                const [name, val] = item.split('\n')
                return (
                  <div
                    key={item}
                    draggable
                    onDragStart={() => setDraggedItem(item)}
                    className="bg-gray-50 rounded-lg p-2.5 border border-gray-100 cursor-grab active:cursor-grabbing hover:border-gray-300 hover:shadow-sm transition-all"
                  >
                    <p className="text-[11px] font-medium text-gray-900">{name}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{val}</p>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
