import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl border border-gray-200 p-8 sm:p-12">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> 홈으로
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">이용약관</h1>
        <p className="text-sm text-gray-500 mb-8">시행일: 2026년 4월 26일</p>

        <div className="prose prose-sm max-w-none text-gray-700 space-y-6">
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제1조 (목적)</h2>
            <p>본 약관은 Outreach(이하 "회사")가 제공하는 B2B 영업 자동화 서비스(이하 "서비스")의 이용 조건을 규정함을 목적으로 합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제2조 (서비스의 내용)</h2>
            <p>회사는 다음과 같은 서비스를 제공합니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>키워드 기반 잠재고객 정보 수집</li>
              <li>이메일·인스타그램 DM 자동 발송</li>
              <li>발송 성과 분석 및 CRM 기능</li>
              <li>크레딧 기반 사용량 결제</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제3조 (회원가입과 이용)</h2>
            <p>① 이용자는 본 약관에 동의하고 회원가입을 신청함으로써 서비스를 이용할 수 있습니다.</p>
            <p>② 회원은 가입 시 정확한 정보를 제공해야 하며, 변경 시 즉시 수정해야 합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제4조 (이용자의 의무)</h2>
            <p>이용자는 다음 행위를 해서는 안 됩니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>타인의 개인정보를 도용하거나 무단 수집·이용·전송</li>
              <li>스팸 메일, 음란물, 명예훼손, 불법 거래 등 법령 위반</li>
              <li>수집된 정보를 본 서비스 외 목적(재판매 등)에 사용</li>
              <li>서비스를 비정상적으로 우회하거나 시스템에 과도한 부하를 주는 행위</li>
            </ul>
            <p className="mt-2 text-red-700 bg-red-50 p-3 rounded-lg text-sm">
              <strong>중요:</strong> 본 서비스는 합법적인 B2B 영업 활동을 위한 도구입니다. 무차별 스팸 발송으로 인한
              계정 정지(Gmail/Instagram), 법적 분쟁(정보통신망법, 개인정보보호법 위반)에 대한 책임은 전적으로 이용자에게 있습니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제5조 (요금과 결제)</h2>
            <p>① 서비스는 크레딧 기반 종량제로 운영됩니다.</p>
            <p>② 결제는 토스페이먼츠를 통해 이루어집니다.</p>
            <p>③ 환불은 결제일로부터 7일 이내, 미사용 크레딧에 한해 가능합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제6조 (서비스 중지·해지)</h2>
            <p>① 회사는 다음의 경우 서비스 이용을 제한·정지할 수 있습니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>본 약관 위반 시</li>
              <li>법령 위반 또는 공공질서 위반 행위 시</li>
              <li>장기간 미사용(12개월 이상)</li>
            </ul>
            <p>② 회원은 언제든지 회원 탈퇴를 요청할 수 있습니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제7조 (책임의 제한)</h2>
            <p>회사는 다음 사유로 인한 손해에 대해 책임지지 않습니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>이용자의 부주의로 인한 비밀번호 유출, 계정 도용</li>
              <li>외부 서비스(Gmail, Instagram, 토스 등) 장애</li>
              <li>이용자의 발송 활동으로 인한 계정 정지 또는 법적 분쟁</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">제8조 (분쟁 해결)</h2>
            <p>본 약관에 관한 분쟁은 대한민국 법률에 따르며, 회사 본점 소재지 관할 법원을 전속 관할로 합니다.</p>
          </section>

          <section className="mt-8 pt-6 border-t border-gray-200 text-xs text-gray-500">
            <p>문의: <a href="mailto:gimuuuujin@gmail.com" className="text-blue-600">gimuuuujin@gmail.com</a></p>
          </section>
        </div>
      </div>
    </div>
  )
}
