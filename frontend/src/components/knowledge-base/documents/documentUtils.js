export const FILE_TYPE_META = {
	PDF: { label: 'PDF', className: 'bg-red-100 text-red-600' },
	DOCX: { label: 'DOCX', className: 'bg-blue-100 text-blue-600' },
	TXT: { label: 'TXT', className: 'bg-slate-200 text-slate-600' },
	MD: { label: 'MD', className: 'bg-slate-200 text-slate-600' },
}

export function getFileTypeMeta(fileType) {
	return FILE_TYPE_META[fileType?.toUpperCase()] || { label: fileType || 'FILE', className: 'bg-slate-200 text-slate-600' }
}

export function formatFileSize(bytes) {
	if (!Number.isFinite(bytes)) return ''
	if (bytes < 1024) return `${bytes} B`

	const kb = bytes / 1024
	if (kb < 1024) return `${kb.toFixed(kb < 10 ? 1 : 0)} KB`

	const mb = kb / 1024
	return `${mb.toFixed(mb < 10 ? 1 : 0)} MB`
}

export function formatUploadedLabel(isoDate) {
	if (!isoDate) return 'Uploaded recently'

	const date = new Date(isoDate)
	const now = new Date()

	const isSameDay = date.toDateString() === now.toDateString()
	if (isSameDay) return 'Uploaded Today'

	const yesterday = new Date(now)
	yesterday.setDate(now.getDate() - 1)
	if (date.toDateString() === yesterday.toDateString()) return 'Uploaded Yesterday'

	return `Uploaded ${date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}`
}

// "uploading" is a client-only transient state that exists before the
// server even receives the file; the backend only ever returns
// learning/ready/failed.
export const STATUS_META = {
	uploading: {
		label: 'Uploading...',
		dotClassName: 'bg-slate-400',
		badgeClassName: 'bg-slate-100 text-slate-600',
	},
	learning: {
		label: 'AISHA is learning...',
		dotClassName: 'bg-amber-500 animate-pulse',
		badgeClassName: 'bg-amber-100 text-amber-700',
	},
	ready: {
		label: 'Ready',
		dotClassName: 'bg-emerald-500',
		badgeClassName: 'bg-emerald-100 text-emerald-700',
	},
	failed: {
		label: 'Processing failed',
		dotClassName: 'bg-red-500',
		badgeClassName: 'bg-red-100 text-red-700',
	},
}

export function getStatusMeta(status) {
	return STATUS_META[status] || STATUS_META.learning
}

export const FILTERS = [
	{ id: 'all', label: 'All Documents' },
	{ id: 'PDF', label: 'PDF' },
	{ id: 'DOCX', label: 'DOCX' },
	{ id: 'TXT', label: 'TXT' },
	{ id: 'learning', label: 'Learning' },
	{ id: 'ready', label: 'Ready' },
	{ id: 'failed', label: 'Failed' },
]

export function matchesFilter(document, filter) {
	if (filter === 'all') return true
	if (['learning', 'ready', 'failed', 'uploading'].includes(filter)) {
		return document.status === filter
	}
	return document.file_type?.toUpperCase() === filter
}

export function matchesSearch(document, query) {
	if (!query.trim()) return true
	const needle = query.trim().toLowerCase()

	return (
		document.display_name?.toLowerCase().includes(needle) ||
		document.file_name?.toLowerCase().includes(needle) ||
		document.category?.toLowerCase().includes(needle) ||
		document.file_type?.toLowerCase().includes(needle)
	)
}
