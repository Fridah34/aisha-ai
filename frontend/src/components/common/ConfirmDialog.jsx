/**
 * Generic confirmation dialog used for destructive actions (delete) and the
 * unsaved-changes prompt. Renders nothing when `open` is false.
 */
export default function ConfirmDialog({
	open,
	title,
	description,
	confirmLabel = 'Confirm',
	cancelLabel = 'Cancel',
	tone = 'default', // 'default' | 'danger'
	onConfirm,
	onCancel,
}) {
	if (!open) return null

	const confirmClassName =
		tone === 'danger'
			? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-400'
			: 'bg-amber-500 text-white hover:bg-amber-600 focus:ring-amber-400'

	return (
		<div
			className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/40 p-4"
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="confirm-dialog-title"
			aria-describedby="confirm-dialog-description"
			onMouseDown={event => {
				if (event.target === event.currentTarget) onCancel()
			}}
		>
			<div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl">
				<h3 id="confirm-dialog-title" className="text-base font-semibold text-slate-800">
					{title}
				</h3>
				<p id="confirm-dialog-description" className="mt-2 text-sm text-slate-600">
					{description}
				</p>
				<div className="mt-5 flex justify-end gap-2">
					<button
						type="button"
						autoFocus
						onClick={onCancel}
						className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-amber-400"
					>
						{cancelLabel}
					</button>
					<button
						type="button"
						onClick={onConfirm}
						className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 ${confirmClassName}`}
					>
						{confirmLabel}
					</button>
				</div>
			</div>
		</div>
	)
}
