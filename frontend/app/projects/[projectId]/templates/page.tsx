'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import { api, Template } from '@/lib/api'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Badge } from '@/components/ui'
import { ArrowLeft, ArrowRight, Loader2, CheckCircle, Layout, BookOpen, GraduationCap, Sparkles, Briefcase, Palette } from 'lucide-react'

const TEMPLATE_ICONS: Record<string, any> = {
  minimalist: Layout,
  classic: BookOpen,
  editorial: Palette,
  academic: GraduationCap,
  fantasy: Sparkles,
  business: Briefcase,
}

const CATEGORY_LABELS: Record<string, string> = {
  modern: 'Moderno',
  traditional: 'Tradicional',
  technical: 'Técnico',
  creative: 'Criativo',
  business: 'Negócios',
}

export default function TemplatesPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = params.projectId as string
  const supabase = createClient()

  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)

  useEffect(() => {
    checkAuthAndLoad()
  }, [])

  async function checkAuthAndLoad() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/login')
      return
    }
    api.setToken(session.access_token)
    loadTemplates()
  }

  async function loadTemplates() {
    try {
      const data = await api.getTemplates(projectId)
      setTemplates(data.templates)
    } catch (error: any) {
      console.error('Failed to load templates:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleApplyTemplate(templateKey: string) {
    setApplying(templateKey)
    try {
      await api.applyTemplate(projectId, templateKey)
      setSelectedTemplate(templateKey)
      
      // Pequeno delay antes de redirecionar
      setTimeout(() => {
        router.push(`/projects/${projectId}/preview`)
      }, 1000)
    } catch (error: any) {
      alert(error.message || 'Erro ao aplicar template')
      setApplying(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Voltar
          </Button>
          <h1 className="text-xl font-semibold">Escolher Template</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">Templates de Diagramação</h2>
          <p className="text-gray-600">Escolha o estilo que melhor combina com seu livro</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => {
            const Icon = TEMPLATE_ICONS[template.key] || Layout
            const isSelected = selectedTemplate === template.key
            const isApplying = applying === template.key

            return (
              <Card 
                key={template.key}
                className={`
                  relative transition-all cursor-pointer
                  ${isSelected ? 'ring-2 ring-primary shadow-lg' : 'hover:shadow-md'}
                  ${applying && !isApplying ? 'opacity-50' : ''}
                `}
                onClick={() => !applying && handleApplyTemplate(template.key)}
              >
                {isSelected && (
                  <div className="absolute -top-3 -right-3 bg-primary text-white rounded-full p-1">
                    <CheckCircle className="h-5 w-5" />
                  </div>
                )}
                
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="bg-primary/10 rounded-lg p-3 mb-2">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <Badge variant="secondary">
                      {CATEGORY_LABELS[template.category] || template.category}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <CardDescription>{template.description}</CardDescription>
                </CardHeader>
                
                <CardContent>
                  <Button 
                    className="w-full" 
                    disabled={!!applying}
                    variant={isSelected ? 'default' : 'outline'}
                  >
                    {isApplying ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Aplicando...
                      </>
                    ) : isSelected ? (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Selecionado
                      </>
                    ) : (
                      <>
                        Usar este template
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </main>
    </div>
  )
}
