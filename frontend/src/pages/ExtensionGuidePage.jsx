import { useState } from 'react'
import { Download, Chrome, Instagram, CheckCircle2, AlertTriangle } from 'lucide-react'

/**
 * 크롬 확장 설치 가이드.
 * 사용자가 인스타 DM을 안전하게 발송하기 위한 모든 단계를 한 페이지에 안내.
 */
export default function ExtensionGuidePage() {
  const [downloading, setDownloading] = useState(false)

  const downloadExtension = async () => {
    setDownloading(true)
    try {
      const res = await fetch('/api/extension/download', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      })
      if (!res.ok) throw new Error('다운로드 실패')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'outreach-extension.zip'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert('다운로드에 실패했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">인스타그램 DM 자동화 설치</h1>
        <p className="text-sm text-gray-500 mt-1">
          크롬 확장을 설치하면, <strong>본인 브라우저의 본인 인스타 세션</strong>으로 안전하게 DM을 자동 발송합니다.
        </p>
      </div>

      {/* 왜 확장인가? */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-5 mb-6">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-green-900">왜 크롬 확장으로 보내나요?</h3>
            <p className="text-sm text-green-800 mt-1 leading-relaxed">
              인스타그램은 데이터센터 IP에서의 자동 로그인을 매우 빠르게 감지·정지합니다.
              크롬 확장은 <strong>이미 사용자가 로그인한 본인 브라우저</strong>에서 동작하기 때문에,
              인스타 입장에선 "사용자가 직접 메시지 버튼을 누른 것"과 구분되지 않아 정지 위험이 가장 낮습니다.
            </p>
          </div>
        </div>
      </div>

      {/* 4단계 설치 */}
      <div className="space-y-4 mb-6">
        <Step
          num="1"
          icon={Download}
          title="확장 다운로드"
          desc="압축파일(.zip)을 받아 적당한 폴더에 풀어두세요."
        >
          <button
            onClick={downloadExtension}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-4 h-4" />
            {downloading ? '다운로드 중...' : '확장 다운로드 (.zip)'}
          </button>
          <p className="text-xs text-gray-500 mt-2">
            맥: 다운로드 폴더에서 zip을 더블클릭해서 풀기 · 윈도우: 우클릭 → 압축 풀기
          </p>
        </Step>

        <Step num="2" icon={Chrome} title="크롬에 확장 설치">
          <ol className="text-sm text-gray-700 space-y-1.5 list-decimal list-inside">
            <li>크롬 주소창에 <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">chrome://extensions</code> 입력 후 엔터</li>
            <li>오른쪽 위 <strong>"개발자 모드"</strong> 토글을 켭니다</li>
            <li>왼쪽 위 <strong>"압축 해제된 확장 프로그램 로드"</strong> 클릭</li>
            <li>1단계에서 풀어둔 <strong>outreach-extension</strong> 폴더 선택</li>
            <li>오른쪽 위 퍼즐 아이콘 → "Outreach DM" 옆 압정을 눌러 고정</li>
          </ol>
        </Step>

        <Step num="3" icon={Instagram} title="인스타그램에 본인 계정으로 로그인">
          <p className="text-sm text-gray-700 mb-2">
            크롬에서 새 탭을 열고 <a href="https://www.instagram.com" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">instagram.com</a>으로 이동해 평소처럼 로그인합니다.
          </p>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-900">
            ⚠️ <strong>메인 계정 사용 비추천.</strong> 영구 정지 위험. 새 부계정을 만들어 최소 1~2주 일반 활동 (팔로우·좋아요·댓글) 후에 DM 발송을 시작하세요.
          </div>
        </Step>

        <Step num="4" icon={CheckCircle2} title="확장에 Outreach 계정 로그인">
          <p className="text-sm text-gray-700">
            크롬 우측 상단 퍼즐 아이콘 → <strong>"Outreach DM"</strong> 클릭 → 우리 사이트에 가입한 이메일·비밀번호로 로그인.
            로그인하면 확장이 자동으로 발송 대상을 가져옵니다.
          </p>
        </Step>
      </div>

      {/* 발송하기 */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
        <h3 className="font-semibold text-blue-900 mb-2">설치 후 — 어떻게 발송하나요?</h3>
        <ol className="text-sm text-blue-800 space-y-1.5 list-decimal list-inside">
          <li>우리 사이트에서 프로젝트 만들고 키워드 추가</li>
          <li>잠재고객 수집 → 인스타 핸들 있는 사람 "승인"</li>
          <li>설정 페이지에서 DM 메시지 작성</li>
          <li><strong>인스타 탭이 열려 있는 상태</strong>에서 확장 팝업의 "발송 시작" 클릭</li>
          <li>확장이 자동으로 한 명씩 90~180초 간격으로 발송 (백그라운드)</li>
        </ol>
      </div>

      {/* 벤 방지 가이드 */}
      <div className="bg-red-50 border border-red-200 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900 mb-2">계정 정지 방지 — 꼭 지켜주세요</h3>
            <ul className="text-sm text-red-800 space-y-1.5 list-disc list-inside">
              <li><strong>신규 계정은 첫 2주간 DM 금지</strong> — 일반 활동만 (팔로우/좋아요/댓글)</li>
              <li><strong>일일 한도 15건 이하</strong> — 성숙 계정도 30건 이하 권장</li>
              <li>발송 간격 <strong>3~8분</strong> — 확장이 자동으로 랜덤 적용</li>
              <li>똑같은 메시지 반복 X — 시스템이 자동으로 인사말/마무리 미세 변형</li>
              <li>스팸 신고 받으면 즉시 멈추세요. 확장이 감지하면 자동 중단</li>
              <li>메시지에 <strong>링크 포함하면 차단 위험 급증</strong></li>
              <li>이 도구로 인한 계정 정지는 사용자 책임입니다 (이용약관 참조)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

function Step({ num, icon: Icon, title, desc, children }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-start gap-4">
        <div className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
          {num}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className="w-4 h-4 text-gray-500" />
            <h3 className="font-semibold text-gray-900">{title}</h3>
          </div>
          {desc && <p className="text-sm text-gray-600 mb-3">{desc}</p>}
          {children}
        </div>
      </div>
    </div>
  )
}
