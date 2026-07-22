import { useState } from 'react'
import KnowledgeBaseOverview from '../components/knowledge-base/KnowledgeBaseOverview'
import BusinessInformation from '../components/knowledge-base/BusinessInformation'
import Documents from '../components/knowledge-base/Documents'
import FAQs from '../components/knowledge-base/FAQs'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { useUnsavedChangesGuard } from '../hooks/useUnsavedChangesGuard'

const TABS = [
	{ id: 'overview', label: 'Overview' },
	{ id: 'business', label: 'Business Information' },
	{ id: 'documents', label: 'Documents' },
	{ id: 'faqs', label: 'FAQs' },
]

export default function KnowledgeBase() {
	const [activeTab, setActiveTab] = useState('overview')
	const [isBusinessInfoDirty, setIsBusinessInfoDirty] = useState(false)
	const { isPromptOpen, requestNavigation, confirmLeave, cancelLeave } = useUnsavedChangesGuard(isBusinessInfoDirty)

	function renderTabContent() {
		switch (activeTab) {
			case 'overview':
				return <KnowledgeBaseOverview />
			case 'business':
				return <BusinessInformation onDirtyChange={setIsBusinessInfoDirty} />
			case 'documents':
				return <Documents />
			case 'faqs':
				return <FAQs />
			default:
				return <KnowledgeBaseOverview />
		}
	}

	return (
		<section className="max-w-6xl p-5 sm:p-8" aria-labelledby="knowledge-base-title">
			{/* Header */}
			<header className="mb-8">
				<h1 id="knowledge-base-title" className="text-2xl font-semibold text-slate-800">
					Knowledge Base
				</h1>
				<p className="mt-1 text-sm text-slate-500">
					Manage your business knowledge and help AISHA serve your customers better.
				</p>
			</header>

			{/* Tab Navigation */}
			<div className="border-b border-slate-200 mb-8 overflow-x-auto">
				<nav className="flex gap-8 -mb-px" role="tablist">
					{TABS.map(tab => (
						<button
							key={tab.id}
							id={`tab-${tab.id}`}
							role="tab"
							aria-selected={activeTab === tab.id}
							aria-controls={`panel-${tab.id}`}
							onClick={() => requestNavigation(() => setActiveTab(tab.id))}
							className={`whitespace-nowrap py-3 px-1 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-white
								${activeTab === tab.id
									? 'border-amber-500 text-amber-600'
									: 'border-transparent text-slate-600 hover:text-slate-800'
								}`}
						>
							{tab.label}
						</button>
					))}
				</nav>
			</div>

			{/* Tab Content */}
			<div id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`}>
				{renderTabContent()}
			</div>

			<ConfirmDialog
				open={isPromptOpen}
				title="You have unsaved changes."
				description="If you leave now, your changes will be lost."
				confirmLabel="Leave"
				cancelLabel="Stay"
				tone="danger"
				onConfirm={confirmLeave}
				onCancel={cancelLeave}
			/>
		</section>
	)
}

