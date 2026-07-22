import { useState } from 'react'
import { Plus, FileText, Type, Trash2, Loader2 } from 'lucide-react'
import AddKnowledgeSourceModal from './AddKnowledgeSourceModal'
import ConfirmDialog from '../../common/ConfirmDialog'
import { useToast } from '../../../context/ToastContext'

const STATUS_META = {
	learning: { label: 'AISHA is learning...', className: 'bg-amber-100 text-amber-700' },
	ready: { label: 'Ready', className: 'bg-emerald-100 text-emerald-700' },
}

export default function CustomKnowledgeSourcesCard({ sources, onAdd, onUpdateStatus, onDelete }) {
	const [isModalOpen, setIsModalOpen] = useState(false)
	const [pendingDeleteId, setPendingDeleteId] = useState(null)
	const { showToast } = useToast()

	function handleAdd(sourceData) {
		const id = crypto.randomUUID()
		onAdd({ id, status: 'learning', ...sourceData })
		setIsModalOpen(false)
		showToast('✓ Source added. AISHA is learning from it...', { variant: 'success' })

		setTimeout(() => {
			onUpdateStatus(id, 'ready')
			showToast('🟢 Ready — AISHA can now use this information.', { variant: 'success' })
		}, 1800)
	}

	function handleConfirmDelete() {
		onDelete(pendingDeleteId)
		setPendingDeleteId(null)
		showToast('✓ Source deleted successfully.', { variant: 'success' })
	}

	return (
		<div className="bg-white border border-slate-200 rounded-2xl p-6">
			<div className="mb-4 flex items-start justify-between gap-3">
				<div>
					<h3 className="text-base font-semibold text-slate-800">Custom Knowledge Sources</h3>
					<p className="mt-1 text-sm text-slate-500">
						Extra brand voice, product, or policy notes AISHA should learn from.
					</p>
				</div>
				<button
					type="button"
					onClick={() => setIsModalOpen(true)}
					className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-400"
				>
					<Plus size={13} />
					Add Source
				</button>
			</div>

			{sources.length === 0 ? (
				<p className="text-sm text-slate-400">No custom knowledge sources yet.</p>
			) : (
				<ul className="space-y-2">
					{sources.map(source => {
						const statusMeta = STATUS_META[source.status] || STATUS_META.learning
						const TypeIcon = source.type === 'text' ? Type : FileText

						return (
							<li
								key={source.id}
								className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3"
							>
								<div className="flex min-w-0 items-center gap-3">
									<span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
										<TypeIcon size={16} />
									</span>
									<div className="min-w-0">
										<p className="truncate text-sm font-medium text-slate-800">{source.name}</p>
										<p className="text-xs text-slate-500">{source.category}</p>
									</div>
								</div>

								<div className="flex shrink-0 items-center gap-2">
									<span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusMeta.className}`}>
										{source.status === 'learning' && <Loader2 size={11} className="animate-spin" />}
										{statusMeta.label}
									</span>
									<button
										type="button"
										onClick={() => setPendingDeleteId(source.id)}
										aria-label={`Delete ${source.name}`}
										className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-300"
									>
										<Trash2 size={15} />
									</button>
								</div>
							</li>
						)
					})}
				</ul>
			)}

			{isModalOpen && <AddKnowledgeSourceModal onClose={() => setIsModalOpen(false)} onAdd={handleAdd} />}

			<ConfirmDialog
				open={pendingDeleteId !== null}
				title="Delete Knowledge Source?"
				description="AISHA will no longer use this information when answering customer questions."
				confirmLabel="Delete"
				tone="danger"
				onConfirm={handleConfirmDelete}
				onCancel={() => setPendingDeleteId(null)}
			/>
		</div>
	)
}
