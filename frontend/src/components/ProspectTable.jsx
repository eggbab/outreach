import { ChevronLeft, ChevronRight, Check, X, ExternalLink } from 'lucide-react'

const statusConfig = {
  collected: { label: '수집', color: 'bg-gray-100 text-gray-700' },
  approved: { label: '승인', color: 'bg-green-100 text-green-700' },
  rejected: { label: '거절', color: 'bg-red-100 text-red-700' },
  sent: { label: '발송완료', color: 'bg-blue-100 text-blue-700' },
}

export default function ProspectTable({
  prospects = [],
  page = 1,
  totalPages = 1,
  onPageChange,
  onApprove,
  onReject,
  onApproveAll,
  showActions = true,
}) {
  return (
    <div>
      {showActions && onApproveAll && (
        <div className="mb-4 flex justify-end">
          <button
            onClick={onApproveAll}
            className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors cursor-pointer"
          >
            전체 승인
          </button>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 font-medium text-gray-600">업체명</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">이메일</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">전화번호</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">인스타그램</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">소스</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">상태</th>
                {showActions && (
                  <th className="text-center px-4 py-3 font-medium text-gray-600">작업</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {prospects.length === 0 ? (
                <tr>
                  <td colSpan={showActions ? 7 : 6} className="px-4 py-12 text-center text-gray-400">
                    수집된 업체가 없습니다
                  </td>
                </tr>
              ) : (
                prospects.map((p) => {
                  const status = statusConfig[p.status] || statusConfig.collected
                  return (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                      <td className="px-4 py-3 text-gray-600">{p.email || '-'}</td>
                      <td className="px-4 py-3 text-gray-600">{p.phone || '-'}</td>
                      <td className="px-4 py-3">
                        {p.instagram ? (
                          <a
                            href={`https://instagram.com/${p.instagram}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline inline-flex items-center gap-1"
                          >
                            @{p.instagram}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{p.source || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
                          {status.label}
                        </span>
                      </td>
                      {showActions && (
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center gap-1">
                            {p.status !== 'approved' && p.status !== 'sent' && onApprove && (
                              <button
                                onClick={() => onApprove(p.id)}
                                className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors cursor-pointer"
                                title="승인"
                              >
                                <Check className="w-4 h-4" />
                              </button>
                            )}
                            {p.status !== 'rejected' && p.status !== 'sent' && onReject && (
                              <button
                                onClick={() => onReject(p.id)}
                                className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer"
                                title="거절"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <span className="text-sm text-gray-600">
              페이지 {page} / {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange?.(page - 1)}
                disabled={page <= 1}
                className="p-1.5 rounded border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => onPageChange?.(page + 1)}
                disabled={page >= totalPages}
                className="p-1.5 rounded border border-gray-300 text-gray-600 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
