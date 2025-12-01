'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { api, Project } from '@/lib/api'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Badge } from '@/components/ui'
import { STATUS_LABELS, STATUS_COLORS, formatDate } from '@/lib/utils'
import { Plus, BookOpen, LogOut, Trash2, ArrowRight, Loader2 } from 'lucide-react'

export default function Dashboard() {
  const router = useRouter()
  const supabase = createClient()
  
  const [user, setUser] = useState<any>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    checkAuth()
  }, [])

  async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession()
    
    if (!session) {
      router.push('/login')
      return
    }

    setUser(session.user)
    api.setToken(session.access_token)
    loadProjects()
  }

  async function loadProjects() {
    try {
      const data = await api.listProjects()
      setProjects(data.projects)
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateProject() {
    if (!newTitle.trim()) return

    setCreating(true)
    try {
      const project = await api.createProject(newTitle)
      router.push(`/projects/${project.id}/upload`)
    } catch (error: any) {
      alert(error.message)
    } finally {
      setCreating(false)
    }
  }

  async function handleDeleteProject(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm('Tem certeza que deseja excluir este projeto?')) return

    try {
      await api.deleteProject(id)
      setProjects(projects.filter(p => p.id !== id))
    } catch (error: any) {
      alert(error.message)
    }
  }

  async function handleLogout() {
    await supabase.auth.signOut()
    router.push('/login')
  }

  function getNextStep(status: string): { href: string; label: string } | null {
    const steps: Record<string, { path: string; label: string }> = {
      created: { path: 'upload', label: 'Enviar PDF' },
      uploaded: { path: 'upload', label: 'Aguardando...' },
      extracting: { path: 'upload', label: 'Processando...' },
      parsed: { path: 'templates', label: 'Escolher Template' },
      normalizing: { path: 'upload', label: 'Normalizando...' },
      normalized: { path: 'templates', label: 'Escolher Template' },
      templated: { path: 'preview', label: 'Ver Preview' },
      approved: { path: 'preview', label: 'Ver Preview' },
      exporting: { path: 'preview', label: 'Exportando...' },
      exported: { path: 'preview', label: 'Baixar PDF' },
    }
    return steps[status] ? { href: steps[status].path, label: steps[status].label } : null
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold">BookFlow</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              Sair
            </Button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions */}
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-xl font-semibold">Meus Projetos</h2>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Projeto
          </Button>
        </div>

        {/* Create Modal */}
        {showCreate && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Novo Projeto</CardTitle>
              <CardDescription>Digite um título para seu livro</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Input
                  placeholder="Título do livro"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                  autoFocus
                />
                <Button onClick={handleCreateProject} disabled={creating || !newTitle.trim()}>
                  {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Criar'}
                </Button>
                <Button variant="outline" onClick={() => { setShowCreate(false); setNewTitle('') }}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Projects Grid */}
        {projects.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <BookOpen className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium mb-2">Nenhum projeto ainda</h3>
              <p className="text-gray-500 mb-4">Crie seu primeiro projeto para começar a diagramar</p>
              <Button onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Criar Projeto
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => {
              const nextStep = getNextStep(project.status)
              
              return (
                <Card 
                  key={project.id} 
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => nextStep && router.push(`/projects/${project.id}/${nextStep.href}`)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg truncate pr-4">{project.title}</CardTitle>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-8 w-8 text-gray-400 hover:text-red-500"
                        onClick={(e) => handleDeleteProject(project.id, e)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    {project.original_filename && (
                      <CardDescription className="truncate">
                        {project.original_filename}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-between items-center">
                      <Badge className={STATUS_COLORS[project.status] || 'bg-gray-100'}>
                        {STATUS_LABELS[project.status] || project.status}
                      </Badge>
                      {nextStep && (
                        <span className="text-sm text-primary flex items-center gap-1">
                          {nextStep.label}
                          <ArrowRight className="h-4 w-4" />
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      {formatDate(project.updated_at)}
                    </p>
                    {project.error_message && (
                      <p className="text-xs text-red-500 mt-2 truncate">
                        {project.error_message}
                      </p>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
