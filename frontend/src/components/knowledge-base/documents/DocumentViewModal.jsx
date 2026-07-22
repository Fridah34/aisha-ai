import { Download } from 'lucide-react'
import ModalShell from './ModalShell'
import { formatFileSize, formatUploadedLabel, getFileTypeMeta, getStatusMeta } from './documentUtils'
import { getDocumentFileUrl } from '../../../services/knowledgeBaseService'

const PREVIEWABLE_TYPES = new Set(['PDF', 'TXT', 'MD'])

export default function DocumentViewModal({ document, onClose }) {
	const typeMeta = getFileTypeMeta(document.file_type)
	const statusMeta = getStatusMeta(document.status)
	const fileUrl = getDocumentFileUrl(document.id)
	const canPreview = PREVIEWABLE_TYPES.has(document.file_type?.toUpperCase())

	return (
		<ModalShell title="Document Details" onClose={onClose} maxWidthClassName="max-w-2xl">
			<div className="space-y-4">
				<div className="flex items-start justify-between gap-4">
					<div>
						<p className="text-sm font-semibold text-slate-800">{document.display_name}</p>
						<p className="mt-1 text-xs text-slate-500">
							{typeMeta.label} • {formatFileSize(document.file_size)} • {formatUploadedLabel(document.created_at)}
						</p>
					</div>
					<span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusMeta.badgeClassName}`}>
						<span className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClassName}`} />
						{statusMeta.label}
					</span>
				</div>

				{document.status === 'failed' && document.error_message && (
					<p className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
						{document.error_message}
					</p>
				)}

				{document.category && (
					<div>
						<p className="text-xs font-medium uppercase tracking-wide text-slate-400">Category</p>
						<p className="mt-0.5 text-sm text-slate-700">{document.category}</p>
					</div>
				)}

				{document.description && (
					<div>
						<p className="text-xs font-medium uppercase tracking-wide text-slate-400">Description</p>
						<p className="mt-0.5 whitespace-pre-wrap text-sm text-slate-700">{document.description}</p>
					</div>
				)}

				{document.tags?.length > 0 && (
					<div className="flex flex-wrap gap-1.5">
						{document.tags.map(tag => (
							<span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
								{tag}
							</span>
						))}
					</div>
				)}

				<div className="pt-2">
					{canPreview ? (
						<iframe
							title={document.display_name}
							src={fileUrl}
							className="h-80 w-full rounded-xl border border-slate-200"
						/>
					) : (
						<a
							href={fileUrl}
							download
							className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-amber-400"
						>
							<Download size={16} />
							Download {typeMeta.label}
						</a>
					)}
				</div>
			</div>
		</ModalShell>
	)
}
