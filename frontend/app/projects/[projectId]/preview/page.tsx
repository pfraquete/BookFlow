'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { api, PreviewData, ExportStatus } from '@/lib/api'
import { Button, Card, CardContent, Progress } from '@/components/ui'
import { formatBytes } from '@/lib/utils'
import { ArrowLeft, Download, Loader2, CheckCircle, RefreshCw, FileText, Palette } from 'lucide-react'

export default function PreviewPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params.projectId as string
  const supabase = createClient()

  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    checkAuthAndLoad()
  }, [])

  useEffect(() => {
    if (exportStatus && ['pdf_generating', 'approved'].includes(exportStatus.status)) {
      const interval = setInterval(checkExportStatus, 3000)
      return () => clearInterval(interval)
    }
  }, [exportStatus])

  async function checkAuthAndLoad() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/login')
      return
    }
    api.setToken(session.access_token)
    loadPreview()
    checkExportStatus()
  }

  async function loadPreview() {
    try {
      const data = await api.getPreview(projectId)
      setPreview(data)
      
      if (data.preview_url) {
        setPreviewUrl(data.preview_url)
      }
    } catch (error: any) {
      console.error('Failed to load preview:', error)
      // Se não tem preview, redirecionar para templates
      router.push(`/projects/${projectId}/templates`)
    } finally {
      setLoading(false)
    }
  }

  async function checkExportStatus() {
    try {
      const status = await api.getExportStatus(projectId)
      setExportStatus(status)
    } catch (error) {
      console.error('Failed to check export status:', error)
    }
  }

  async function handleApprove() {
    setExporting(true)
    try {
      const result = await api.approveAndExport(projectId)
      setExportStatus({
        project_id: projectId,
        status: result.status,
        message: result.message,
        download_url: result.download_url,
        page_count: result.page_count,
        file_size_bytes: result.file_size_bytes,
      })
      
      if (result.download_url) {
        // PDF já estava pronto
        setExporting(false)
      }
    } catch (error: any) {
      alert(error.message || 'Erro ao aprovar')
      setExporting(false)
    }
  }

  async function handleDownload() {
    try {
      const { download_url, filename } = await api.getDownloadLink(projectId)
      
      // Abrir em nova aba para download
      window.open(download_url, '_blank')
    } catch (error: any) {
      alert(error.message || 'Erro ao baixar')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const isExporting = exportStatus?.status === 'pdf_generating'
  const isExported = exportStatus?.status === 'pdf_generated'

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push('/')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Voltar
            </Button>
            <h1 className="text-xl font-semibold">Preview da Diagramação</h1>
          </div>
          
          <div className="flex items-center gap-4">
            {preview && (
              <div className="text-sm text-gray-500">
                Template: <span className="font-medium">{preview.template_name}</span>
                {preview.word_count && (
                  <span className="ml-4">{preview.word_count.toLocaleString()} palavras</span>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Preview Frame */}
        <div className="flex-1 p-4">
          <div className="bg-white rounded-lg shadow-lg h-full overflow-hidden">
            {previewUrl ? (
              <iframe
                src={previewUrl}
                className="w-full h-full border-0"
                title="Preview do livro"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4" />
                  <p>Preview não disponível</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white border-l p-4 space-y-4">
          {/* Template Info */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="bg-primary/10 rounded-lg p-2">
                  <Palette className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium">{preview?.template_name}</p>
                  <p className="text-sm text-gray-500">Template atual</p>
                </div>
              </div>
              
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => router.push(`/projects/${projectId}/templates`)}
                disabled={isExporting}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Trocar Template
              </Button>
            </CardContent>
          </Card>

          {/* Export Status */}
          {isExporting && (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center space-y-3">
                  <Loader2 className="h-8 w-8 mx-auto animate-spin text-primary" />
                  <p className="font-medium">Gerando PDF...</p>
                  <p className="text-sm text-gray-500">Isso pode levar alguns minutos</p>
                  <Progress value={66} />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Download Ready */}
          {isExported && exportStatus?.download_url && (
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-6">
                <div className="text-center space-y-3">
                  <CheckCircle className="h-8 w-8 mx-auto text-green-500" />
                  <p className="font-medium text-green-700">PDF Pronto!</p>
                  {exportStatus.page_count && (
                    <p className="text-sm text-green-600">
                      {exportStatus.page_count} páginas
                      {exportStatus.file_size_bytes && (
                        <> · {formatBytes(exportStatus.file_size_bytes)}</>
                      )}
                    </p>
                  )}
                  <Button onClick={handleDownload} className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Baixar PDF
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Approve Button */}
          {!isExporting && !isExported && (
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Satisfeito com o resultado? Aprove para gerar o PDF final.
                  </p>
                  <Button 
                    onClick={handleApprove} 
                    className="w-full"
                    disabled={exporting}
                  >
                    {exporting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processando...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Aprovar e Gerar PDF
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stats */}
          {preview?.word_count && (
            <Card>
              <CardContent className="pt-6">
                <h4 className="font-medium mb-3">Estatísticas</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Palavras</span>
                    <span>{preview.word_count.toLocaleString()}</span>
                  </div>
                  {exportStatus?.page_count && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Páginas</span>
                      <span>{exportStatus.page_count}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
