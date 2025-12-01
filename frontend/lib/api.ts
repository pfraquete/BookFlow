const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiClient {
  private token: string | null = null

  setToken(token: string) {
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_BASE}/api/v1${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Projects
  async createProject(title: string) {
    return this.request<{ id: string; title: string; status: string }>('/projects', {
      method: 'POST',
      body: JSON.stringify({ title }),
    })
  }

  async listProjects() {
    return this.request<{ projects: Project[]; total: number }>('/projects')
  }

  async getProject(projectId: string) {
    return this.request<ProjectDetail>(`/projects/${projectId}`)
  }

  async deleteProject(projectId: string) {
    return this.request<void>(`/projects/${projectId}`, { method: 'DELETE' })
  }

  // Upload
  async uploadPdf(projectId: string, file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData()
    formData.append('file', file)

    const headers: HeadersInit = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_BASE}/api/v1/projects/${projectId}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(error.detail)
    }

    return response.json()
  }

  async getProcessingStatus(projectId: string) {
    return this.request<ProcessingStatus>(`/projects/${projectId}/status`)
  }

  // Templates
  async getTemplates(projectId: string) {
    return this.request<{ templates: Template[] }>(`/projects/${projectId}/preview-templates`)
  }

  async applyTemplate(projectId: string, templateKey: string) {
    return this.request<{ success: boolean; message: string; rendition_id: string; preview_url: string }>(
      `/projects/${projectId}/apply-template`,
      {
        method: 'POST',
        body: JSON.stringify({ template_key: templateKey }),
      }
    )
  }

  // Preview
  async getPreview(projectId: string) {
    return this.request<PreviewData>(`/projects/${projectId}/preview`)
  }

  getPreviewHtmlUrl(projectId: string) {
    return `${API_BASE}/api/v1/projects/${projectId}/preview/html`
  }

  // Export
  async approveAndExport(projectId: string) {
    return this.request<ExportResponse>(`/projects/${projectId}/approve`, {
      method: 'POST',
    })
  }

  async getExportStatus(projectId: string) {
    return this.request<ExportStatus>(`/projects/${projectId}/export-status`)
  }

  async getDownloadLink(projectId: string) {
    return this.request<{ download_url: string; filename: string }>(`/projects/${projectId}/download`)
  }
}

// Types
export interface Project {
  id: string
  title: string
  original_filename: string | null
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ProjectDetail extends Project {
  upload: {
    id: string
    storage_path: string
    original_filename: string
    file_size_bytes: number
    pages_count: number | null
  } | null
  current_rendition: {
    id: string
    template_id: string
    status: string
    preview_html_path: string | null
    final_pdf_path: string | null
  } | null
  structure_stats: {
    word_count: number | null
    chapter_count: number | null
    image_count: number | null
  } | null
}

export interface ProcessingStatus {
  project_id: string
  status: string
  message: string
  progress: number | null
  error: string | null
}

export interface Template {
  key: string
  name: string
  description: string
  category: string
  preview_thumbnail_url: string | null
}

export interface PreviewData {
  project_id: string
  template_key: string
  template_name: string
  preview_html: string | null
  preview_url: string | null
  page_count: number | null
  word_count: number | null
}

export interface ExportResponse {
  success: boolean
  message: string
  status: string
  download_url: string | null
  page_count: number | null
  file_size_bytes: number | null
}

export interface ExportStatus {
  project_id: string
  status: string
  message: string
  download_url: string | null
  page_count: number | null
  file_size_bytes: number | null
}

export const api = new ApiClient()
