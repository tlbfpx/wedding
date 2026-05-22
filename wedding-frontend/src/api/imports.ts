import request from './index'

export function downloadTemplate(importType: string): Promise<Blob> {
  return request.get('/imports/template', {
    params: { import_type: importType },
    responseType: 'blob',
  })
}

export function uploadImport(importType: string, file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/imports/upload?import_type=${importType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
