import { useState } from 'react'
import CardShell from './CardShell'
import { useToast } from '../../../context/ToastContext'

const CATEGORY_OPTIONS = [
	{ value: 'retail', label: 'Retail' },
	{ value: 'services', label: 'Services' },
	{ value: 'general', label: 'General' },
]

function fieldClassName() {
	return 'mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400'
}

export default function BusinessProfileCard({
	businessName,
	businessType,
	description,
	deliveryLocation,               // NEW
	savedAt,
	onSaveBusinessType,
	onSaveDescription,
	onSaveDeliveryLocation,         // NEW
	onDirtyChange,
}) {
	const [isEditing, setIsEditing] = useState(false)
	const [draftType, setDraftType] = useState(businessType || 'general')
	const [draftDescription, setDraftDescription] = useState(description || '')
	const [draftDeliveryLocation, setDraftDeliveryLocation] = useState(deliveryLocation || '')  // NEW
	const [saveStatus, setSaveStatus] = useState('idle')
	const { showToast } = useToast()

	function startEditing() {
		setDraftType(businessType || 'general')
		setDraftDescription(description || '')
		setDraftDeliveryLocation(deliveryLocation || '')  // NEW
		setIsEditing(true)
		onDirtyChange?.(false)
	}

	function handleChange(setter) {
		return event => {
			setter(event.target.value)
			onDirtyChange?.(true)
		}
	}

	function handleCancel() {
		setIsEditing(false)
		onDirtyChange?.(false)
	}

	async function handleSave() {
		setSaveStatus('saving')
		try {
			await onSaveBusinessType(draftType)
			onSaveDescription(draftDescription)
			await onSaveDeliveryLocation(draftDeliveryLocation)  // NEW
			setSaveStatus('saved')
			showToast('✓ Business Profile saved', { variant: 'success' })
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
			title="Business Profile"
			description="The basics AISHA uses to introduce and describe your business."
			isEditing={isEditing}
			onEdit={startEditing}
			onCancel={handleCancel}
			onSave={handleSave}
			saveStatus={saveStatus}
			savedAt={savedAt}
		>
			{!isEditing ? (
				<div className="space-y-4">
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Business Name</p>
						<p className="mt-1 text-sm font-medium text-slate-800">{businessName || '—'}</p>
					</div>
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Business Category</p>
						<p className="mt-1 text-sm font-medium capitalize text-slate-800">{businessType || '—'}</p>
					</div>
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Business Description</p>
						{description ? (
							<p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{description}</p>
						) : (
							<p className="mt-1 text-sm text-slate-400">No description added yet.</p>
						)}
					</div>
					{/* NEW block */}
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Order Pickup / Delivery Location</p>
						{deliveryLocation ? (
							<p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{deliveryLocation}</p>
						) : (
							<p className="mt-1 text-sm text-slate-400">No pickup location added yet.</p>
						)}
					</div>
				</div>
			) : (
				<div className="space-y-4">
					<div>
						<label htmlFor="business-name" className="block text-sm font-medium text-slate-700">
							Business Name
						</label>
						<input
							id="business-name"
							type="text"
							value={businessName || ''}
							disabled
							className={`${fieldClassName()} bg-slate-50 text-slate-500`}
						/>
						<p className="mt-1 text-xs text-slate-400">Contact support to change your business name.</p>
					</div>

					<div>
						<label htmlFor="business-category" className="block text-sm font-medium text-slate-700">
							Business Category
						</label>
						<select
							id="business-category"
							value={draftType}
							onChange={handleChange(setDraftType)}
							className={fieldClassName()}
						>
							{CATEGORY_OPTIONS.map(option => (
								<option key={option.value} value={option.value}>
									{option.label}
								</option>
							))}
						</select>
					</div>

					<div>
						<label htmlFor="business-description" className="block text-sm font-medium text-slate-700">
							Business Description
						</label>
						<textarea
							id="business-description"
							rows={4}
							value={draftDescription}
							onChange={handleChange(setDraftDescription)}
							placeholder="Tell AISHA what your business does and what makes it special."
							className={fieldClassName()}
						/>
					</div>

					{/* NEW field */}
					<div>
						<label htmlFor="delivery-location" className="block text-sm font-medium text-slate-700">
							Order Pickup / Delivery Location
						</label>
						<input
							id="delivery-location"
							type="text"
							value={draftDeliveryLocation}
							onChange={handleChange(setDraftDeliveryLocation)}
							placeholder="e.g. Our shop, Kimathi Street, Nairobi"
							className={fieldClassName()}
						/>
						<p className="mt-1 text-xs text-slate-400">
							Sent to customers automatically when their order status changes to Shipping.
						</p>
					</div>
				</div>
			)}
		</CardShell>
	)
}