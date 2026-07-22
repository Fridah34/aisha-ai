import { useMemo, useState } from 'react'
import { Plus, Search, ChevronDown, Pencil, Trash2, HelpCircle } from 'lucide-react'
import ModalShell from './documents/ModalShell'
import ConfirmDialog from '../common/ConfirmDialog'
import { useLocalKnowledgeProfile } from '../../hooks/useLocalKnowledgeProfile'
import { useToast } from '../../context/ToastContext'

function FaqFormModal({ initialFaq, onClose, onSubmit }) {
	const [question, setQuestion] = useState(initialFaq?.question || '')
	const [answer, setAnswer] = useState(initialFaq?.answer || '')
	const [error, setError] = useState('')

	function handleSubmit(event) {
		event.preventDefault()
		if (!question.trim() || !answer.trim()) {
			setError('Add both a question and an answer.')
			return
		}
		onSubmit({ question: question.trim(), answer: answer.trim() })
	}

	return (
		<ModalShell title={initialFaq ? 'Edit FAQ' : 'Add FAQ'} onClose={onClose}>
			<form className="space-y-4" onSubmit={handleSubmit}>
				<div>
					<label htmlFor="faq-question" className="block text-sm font-medium text-slate-700">
						Question
					</label>
					<input
						id="faq-question"
						type="text"
						value={question}
						onChange={event => setQuestion(event.target.value)}
						placeholder="e.g. Do you deliver outside Nairobi?"
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>
				<div>
					<label htmlFor="faq-answer" className="block text-sm font-medium text-slate-700">
						Answer
					</label>
					<textarea
						id="faq-answer"
						rows={4}
						value={answer}
						onChange={event => setAnswer(event.target.value)}
						placeholder="How should AISHA answer this question?"
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>

				{error && <p className="text-sm text-red-600">{error}</p>}

				<div className="flex justify-end gap-2 pt-2">
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</button>
					<button
						type="submit"
						className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600"
					>
						{initialFaq ? 'Save Changes' : 'Add FAQ'}
					</button>
				</div>
			</form>
		</ModalShell>
	)
}

export default function FAQs() {
	const { profile, addFaq, updateFaq, deleteFaq } = useLocalKnowledgeProfile()
	const { showToast } = useToast()

	const [searchQuery, setSearchQuery] = useState('')
	const [openId, setOpenId] = useState(null)
	const [modalMode, setModalMode] = useState(null) // null | 'add' | faq object being edited
	const [pendingDeleteId, setPendingDeleteId] = useState(null)

	const filteredFaqs = useMemo(() => {
		const needle = searchQuery.trim().toLowerCase()
		if (!needle) return profile.faqs
		return profile.faqs.filter(
			faq => faq.question.toLowerCase().includes(needle) || faq.answer.toLowerCase().includes(needle)
		)
	}, [profile.faqs, searchQuery])

	function handleAdd(data) {
		addFaq(data)
		setModalMode(null)
		showToast('✓ FAQ added successfully', { variant: 'success' })
	}

	function handleEditSave(data) {
		updateFaq(modalMode.id, data)
		setModalMode(null)
		showToast('✓ FAQ updated successfully', { variant: 'success' })
	}

	function handleConfirmDelete() {
		deleteFaq(pendingDeleteId)
		setPendingDeleteId(null)
		showToast('✓ FAQ deleted successfully.', { variant: 'success' })
	}

	const isEditing = modalMode && modalMode !== 'add'

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-xl font-semibold text-slate-800">Frequently Asked Questions</h2>
					<p className="mt-1 text-sm text-slate-500">
						Manage common questions and answers that AISHA should know about.
					</p>
				</div>
				<button
					type="button"
					onClick={() => setModalMode('add')}
					className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
				>
					<Plus size={16} />
					Add FAQ
				</button>
			</div>

			{/* Search */}
			<div className="relative">
				<Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
				<input
					type="search"
					value={searchQuery}
					onChange={event => setSearchQuery(event.target.value)}
					placeholder="Search FAQs"
					className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
				/>
			</div>

			{/* Accordion list / empty state */}
			{profile.faqs.length === 0 ? (
				<div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
					<span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-600">
						<HelpCircle size={26} />
					</span>
					<h3 className="mt-4 text-base font-semibold text-slate-800">No FAQs created yet</h3>
					<p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
						Add the questions your customers ask most so AISHA can answer them instantly and consistently.
					</p>
					<button
						type="button"
						onClick={() => setModalMode('add')}
						className="mt-5 inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
					>
						<Plus size={16} />
						Add FAQ
					</button>
				</div>
			) : filteredFaqs.length === 0 ? (
				<div className="rounded-2xl border border-slate-200 bg-slate-50 p-8 text-center">
					<p className="text-sm text-slate-500">No FAQs match your search.</p>
				</div>
			) : (
				<ul className="space-y-2">
					{filteredFaqs.map(faq => {
						const isOpen = openId === faq.id
						return (
							<li key={faq.id} className="rounded-2xl border border-slate-200 bg-white">
								<div className="flex items-center gap-2 px-4 py-3">
									<button
										type="button"
										onClick={() => setOpenId(isOpen ? null : faq.id)}
										aria-expanded={isOpen}
										className="flex flex-1 items-center justify-between gap-3 text-left focus:outline-none"
									>
										<span className="text-sm font-medium text-slate-800">{faq.question}</span>
										<ChevronDown
											size={16}
											className={`shrink-0 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
										/>
									</button>
									<button
										type="button"
										onClick={() => setModalMode(faq)}
										aria-label={`Edit ${faq.question}`}
										className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-400"
									>
										<Pencil size={15} />
									</button>
									<button
										type="button"
										onClick={() => setPendingDeleteId(faq.id)}
										aria-label={`Delete ${faq.question}`}
										className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-300"
									>
										<Trash2 size={15} />
									</button>
								</div>
								{isOpen && (
									<div className="border-t border-slate-100 px-4 py-3">
										<p className="whitespace-pre-wrap text-sm text-slate-600">{faq.answer}</p>
									</div>
								)}
							</li>
						)
					})}
				</ul>
			)}

			{modalMode === 'add' && <FaqFormModal onClose={() => setModalMode(null)} onSubmit={handleAdd} />}
			{isEditing && (
				<FaqFormModal initialFaq={modalMode} onClose={() => setModalMode(null)} onSubmit={handleEditSave} />
			)}

			<ConfirmDialog
				open={pendingDeleteId !== null}
				title="Delete FAQ?"
				description="AISHA will no longer use this information when answering customer questions."
				confirmLabel="Delete"
				tone="danger"
				onConfirm={handleConfirmDelete}
				onCancel={() => setPendingDeleteId(null)}
			/>
		</div>
	)
}

