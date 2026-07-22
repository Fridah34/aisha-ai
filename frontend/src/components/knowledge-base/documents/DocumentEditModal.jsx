import { useState } from 'react'
import ModalShell from './ModalShell'
import { updateDocument } from '../../../services/knowledgeBaseService'

export default function DocumentEditModal({ document, onClose, onSaved }) {
	const [displayName, setDisplayName] = useState(document.display_name)
	const [category, setCategory] = useState(document.category || '')
	const [description, setDescription] = useState(document.description || '')
	const [tagsText, setTagsText] = useState((document.tags || []).join(', '))
	const [isSaving, setIsSaving] = useState(false)
	const [error, setError] = useState('')

	async function handleSubmit(event) {
		event.preventDefault()

		if (!displayName.trim()) {
			setError('Display name cannot be empty.')
			return
		}

		setIsSaving(true)
		setError('')

		try {
			const tags = tagsText
				.split(',')
				.map(tag => tag.trim())
				.filter(Boolean)

			const updated = await updateDocument(document.id, {
				display_name: displayName.trim(),
				category: category.trim() || null,
				description: description.trim() || null,
				tags,
			})
			onSaved(updated)
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Could not save changes. Please try again.')
		} finally {
			setIsSaving(false)
		}
	}

	return (
		<ModalShell title="Edit Document" onClose={onClose}>
			<form className="space-y-4" onSubmit={handleSubmit}>
				<p className="text-xs text-slate-500">
					Editing these details won't ask AISHA to relearn the document — only replacing the file does that.
				</p>

				<div>
					<label htmlFor="document-display-name" className="block text-sm font-medium text-slate-700">
						Display Name
					</label>
					<input
						id="document-display-name"
						type="text"
						value={displayName}
						onChange={event => setDisplayName(event.target.value)}
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>

				<div>
					<label htmlFor="document-category" className="block text-sm font-medium text-slate-700">
						Category
					</label>
					<input
						id="document-category"
						type="text"
						value={category}
						onChange={event => setCategory(event.target.value)}
						placeholder="e.g. Price List, Policy, Menu"
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>

				<div>
					<label htmlFor="document-description" className="block text-sm font-medium text-slate-700">
						Description
					</label>
					<textarea
						id="document-description"
						rows={3}
						value={description}
						onChange={event => setDescription(event.target.value)}
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>

				<div>
					<label htmlFor="document-tags" className="block text-sm font-medium text-slate-700">
						Tags <span className="font-normal text-slate-400">(optional, comma-separated)</span>
					</label>
					<input
						id="document-tags"
						type="text"
						value={tagsText}
						onChange={event => setTagsText(event.target.value)}
						placeholder="e.g. seasonal, 2026, retail"
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
						disabled={isSaving}
						className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
					>
						{isSaving ? 'Saving...' : 'Save Changes'}
					</button>
				</div>
			</form>
		</ModalShell>
	)
}
