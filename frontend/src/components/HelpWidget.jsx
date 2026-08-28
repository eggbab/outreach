import { useState } from 'react'
import { HelpCircle, X, Mail, BookOpen } from 'lucide-react'

/**
 * 우측 하단에 항상 떠있는 도움말 위젯.
 * - 카카오톡 채널 (배포 후 채널 만들고 URL 교체)
 * - 이메일 문의
 * - 사용 가이드 링크
 */
export default function HelpWidget() {
  const [open, setOpen] = useState(false)

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {open && (
        <div className="mb-3 w-72 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden animate-fade-in">
          <div className="bg-blue-600 text-white px-5 py-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">도움이 필요하세요?</h3>
              <button onClick={() => setOpen(false)} className="hover:bg-blue-700 rounded p-1 cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-blue-100 text-xs mt-1">평일 10시~19시 답변</p>
          </div>

          <div className="p-2">
            <a
              href="mailto:gimuuuujin@gmail.com?subject=Outreach%20문의"
              className="flex items-center gap-3 px-3 py-3 hover:bg-gray-50 rounded-lg cursor-pointer"
            >
              <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center">
                <Mail className="w-4 h-4 text-blue-700" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900">이메일 문의</div>
                <div className="text-xs text-gray-500">gimuuuujin@gmail.com</div>
              </div>
            </a>

            <a
              href="https://outreach-help.notion.site"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 px-3 py-3 hover:bg-gray-50 rounded-lg cursor-pointer"
            >
              <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center">
                <BookOpen className="w-4 h-4 text-green-700" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900">사용 가이드</div>
                <div className="text-xs text-gray-500">처음이세요? 5분 가이드</div>
              </div>
            </a>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen(!open)}
        className="w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center cursor-pointer transition-transform hover:scale-105"
        aria-label="도움말"
      >
        {open ? <X className="w-6 h-6" /> : <HelpCircle className="w-6 h-6" />}
      </button>
    </div>
  )
}
