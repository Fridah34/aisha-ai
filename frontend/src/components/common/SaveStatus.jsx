import { Loader2, CheckCircle2 } from 'lucide-react'

function formatRelativeTime(date) {
	if (!date) return ''
	const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000))

	if (seconds < 10) return 'just now'
	if (seconds < 60) return `${seconds} seconds ago`

	const minutes = Math.round(seconds / 60)
	if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`

	const hours = Math.round(minutes / 60)
	if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`

	const days = Math.round(hours / 24)
	return `${days} day${days === 1 ? '' : 's'} ago`
}

/**
 * Subtle inline save-status text: "Saving...", "Saved", or
 * "Last updated 2 minutes ago". Renders nothing when there's nothing to show.
 */
export default function SaveStatus({ status, savedAt }) {
	if (status === 'saving') {
		return (
			<span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600">
				<Loader2 size={13} className="animate-spin" />
				Saving...
			</span>
		)
	}

	if (status === 'saved') {
		return (
			<span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600">
				<CheckCircle2 size={13} />
				Saved
			</span>
		)
	}

	if (savedAt) {
		return <span className="text-xs text-slate-400">Last updated {formatRelativeTime(savedAt)}</span>
	}

	return null
}
