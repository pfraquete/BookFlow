import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export function formatDate(date: string | Date) {
  return new Date(date).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export const STATUS_LABELS: Record<string, string> = {
  created: 'Criado',
  uploaded: 'PDF Enviado',
  extracting: 'Extraindo...',
  parsed: 'Analisado',
  normalizing: 'Normalizando...',
  normalized: 'Pronto para Template',
  templated: 'Template Aplicado',
  approved: 'Aprovado',
  exporting: 'Exportando...',
  exported: 'PDF Pronto',
  error: 'Erro'
}

export const STATUS_COLORS: Record<string, string> = {
  created: 'bg-gray-100 text-gray-800',
  uploaded: 'bg-blue-100 text-blue-800',
  extracting: 'bg-yellow-100 text-yellow-800',
  parsed: 'bg-blue-100 text-blue-800',
  normalizing: 'bg-yellow-100 text-yellow-800',
  normalized: 'bg-green-100 text-green-800',
  templated: 'bg-purple-100 text-purple-800',
  approved: 'bg-purple-100 text-purple-800',
  exporting: 'bg-yellow-100 text-yellow-800',
  exported: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800'
}
