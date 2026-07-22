import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../../api/settings'
import { useLocalKnowledgeProfile } from '../../hooks/useLocalKnowledgeProfile'
import { SkeletonCard } from '../common/Skeleton'
import BusinessProfileCard from './business/BusinessProfileCard'
import FieldSetCard from './business/FieldSetCard'
import CustomKnowledgeSourcesCard from './business/CustomKnowledgeSourcesCard'

const OPERATIONS_FIELDS = [
	{ key: 'address', label: 'Address', placeholder: 'Where customers can find you' },
	{ key: 'contact', label: 'Contact Information', placeholder: 'Phone, email, or WhatsApp' },
	{ key: 'hours', label: 'Operating Hours', placeholder: 'e.g. Mon–Sat, 8am–6pm' },
	{ key: 'deliveryAreas', label: 'Delivery Areas', placeholder: 'Areas you deliver to' },
	{ key: 'paymentMethods', label: 'Payment Methods', placeholder: 'e.g. M-Pesa, cash, card' },
]

const AI_INSTRUCTION_FIELDS = [
	{ key: 'personality', label: 'Personality', placeholder: 'How AISHA should come across' },
	{ key: 'greetingStyle', label: 'Greeting Style', placeholder: 'How AISHA should greet customers' },
	{ key: 'tone', label: 'Tone', placeholder: 'e.g. warm and professional' },
	{
		key: 'escalationRules',
		label: 'Escalation Rules',
		placeholder: 'When AISHA should hand over to a human',
		type: 'textarea',
	},
	{
		key: 'restrictedResponses',
		label: 'Restricted Responses',
		placeholder: "Topics AISHA shouldn't discuss",
		type: 'textarea',
	},
]

export default function BusinessInformation({ onDirtyChange }) {
	const [settings, setSettings] = useState(null)
	const [loading, setLoading] = useState(true)
	const { profile, updateSection, addKnowledgeSource, updateKnowledgeSourceStatus, deleteKnowledgeSource } =
		useLocalKnowledgeProfile()
	const [dirtyMap, setDirtyMap] = useState({})

	useEffect(() => {
		getSettings()
			.then(setSettings)
			.catch(() => setSettings(null))
			.finally(() => setLoading(false))
	}, [])

	useEffect(() => {
		onDirtyChange?.(Object.values(dirtyMap).some(Boolean))
	}, [dirtyMap, onDirtyChange])

	function setDirty(section) {
		return value => setDirtyMap(current => ({ ...current, [section]: value }))
	}

	async function handleSaveBusinessType(businessType) {
		const updated = await updateSettings({ business_type: businessType })
		setSettings(current => ({ ...current, ...updated }))
	}

	if (loading) {
		return (
			<div className="space-y-6">
				<div>
					<h2 className="text-xl font-semibold text-slate-800">Business Information</h2>
					<p className="mt-1 text-sm text-slate-500">
						Teach AISHA about your business so she can better assist your customers.
					</p>
				</div>
				<div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
					<SkeletonCard lines={4} />
					<SkeletonCard lines={4} />
					<SkeletonCard lines={4} />
					<SkeletonCard lines={4} />
				</div>
			</div>
		)
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div>
				<h2 className="text-xl font-semibold text-slate-800">Business Information</h2>
				<p className="mt-1 text-sm text-slate-500">
					Teach AISHA about your business so she can better assist your customers.
				</p>
			</div>

			<div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
				<BusinessProfileCard
					businessName={settings?.business_name}
					businessType={settings?.business_type}
					description={profile.businessProfile.description}
					savedAt={profile.updatedAt.businessProfile ? new Date(profile.updatedAt.businessProfile) : null}
					onSaveBusinessType={handleSaveBusinessType}
					onSaveDescription={description => updateSection('businessProfile', { description })}
					onDirtyChange={setDirty('profile')}
				/>

				<FieldSetCard
					title="Business Operations"
					description="Practical details customers ask about most."
					emptyMessage="No operations details added yet."
					fields={OPERATIONS_FIELDS}
					values={profile.operations}
					savedAt={profile.updatedAt.operations ? new Date(profile.updatedAt.operations) : null}
					onSave={values => updateSection('operations', values)}
					onDirtyChange={setDirty('operations')}
					savedToastMessage="✓ Business Operations saved"
				/>

				<FieldSetCard
					title="AI Instructions"
					description="Guides how AISHA talks to your customers."
					emptyMessage="No AI instructions added yet."
					fields={AI_INSTRUCTION_FIELDS}
					values={profile.aiInstructions}
					savedAt={profile.updatedAt.aiInstructions ? new Date(profile.updatedAt.aiInstructions) : null}
					onSave={values => updateSection('aiInstructions', values)}
					onDirtyChange={setDirty('aiInstructions')}
					savedToastMessage="✓ AI Instructions saved"
				/>

				<CustomKnowledgeSourcesCard
					sources={profile.knowledgeSources}
					onAdd={addKnowledgeSource}
					onUpdateStatus={updateKnowledgeSourceStatus}
					onDelete={deleteKnowledgeSource}
				/>
			</div>
		</div>
	)
}
