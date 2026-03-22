import { useState } from 'react'
import { ChevronLeft, ChevronRight, Check, X, ExternalLink, Download } from 'lucide-react'
import ProspectDetail from './ProspectDetail'
import ExportButton from './ExportButton'

const statusConfig = {
  collected: { label: '수집', color: 'bg-gray-100 text-gray-700' },
  approved: { label: '승인', color: 'bg-green-100 text-green-700' },
  rejected: { label: '거절', color: 'bg-red-100 text-red-700' },
  email_sent: { label: '이메일 발송', color: 'bg-blue-100 text-blue-700' },
  dm_sent: { label: 'DM 발송', color: 'bg-purple-100 text-purple-700' },
  sent: { label: '발송완료', color: 'bg-blue-100 text-blue-700' },
}

const getScoreColor = (score) => {
  if (score >= 70) return 'text-green-600 bg-green-50'
  if (score >= 40) return 'text-yellow-600 bg-yellow-50'
  return 'text-gray-500 bg-gray-50'
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
  projectId,
}) {
  const [selectedProspect, setSelectedProspect] = useState(null)

  return (
    <div>
      {showActions && (
        <div className="mb-4 flex justify-between items-center">
          <div>
            {projectId && <ExportButton projectId={projectId} />}
          </div>
          {onApproveAll && (
            <button
              onClick={onApproveAll}
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors cursor-pointer"
            >
              전체 승인
            </button>
          )}
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
                <th className="text-center px-4 py-3 font-medium text-gray-600">스코어</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">상태</th>
                {showActions && (
                  <th className="text-center px-4 py-3 font-medium text-gray-600">작업</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {prospects.length === 0 ? (
                <tr>
                  <td colSpan={showActions ? 8 : 7} className="px-4 py-12 text-center text-gray-400">
                    수집된 업체가 없습니다
                  </td>
                </tr>
              ) : (
                prospects.map((p) => {
                  const status = statusConfig[p.status] || statusConfig.collected
                  return (
                    <tr
                      key={p.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedProspect(p)}
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {p.name}
                        {p.tags && p.tags.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {p.tags.slice(0, 3).map((t) => (
                              <span key={t.id} className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: t.tag?.color || '#6B7280' }} />
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{p.email || '-'}</td>
                      <td className="px-4 py-3 text-gray-600">{p.phone || '-'}</td>
                      <td className="px-4 py-3">
                        {p.instagram ? (
                          <a
                            href={`https://instagram.com/${p.instagram}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline inline-flex items-center gap-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            @{p.instagram}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{p.source || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${getScoreColor(p.score || 0)}`}>
                          {p.score || 0}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${status.color}`}>
                          {status.label}
                        </span>
                      </td>
                      {showActions && (
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
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

      {selectedProspect && (
        <ProspectDetail
          prospect={selectedProspect}
          projectId={projectId}
          onClose={() => setSelectedProspect(null)}
        />
      )}
    </div>
  )
}
