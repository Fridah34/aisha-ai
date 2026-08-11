import { useEffect, useState } from 'react'
import { LayoutDashboard, MessageCircle, Mail } from 'lucide-react'
import { getSettings, updateSettings } from '../../api/settings'
import { useToast } from '../../context/ToastContext'
import { SkeletonCard } from '../common/Skeleton'
import CardShell from '../knowledge-base/business/CardShell'
import NotificationChannelCard from './NotificationChannelCard'

// Matches the backend's expected `handover_notifications` shape:
// { dashboard: { enabled, delay_minutes }, whatsapp: {...}, email: {...} }
// `delay_minutes: 0` means "Immediately"; a positive value means "After N Minutes".
const DEFAULT_HANDOVER_NOTIFICATIONS = {
	dashboard: { enabled: true, delay_minutes: 0 },
	whatsapp: { enabled: true, delay_minutes: 0 },
	email: { enabled: true, delay_minutes: 5 },
}

const CHANNELS = [
	{
		key: 'dashboard',
		label: 'Dashboard Notifications',
		description: 'Show an alert in the AISHA dashboard.',
		icon: LayoutDashboard,
	},
	{
		key: 'whatsapp',
		label: 'WhatsApp Notifications',
		description: 'Send a WhatsApp message to your business number.',
		icon: MessageCircle,
	},
	{
		key: 'email',
		label: 'Email Notifications',
		description: 'Send an email to your registered business email.',
		icon: Mail,
	},
]

// The GET /settings response may not include handover_notifications yet
// (backend support pending) — fall back to the documented defaults per
// channel so the UI never renders in an undefined state.
function mergeNotifications(source) {
	return {
		dashboard: { ...DEFAULT_HANDOVER_NOTIFICATIONS.dashboard, ...source?.dashboard },
		whatsapp: { ...DEFAULT_HANDOVER_NOTIFICATIONS.whatsapp, ...source?.whatsapp },
		email: { ...DEFAULT_HANDOVER_NOTIFICATIONS.email, ...source?.email },
	}
}

/**
 * Human Handover Notifications settings card. Follows the same
 * fetch-on-mount + edit/draft/Save Changes pattern as the other Settings
 * cards (see BusinessProfileCard) — no separate save button is introduced.
 */
export default function HandoverNotifications({ onDirtyChange }) {
	const [settings, setSettings] = useState(null)
	const [loading, setLoading] = useState(true)
	const [isEditing, setIsEditing] = useState(false)
	const [draft, setDraft] = useState(DEFAULT_HANDOVER_NOTIFICATIONS)
	const [saveStatus, setSaveStatus] = useState('idle')
	const { showToast } = useToast()

	useEffect(() => {
		getSettings()
			.then(setSettings)
			.catch(() => setSettings(null))
			.finally(() => setLoading(false))
	}, [])

	const notifications = mergeNotifications(settings?.handover_notifications)
	const activeNotifications = isEditing ? draft : notifications

	function startEditing() {
		setDraft(notifications)
		setIsEditing(true)
		onDirtyChange?.(false)
	}

	function handleCancel() {
		setIsEditing(false)
		onDirtyChange?.(false)
	}

	function handleChannelChange(channelKey) {
		return patch => {
			setDraft(current => ({
				...current,
				[channelKey]: { ...current[channelKey], ...patch },
			}))
			onDirtyChange?.(true)
		}
	}

	async function handleSave() {
		setSaveStatus('saving')
		try {
			const updated = await updateSettings({ handover_notifications: draft })
			setSettings(current => ({ ...current, ...updated, handover_notifications: draft }))
			setSaveStatus('saved')
			showToast('✓ Handover Notifications saved', { variant: 'success' })
			setIsEditing(false)
			onDirtyChange?.(false)
			setTimeout(() => setSaveStatus('idle'), 2000)
		} catch (error) {
			setSaveStatus('idle')
			showToast(error instanceof Error ? error.message : 'Could not save changes.', { variant: 'error' })
		}
	}

	if (loading) {
		return <SkeletonCard lines={5} />
	}

	return (
		<CardShell
			title="Human Handover Notifications"
			description="Choose how AISHA should notify you whenever a conversation requires human intervention."
			isEditing={isEditing}
			onEdit={startEditing}
			onCancel={handleCancel}
			onSave={handleSave}
			saveStatus={saveStatus}
		>
			<div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
				{CHANNELS.map(channel => (
					<NotificationChannelCard
						key={channel.key}
						idPrefix={`handover-${channel.key}`}
						icon={channel.icon}
						label={channel.label}
						description={channel.description}
						value={activeNotifications[channel.key]}
						isEditing={isEditing}
						onChange={handleChannelChange(channel.key)}
					/>
				))}
			</div>
		</CardShell>
	)
}
