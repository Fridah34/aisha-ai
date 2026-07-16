import { AlertTriangle, CheckCircle2, Loader2, RotateCcw } from 'lucide-react'

const STATUS_CONFIG = {
	success: {
		icon: CheckCircle2,
		iconClassName: 'bg-emerald-100 text-emerald-600',
		containerClassName: 'border-emerald-200 bg-emerald-50',
		title: 'Upload complete',
		titleClassName: 'text-emerald-800',
		messageClassName: 'text-emerald-700',
		buttonClassName: 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-100',
		buttonLabel: 'Upload another',
	},
	failed: {
		icon: AlertTriangle,
		iconClassName: 'bg-red-100 text-red-600',
		containerClassName: 'border-red-200 bg-red-50',
		title: 'Upload failed',
		titleClassName: 'text-red-800',
		messageClassName: 'text-red-700',
		buttonClassName: 'border-red-200 bg-white text-red-700 hover:bg-red-100',
		buttonLabel: 'Try again',
	},
}

export default function UploadStatus({ status, fileName, message, onReset }) {
	let content = null

	if (status === 'uploading') {
		content = (
			<div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
				<span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
					<Loader2 size={21} className="animate-spin" />
				</span>
				<span className="min-w-0">
					<span className="block text-sm font-semibold text-amber-900">Uploading file...</span>
					<span className="mt-0.5 block truncate text-sm text-amber-700">{fileName}</span>
				</span>
			</div>
		)
	} else if (status !== 'idle') {
		const config = STATUS_CONFIG[status]
		const Icon = config.icon

		content = (
			<div className={`rounded-xl border p-4 ${config.containerClassName}`}>
			<div className="flex items-start gap-3">
				<span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${config.iconClassName}`}>
					<Icon size={21} />
				</span>
				<div className="min-w-0 flex-1">
					<p className={`text-sm font-semibold ${config.titleClassName}`}>{config.title}</p>
					<p className={`mt-1 break-words text-sm ${config.messageClassName}`}>{message}</p>
					<button
						type="button"
						onClick={onReset}
						className={`mt-3 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 ${config.buttonClassName}`}
					>
						<RotateCcw size={15} />
						{config.buttonLabel}
					</button>
				</div>
			</div>
		</div>
		)
	}

	return (
		<div className="mt-5" role="status" aria-live="polite" aria-atomic="true">
			{content}
		</div>
	)
}
