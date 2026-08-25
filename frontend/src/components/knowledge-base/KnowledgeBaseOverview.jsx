import { useEffect, useState } from 'react'
import { FileText, Clock, Zap, CheckCircle2 } from 'lucide-react'
import { getSettings } from '../../api/settings'
import { useLocalKnowledgeProfile } from '../../hooks/useLocalKnowledgeProfile'
import { SkeletonCard } from '../common/Skeleton'

function StatCard({ label, value, sub, Icon, iconBg, iconColor }) {
	return (
		<div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col gap-3">
			<div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg}`}>
				<Icon size={20} className={iconColor} />
			</div>
			<div>
				<p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
					{label}
				</p>
				<p className="text-3xl font-semibold text-slate-800 mt-2 leading-none">
					{value ?? '—'}
				</p>
				{sub && <p className="text-xs text-slate-400 mt-2">{sub}</p>}
			</div>
		</div>
	)
}

export default function KnowledgeBaseOverview() {
	const [settings, setSettings] = useState(null)
	const [loading, setLoading] = useState(true)
	const { profile } = useLocalKnowledgeProfile()

	useEffect(() => {
		getSettings()
			.then(setSettings)
			.catch(() => setSettings(null))
			.finally(() => setLoading(false))
	}, [])

	const hasKB = settings?.knowledge_base_text?.trim().length > 0
	const wordCount = hasKB
		? settings.knowledge_base_text.trim().split(/\s+/).length
		: 0

	const lastUpdated = settings?.kb_updated_at
		? new Date(settings.kb_updated_at).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
		  })
		: 'Not yet'

	// A simple, human-friendly readiness score across the four Knowledge Base
	// areas — deliberately independent of implementation details like
	// embeddings/indexing, since business owners only need to know whether
	// AISHA has what she needs.
	const sections = [
		{ id: 'profile', complete: Boolean(settings?.business_type) },
		{ id: 'documents', complete: (settings?.kb_document_count ?? 0) > 0 },
		{ id: 'faqs', complete: profile.faqs.length > 0 },
		{
			id: 'aiInstructions',
			complete: Object.values(profile.aiInstructions).some(value => value?.trim()),
		},
	]
	const completedCount = sections.filter(section => section.complete).length
	const totalSections = sections.length
	const isFullyReady = completedCount === totalSections

	if (loading) {
		return (
			<div className="space-y-6">
				<div>
					<h2 className="text-xl font-semibold text-slate-800">Knowledge Base Overview</h2>
					<p className="text-sm text-slate-500 mt-1">Monitor the state of your business knowledge and content.</p>
				</div>
				<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
					<SkeletonCard />
					<SkeletonCard />
					<SkeletonCard />
				</div>
				<SkeletonCard lines={2} />
			</div>
		)
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div>
				<h2 className="text-xl font-semibold text-slate-800">
					Knowledge Base Overview
				</h2>
				<p className="text-sm text-slate-500 mt-1">
					Monitor the state of your business knowledge and content.
				</p>
			</div>

			{/* Stats Grid */}
			<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
				<StatCard
					label="Total Documents"
					value={settings?.kb_document_count ?? 0}
					sub="uploaded documents"
					Icon={FileText}
					iconBg="bg-blue-100"
					iconColor="text-blue-600"
				/>

				<StatCard
					label="Total Words"
					value={wordCount > 0 ? wordCount.toLocaleString() : 0}
					sub="in your knowledge base"
					Icon={Zap}
					iconBg="bg-amber-100"
					iconColor="text-amber-600"
				/>

				<StatCard
					label="Last Updated"
					value={lastUpdated}
					sub={hasKB ? 'most recent change' : 'no documents yet'}
					Icon={Clock}
					iconBg="bg-slate-100"
					iconColor="text-slate-600"
				/>
			</div>

			{/* Readiness Card */}
			<div className="bg-white border border-slate-200 rounded-2xl p-6">
				<div className="flex items-center gap-3">
					<span
						className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
							isFullyReady ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'
						}`}
					>
						<CheckCircle2 size={20} />
					</span>
					<div>
						<h3 className="text-sm font-semibold text-slate-800">
							{isFullyReady ? 'Ready to answer customers' : 'Getting ready to answer customers'}
						</h3>
						<p className="text-xs text-slate-500 mt-0.5">
							{completedCount} of {totalSections} sections completed
						</p>
					</div>
				</div>

				<div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
					<div
						className={`h-full rounded-full transition-all ${isFullyReady ? 'bg-emerald-500' : 'bg-amber-500'}`}
						style={{ width: `${(completedCount / totalSections) * 100}%` }}
					/>
				</div>

				<p className="text-xs text-slate-500 mt-4 border-t border-slate-200 pt-3">
					{isFullyReady
						? 'Your Knowledge Base is active and AISHA can use it to answer customer questions.'
						: 'Add business information, documents, or FAQs to help AISHA answer more customer questions.'}
				</p>
			</div>
		</div>
	)
}
