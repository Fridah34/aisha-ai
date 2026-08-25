import { X } from 'lucide-react'

export default function ModalShell({ title, onClose, children, maxWidthClassName = 'max-w-lg' }) {
	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
			role="dialog"
			aria-modal="true"
			aria-label={title}
			onMouseDown={event => {
				if (event.target === event.currentTarget) onClose()
			}}
		>
			<div className={`w-full ${maxWidthClassName} rounded-2xl bg-white shadow-xl`}>
				<div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
					<h3 className="text-base font-semibold text-slate-800">{title}</h3>
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-400"
						aria-label="Close"
					>
						<X size={18} />
					</button>
				</div>
				<div className="max-h-[75vh] overflow-y-auto px-5 py-5">{children}</div>
			</div>
		</div>
	)
}
