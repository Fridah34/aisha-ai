import { useState } from 'react'
import ModalShell from '../documents/ModalShell'

const CATEGORIES = ['Brand Voice', 'Products', 'Services', 'Policies', 'Marketing', 'Promotions', 'Internal Use', 'Other']

export default function AddKnowledgeSourceModal({ onClose, onAdd }) {
	const [name, setName] = useState('')
	const [category, setCategory] = useState(CATEGORIES[0])
	const [knowledgeType, setKnowledgeType] = useState('file') // 'file' | 'text'
	const [text, setText] = useState('')
	const [fileName, setFileName] = useState('')
	const [error, setError] = useState('')

	function handleSubmit(event) {
		event.preventDefault()

		if (!name.trim()) {
			setError('Give this source a name.')
			return
		}
		if (knowledgeType === 'text' && !text.trim()) {
			setError('Add some text for AISHA to learn from.')
			return
		}
		if (knowledgeType === 'file' && !fileName) {
			setError('Choose a file to upload.')
			return
		}

		onAdd({
			name: name.trim(),
			category,
			type: knowledgeType,
			text: knowledgeType === 'text' ? text.trim() : '',
			fileName: knowledgeType === 'file' ? fileName : '',
		})
	}

	return (
		<ModalShell title="Add Knowledge Source" onClose={onClose}>
			<form className="space-y-4" onSubmit={handleSubmit}>
				<div>
					<label htmlFor="source-name" className="block text-sm font-medium text-slate-700">
						Source Name
					</label>
					<input
						id="source-name"
						type="text"
						value={name}
						onChange={event => setName(event.target.value)}
						placeholder="e.g. Loyalty Program Rules"
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
					/>
				</div>

				<div>
					<label htmlFor="source-category" className="block text-sm font-medium text-slate-700">
						Category
					</label>
					<select
						id="source-category"
						value={category}
						onChange={event => setCategory(event.target.value)}
						className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
					>
						{CATEGORIES.map(option => (
							<option key={option} value={option}>
								{option}
							</option>
						))}
					</select>
				</div>

				<fieldset>
					<legend className="block text-sm font-medium text-slate-700">Knowledge Type</legend>
					<div className="mt-2 flex gap-4">
						<label className="flex items-center gap-2 text-sm text-slate-700">
							<input
								type="radio"
								name="knowledge-type"
								checked={knowledgeType === 'file'}
								onChange={() => setKnowledgeType('file')}
								className="h-4 w-4 text-amber-500 focus:ring-amber-400"
							/>
							Upload File
						</label>
						<label className="flex items-center gap-2 text-sm text-slate-700">
							<input
								type="radio"
								name="knowledge-type"
								checked={knowledgeType === 'text'}
								onChange={() => setKnowledgeType('text')}
								className="h-4 w-4 text-amber-500 focus:ring-amber-400"
							/>
							Add Text
						</label>
					</div>
				</fieldset>

				{knowledgeType === 'file' ? (
					<div>
						<label htmlFor="source-file" className="block text-sm font-medium text-slate-700">
							File
						</label>
						<input
							id="source-file"
							type="file"
							onChange={event => setFileName(event.target.files?.[0]?.name || '')}
							className="mt-1 w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-amber-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-amber-700 hover:file:bg-amber-200"
						/>
					</div>
				) : (
					<div>
						<label htmlFor="source-text" className="block text-sm font-medium text-slate-700">
							Text
						</label>
						<textarea
							id="source-text"
							rows={6}
							value={text}
							onChange={event => setText(event.target.value)}
							placeholder="Paste or write the information AISHA should learn."
							className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
						/>
					</div>
				)}

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
						Add Source
					</button>
				</div>
			</form>
		</ModalShell>
	)
}
