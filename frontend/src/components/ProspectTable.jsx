import { useState } from 'react'
import { ChevronLeft, ChevronRight, Check, X, ExternalLink, Download, ShieldX } from 'lucide-react'
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

const sourceConfig = {
  naver: { label: '네이버 검색', color: 'bg-green-100 text-green-700' },
  naver_shopping: { label: '네이버 쇼핑', color: 'bg-green-100 text-green-700' },
  naver_map: { label: '네이버 지도', color: 'bg-green-100 text-green-700' },
  kakao: { label: '카카오 지도', color: 'bg-yellow-100 text-yellow-700' },
  ftc: { label: '정부 등록부', color: 'bg-indigo-100 text-indigo-700' },
  google: { label: '구글', color: 'bg-blue-100 text-blue-700' },
  instagram: { label: '인스타그램', color: 'bg-pink-100 text-pink-700' },
}

const getScoreColor = (score) => {
  if (score >= 70) return 'text-green-600 bg-green-50'
  if (score >= 40) return 'text-yellow-600 bg-yellow-50'
  return 'text-gray-500 bg-gray-50'
}

export default function ProspectTable({
  prospects = [],
  channelStats = null,   // {email, phone, instagram, email_or_instagram, none}
  total = 0,
  page = 1,
  totalPages = 1,
  onPageChange,
  onApprove,
  onReject,
  onApproveAll,
  showActions = true,
  projectId,
  onBlacklist,
}) {
  const [selectedProspect, setSelectedProspect] = useState(null)

  return (
    <div>
      {/* 연락 수단 집계 — 발송 계획을 세울 수 있게 채널별 보유 현황을 먼저 보여준다 */}
      {channelStats && total > 0 && (
        <div className="mb-4 bg-white border border-gray-200 rounded-lg px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
            <span className="font-medium text-gray-900">전체 {total.toLocaleString()}곳</span>
            <span className="text-gray-300">|</span>
            <span className="text-gray-600">📧 이메일 보유 <b className="text-blue-600">{channelStats.email}</b>곳</span>
            <span className="text-gray-600">📷 인스타그램 보유 <b className="text-pink-600">{channelStats.instagram}</b>곳</span>
            <span className="text-gray-600">📞 전화번호 보유 <b className="text-green-600">{channelStats.phone}</b>곳</span>
            <span className="text-gray-300">|</span>
            <span className="text-gray-600">발송 가능(이메일·인스타 중 하나 이상) <b className="text-gray-900">{channelStats.email_or_instagram}</b>곳</span>
            {channelStats.none > 0 && (
              <span className="text-gray-400">연락처 없음 {channelStats.none}곳</span>
            )}
          </div>
        </div>
      )}

      {showActions && (
        <div className="mb-4 flex justify-between items-center gap-3">
          <div>
            {projectId && <ExportButton projectId={projectId} />}
          </div>
          {onApproveAll && (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline text-xs text-gray-400">
                승인한 업체만 발송 대상이 됩니다
              </span>
              <button
                onClick={onApproveAll}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors cursor-pointer"
              >
                수집된 업체 전체 승인
              </button>
            </div>
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">수집 경로</th>
                <th
                  className="text-center px-4 py-3 font-medium text-gray-600"
                  title="이 업체가 영업 메일에 얼마나 반응해왔는지 (열람·클릭·답장 이력 기반, 0~100). 높을수록 답장 확률이 높습니다."
                >
                  반응 점수 ⓘ
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">상태</th>
                {showActions && (
                  <th className="text-center px-4 py-3 font-medium text-gray-600">승인/제외</th>
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
                        <div className="flex items-center gap-1.5">
                          {p.name}
                          {p.website && (
                            <a
                              href={p.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              title={p.website}
                              className="text-gray-400 hover:text-blue-600"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                        {p.description && (
                          <p className="mt-0.5 text-xs font-normal text-gray-500 truncate max-w-[16rem]" title={p.description}>
                            {p.description}
                          </p>
                        )}
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
                      <td className="px-4 py-3">
                        {p.source ? (
                          <span className="inline-flex flex-wrap items-center gap-1">
                            {p.source.split('+').map((srcKey) => (
                              <span key={srcKey} className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${sourceConfig[srcKey]?.color || 'bg-gray-100 text-gray-600'}`}>
                                {sourceConfig[srcKey]?.label || srcKey}
                              </span>
                            ))}
                            {p.source.includes('+') && (
                              <span
                                className="inline-flex px-1.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700"
                                title="두 곳 이상에서 같은 업체로 확인됨 — 정보 신뢰도가 높습니다"
                              >✓ 교차확인</span>
                            )}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                        {p.keyword && (
                          <p className="mt-0.5 text-xs text-gray-400" title="이 키워드로 검색해서 찾았습니다">
                            "{p.keyword}"
                          </p>
                        )}
                      </td>
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
                                title="발송 대상으로 승인"
                              >
                                <Check className="w-4 h-4" />
                              </button>
                            )}
                            {p.status !== 'rejected' && p.status !== 'sent' && onReject && (
                              <button
                                onClick={() => onReject(p.id)}
                                className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer"
                                title="발송 대상에서 제외"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            )}
                            {p.status === 'rejected' && onBlacklist && (
                              <button
                                onClick={() => onBlacklist(p)}
                                className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors cursor-pointer"
                                title="블랙리스트에 추가"
                              >
                                <ShieldX className="w-4 h-4" />
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
