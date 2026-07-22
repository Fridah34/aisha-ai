import { FileText, Loader2, AlertTriangle } from 'lucide-react'
import DocumentActionsMenu from './DocumentActionsMenu'
import {
	formatFileSize,
	formatUploadedLabel,
	getFileTypeMeta,
	getStatusMeta,
} from './documentUtils'

export default function DocumentListItem({ document, onView, onEdit, onReplace, onDelete, onRetry }) {
	const typeMeta = getFileTypeMeta(document.file_type)
	const statusMeta = getStatusMeta(document.status)
	const isUploading = document.status === 'uploading'
	const isLearning = document.status === 'learning'

	return (
		<li className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
			<div className="flex min-w-0 items-start gap-3">
				<span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${typeMeta.className}`}>
					<FileText size={19} />
				</span>

				<div className="min-w-0">
					<p className="truncate text-sm font-semibold text-slate-800">{document.display_name}</p>
					<p className="mt-0.5 text-xs text-slate-500">
						{typeMeta.label} • {formatFileSize(document.file_size)} • {formatUploadedLabel(document.created_at)}
					</p>
					{document.category && (
						<p className="mt-1 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
							{document.category}
						</p>
					)}
				</div>
			</div>

			<div className="flex shrink-0 items-center justify-between gap-3 sm:justify-end">
				<span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusMeta.badgeClassName}`}>
					{isUploading || isLearning ? (
						<Loader2 size={12} className="animate-spin" />
					) : (
						<span className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClassName}`} />
					)}
					{statusMeta.label}
				</span>

				{document.status === 'failed' && (
					<button
						type="button"
						onClick={onRetry}
						className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-300"
					>
						<AlertTriangle size={12} />
						Retry
					</button>
				)}

				{!isUploading && (
					<DocumentActionsMenu onView={onView} onEdit={onEdit} onReplace={onReplace} onDelete={onDelete} />
				)}
			</div>
		</li>
	)
}
