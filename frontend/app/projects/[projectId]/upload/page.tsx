'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useDropzone } from 'react-dropzone'
import { createClient } from '@/lib/supabase'
import { api, ProcessingStatus } from '@/lib/api'
import { Button, Card, CardContent, CardHeader, CardTitle, Progress } from '@/components/ui'
import { formatBytes } from '@/lib/utils'
import { Upload, FileText, CheckCircle, Loader2, AlertCircle, ArrowRight, ArrowLeft } from 'lucide-react'

export default function UploadPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params.projectId as string
  const supabase = createClient()

  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null)
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)

  useEffect(() => {
    checkAuth()
  }, [])

  useEffect(() => {
    if (processingStatus && ['extracting', 'normalizing', 'uploaded'].includes(processingStatus.status)) {
      const interval = setInterval(checkStatus, 2000)
      return () => clearInterval(interval)
    }
  }, [processingStatus])

  async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/login')
      return
    }
    api.setToken(session.access_token)
    checkStatus()
  }

  async function checkStatus() {
    try {
      const status = await api.getProcessingStatus(projectId)
      setProcessingStatus(status)
      
      // Se já está normalizado ou com template, redirecionar
      if (['normalized', 'templated', 'approved', 'exported'].includes(status.status)) {
        router.push(`/projects/${projectId}/templates`)
      }
    } catch (error) {
      console.error('Failed to check status:', error)
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const pdfFile = acceptedFiles.find(f => f.type === 'application/pdf')
    if (pdfFile) {
      setFile(pdfFile)
      setError('')
    } else {
      setError('Apenas arquivos PDF são aceitos')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100MB
  })

  async function handleUpload() {
    if (!file) return

    setUploading(true)
    setUploadProgress(0)
    setError('')

    try {
      // Simular progresso de upload
      const progressInterval = setInterval(() => {
        setUploadProgress(p => Math.min(p + 10, 90))
      }, 200)

      await api.uploadPdf(projectId, file)
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      // Iniciar polling de status
      checkStatus()
    } catch (err: any) {
      setError(err.message || 'Erro ao enviar arquivo')
      setUploading(false)
    }
  }

  const isProcessing = processingStatus && ['uploaded', 'extracting', 'normalizing'].includes(processingStatus.status)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar
          </Button>
          <h1 className="text-xl font-semibold">Enviar PDF</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Upload Area */}
        {!isProcessing && !uploading && (
          <Card>
            <CardHeader>
              <CardTitle>Upload do PDF</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`
                  border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
                  ${isDragActive ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-primary'}
                  ${file ? 'border-green-500 bg-green-50' : ''}
                `}
              >
                <input {...getInputProps()} />
                
                {file ? (
                  <div className="space-y-2">
                    <FileText className="h-12 w-12 mx-auto text-green-500" />
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-gray-500">{formatBytes(file.size)}</p>
                    <p className="text-sm text-green-600">Pronto para enviar</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="h-12 w-12 mx-auto text-gray-400" />
                    <p className="font-medium">
                      {isDragActive ? 'Solte o arquivo aqui' : 'Arraste um PDF ou clique para selecionar'}
                    </p>
                    <p className="text-sm text-gray-500">Máximo 100MB</p>
                  </div>
                )}
              </div>

              {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  {error}
                </div>
              )}

              {file && (
                <div className="mt-6 flex justify-end gap-4">
                  <Button variant="outline" onClick={() => setFile(null)}>
                    Trocar arquivo
                  </Button>
                  <Button onClick={handleUpload}>
                    Enviar PDF
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Upload Progress */}
        {uploading && uploadProgress < 100 && (
          <Card>
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary" />
                <h3 className="text-lg font-medium">Enviando arquivo...</h3>
                <Progress value={uploadProgress} className="max-w-md mx-auto" />
                <p className="text-sm text-gray-500">{uploadProgress}%</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Processing Status */}
        {(isProcessing || uploadProgress === 100) && processingStatus && (
          <Card>
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                {processingStatus.status === 'error' ? (
                  <>
                    <AlertCircle className="h-12 w-12 mx-auto text-red-500" />
                    <h3 className="text-lg font-medium text-red-600">Erro no processamento</h3>
                    <p className="text-gray-600">{processingStatus.error}</p>
                    <Button onClick={() => { setFile(null); setUploading(false); setUploadProgress(0) }}>
                      Tentar novamente
                    </Button>
                  </>
                ) : (
                  <>
                    <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary" />
                    <h3 className="text-lg font-medium">{processingStatus.message}</h3>
                    <Progress value={processingStatus.progress || 0} className="max-w-md mx-auto" />
                    <p className="text-sm text-gray-500">
                      Isso pode levar alguns minutos para livros grandes...
                    </p>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Success */}
        {processingStatus?.status === 'normalized' && (
          <Card>
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
                <h3 className="text-lg font-medium">PDF processado com sucesso!</h3>
                <p className="text-gray-600">Agora escolha um template de diagramação</p>
                <Button onClick={() => router.push(`/projects/${projectId}/templates`)}>
                  Escolher Template
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
