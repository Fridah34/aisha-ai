import { useState } from 'react'
import CardShell from './CardShell'
import { useToast } from '../../../context/ToastContext'

const fieldClassName =
	'mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400'

/**
 * Generic card for a flat set of text/textarea fields, backed by the local
 * knowledge profile (Business Operations, AI Instructions).
 */
export default function FieldSetCard({
	title,
	description,
	emptyMessage,
	fields,
	values,
	savedAt,
	onSave,
	onDirtyChange,
	savedToastMessage,
}) {
	const [isEditing, setIsEditing] = useState(false)
	const [draft, setDraft] = useState(values)
	const [saveStatus, setSaveStatus] = useState('idle')
	const { showToast } = useToast()

	const hasAnyValue = fields.some(field => values[field.key]?.trim())

	function startEditing() {
		setDraft(values)
		setIsEditing(true)
		onDirtyChange?.(false)
	}

	function handleFieldChange(key, value) {
		setDraft(current => ({ ...current, [key]: value }))
		onDirtyChange?.(true)
	}

	function handleCancel() {
		setIsEditing(false)
		onDirtyChange?.(false)
	}

	async function handleSave() {
		setSaveStatus('saving')
		try {
			onSave(draft)
			setSaveStatus('saved')
			showToast(savedToastMessage || '✓ Changes saved', { variant: 'success' })
			setIsEditing(false)
			onDirtyChange?.(false)
			setTimeout(() => setSaveStatus('idle'), 2000)
		} catch (error) {
			setSaveStatus('idle')
			showToast(error instanceof Error ? error.message : 'Could not save changes.', { variant: 'error' })
		}
	}

	return (
		<CardShell
			title={title}
			description={description}
			isEditing={isEditing}
			onEdit={startEditing}
			onCancel={handleCancel}
			onSave={handleSave}
			saveStatus={saveStatus}
			savedAt={savedAt}
		>
			{!isEditing ? (
				hasAnyValue ? (
					<div className="space-y-4">
						{fields.map(field =>
							values[field.key]?.trim() ? (
								<div key={field.key}>
									<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{field.label}</p>
									<p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{values[field.key]}</p>
								</div>
							) : null
						)}
					</div>
				) : (
					<p className="text-sm text-slate-400">{emptyMessage}</p>
				)
			) : (
				<div className="space-y-4">
					{fields.map(field => (
						<div key={field.key}>
							<label htmlFor={`field-${field.key}`} className="block text-sm font-medium text-slate-700">
								{field.label}
							</label>
							{field.type === 'textarea' ? (
								<textarea
									id={`field-${field.key}`}
									rows={3}
									value={draft[field.key] || ''}
									onChange={event => handleFieldChange(field.key, event.target.value)}
									placeholder={field.placeholder}
									className={fieldClassName}
								/>
							) : (
								<input
									id={`field-${field.key}`}
									type="text"
									value={draft[field.key] || ''}
									onChange={event => handleFieldChange(field.key, event.target.value)}
									placeholder={field.placeholder}
									className={fieldClassName}
								/>
							)}
						</div>
					))}
				</div>
			)}
		</CardShell>
	)
}
