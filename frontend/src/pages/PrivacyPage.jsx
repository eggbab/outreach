import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl border border-gray-200 p-8 sm:p-12">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> 홈으로
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">개인정보처리방침</h1>
        <p className="text-sm text-gray-500 mb-8">시행일: 2026년 4월 26일</p>

        <div className="prose prose-sm max-w-none text-gray-700 space-y-6">
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">1. 수집하는 개인정보</h2>
            <p><strong>회원가입 시</strong></p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>필수: 이메일, 비밀번호(암호화 저장), 이름</li>
            </ul>
            <p className="mt-3"><strong>서비스 이용 중 자동 수집</strong></p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>접속 IP, 쿠키, 서비스 이용 기록</li>
              <li>발송 통계(이메일 오픈·클릭 수)</li>
            </ul>
            <p className="mt-3"><strong>결제 시</strong></p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>결제 내역(카드 정보는 토스페이먼츠가 직접 보관, 회사는 미보유)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">2. 개인정보 이용 목적</h2>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>회원 식별 및 로그인</li>
              <li>서비스 제공·요금 정산</li>
              <li>고객 문의 응대</li>
              <li>서비스 개선을 위한 통계 분석</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">3. 보유 기간</h2>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>회원 정보: 회원 탈퇴 시까지 (탈퇴 후 즉시 파기)</li>
              <li>결제 기록: 5년 (전자상거래법)</li>
              <li>접속 로그: 3개월 (통신비밀보호법)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">4. 제3자 제공</h2>
            <p>회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만 다음의 경우는 예외입니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>법령에 의한 제출 의무가 있는 경우</li>
              <li>이용자가 사전에 동의한 경우</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">5. 처리 위탁</h2>
            <table className="w-full text-sm border border-gray-200 mt-2">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">위탁받는 자</th>
                  <th className="px-3 py-2 text-left">위탁 업무</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-200">
                  <td className="px-3 py-2">Supabase (DB 호스팅)</td>
                  <td className="px-3 py-2">회원 데이터 저장</td>
                </tr>
                <tr className="border-t border-gray-200">
                  <td className="px-3 py-2">토스페이먼츠</td>
                  <td className="px-3 py-2">결제 처리</td>
                </tr>
                <tr className="border-t border-gray-200">
                  <td className="px-3 py-2">Render / AWS</td>
                  <td className="px-3 py-2">서버 호스팅</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">6. 이용자 권리</h2>
            <p>이용자는 언제든지 다음의 권리를 행사할 수 있습니다.</p>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>개인정보 열람·수정 요청</li>
              <li>회원 탈퇴 및 개인정보 삭제 요청</li>
              <li>개인정보 처리에 대한 동의 철회</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">7. 안전성 확보 조치</h2>
            <ul className="list-disc ml-6 mt-2 space-y-1">
              <li>비밀번호: bcrypt 단방향 암호화</li>
              <li>민감 데이터(Gmail 앱 비밀번호 등): Fernet 대칭 암호화</li>
              <li>전송 구간: HTTPS/TLS 암호화</li>
              <li>접근 권한 통제 및 접속 로그 보관</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-2">8. 개인정보 보호 책임자</h2>
            <p>이름: 김우진<br/>
            연락처: <a href="mailto:weefree24@gmail.com" className="text-blue-600">weefree24@gmail.com</a></p>
            <p className="mt-3 text-sm text-gray-500">
              개인정보 침해에 대한 신고·상담이 필요하신 경우 아래 기관에 문의하실 수 있습니다.
            </p>
            <ul className="list-disc ml-6 mt-2 space-y-1 text-sm text-gray-500">
              <li>개인정보보호위원회: 1833-6972</li>
              <li>개인정보 침해신고센터: 118</li>
              <li>대검찰청 사이버수사과: 1301</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
