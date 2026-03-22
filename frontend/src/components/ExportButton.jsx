import { Download } from 'lucide-react'
import api from '../lib/api'

export default function ExportButton({ projectId }) {
  const handleExport = async () => {
    try {
      const res = await api.get(`/projects/${projectId}/export/prospects`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `prospects_${projectId}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch {}
  }

  return (
    <button
      onClick={handleExport}
      className="inline-flex items-center gap-2 px-3 py-1.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
    >
      <Download className="w-4 h-4" />
      CSV 내보내기
    </button>
  )
}
