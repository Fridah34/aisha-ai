import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const VARIANT_META = {
	success: {
		icon: CheckCircle2,
		className: 'border-emerald-200 bg-emerald-50 text-emerald-800',
		iconClassName: 'text-emerald-600',
	},
	error: {
		icon: AlertTriangle,
		className: 'border-red-200 bg-red-50 text-red-800',
		iconClassName: 'text-red-600',
	},
	info: {
		icon: Info,
		className: 'border-slate-200 bg-white text-slate-700',
		iconClassName: 'text-amber-600',
	},
}

/**
 * Lightweight, in-app toast system used instead of browser alerts.
 * Wrap the app once with <ToastProvider> and call useToast() anywhere below it.
 */
export function ToastProvider({ children }) {
	const [toasts, setToasts] = useState([])
	const timersRef = useRef(new Map())

	const dismissToast = useCallback(id => {
		setToasts(current => current.filter(toast => toast.id !== id))
		const timer = timersRef.current.get(id)
		if (timer) {
			clearTimeout(timer)
			timersRef.current.delete(id)
		}
	}, [])

	const showToast = useCallback(
		(message, { variant = 'info', duration = 3500 } = {}) => {
			const id = crypto.randomUUID()
			setToasts(current => [...current, { id, message, variant }])

			if (duration > 0) {
				const timer = setTimeout(() => dismissToast(id), duration)
				timersRef.current.set(id, timer)
			}

			return id
		},
		[dismissToast]
	)

	return (
		<ToastContext.Provider value={{ showToast, dismissToast }}>
			{children}
			<div
				className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4"
				aria-live="polite"
				aria-atomic="true"
			>
				{toasts.map(toast => {
					const meta = VARIANT_META[toast.variant] || VARIANT_META.info
					const Icon = meta.icon
					return (
						<div
							key={toast.id}
							role="status"
							className={`pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-xl border px-4 py-3 shadow-lg ${meta.className}`}
						>
							<Icon size={18} className={`mt-0.5 shrink-0 ${meta.iconClassName}`} />
							<p className="flex-1 text-sm font-medium">{toast.message}</p>
							<button
								type="button"
								onClick={() => dismissToast(toast.id)}
								className="shrink-0 rounded-md p-0.5 text-current/60 hover:bg-black/5 focus:outline-none focus:ring-2 focus:ring-amber-400"
								aria-label="Dismiss notification"
							>
								<X size={14} />
							</button>
						</div>
					)
				})}
			</div>
		</ToastContext.Provider>
	)
}

export function useToast() {
	const context = useContext(ToastContext)
	if (!context) {
		throw new Error('useToast must be used within a ToastProvider')
	}
	return context
}
