import { useState } from 'react'
import { CheckCircle2, AlertTriangle } from 'lucide-react'
import ModalShell from './ModalShell'
import UploadDropzone from '../UploadDropzone'
import { replaceDocument } from '../../../services/knowledgeBaseService'

export default function DocumentReplaceModal({ document, config, onClose, onReplaced }) {
	const [phase, setPhase] = useState('idle') // idle | uploading | learning | done
	const [progress, setProgress] = useState(0)
	const [error, setError] = useState('')
	const [result, setResult] = useState(null)

	async function handleFileSelected(file) {
		setError('')
		setPhase('uploading')
		setProgress(0)

		try {
			const updated = await replaceDocument(document.id, file, {
				onProgress: value => {
					setProgress(value)
					if (value >= 1) setPhase('learning')
				},
			})
			setResult(updated)
			setPhase('done')
			onReplaced(updated)
		} catch (err) {
			setError(err instanceof Error ? err.message : 'The document could not be replaced. Please try again.')
			setPhase('idle')
		}
	}

	function handleValidationError(message) {
		setError(message)
	}

	const isBusy = phase === 'uploading' || phase === 'learning'

	return (
		<ModalShell title="Replace Document" onClose={onClose}>
			<div className="space-y-4">
				<p className="text-sm text-slate-500">
					Upload a newer version of <span className="font-medium text-slate-700">{document.display_name}</span>.
					AISHA will relearn from the updated file.
				</p>

				{phase === 'idle' && (
					<UploadDropzone config={config} onFileSelected={handleFileSelected} onValidationError={handleValidationError} />
				)}

				{phase === 'uploading' && (
					<div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
						<p className="text-sm font-medium text-amber-800">Uploading...</p>
						<div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-amber-100">
							<div
								className="h-full rounded-full bg-amber-500 transition-all"
								style={{ width: `${Math.round(progress * 100)}%` }}
							/>
						</div>
					</div>
				)}

				{phase === 'learning' && (
					<div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
						<p className="text-sm font-medium text-amber-800">✓ Document replaced successfully</p>
						<p className="mt-1 text-sm text-amber-700">AISHA is learning from the updated document...</p>
					</div>
				)}

				{phase === 'done' && result?.status === 'ready' && (
					<div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
						<CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />
						<div>
							<p className="text-sm font-medium text-emerald-800">🟢 Ready</p>
							<p className="mt-1 text-sm text-emerald-700">
								AISHA has updated her knowledge using the latest version.
							</p>
						</div>
					</div>
				)}

				{phase === 'done' && result?.status === 'failed' && (
					<div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
						<AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-600" />
						<div>
							<p className="text-sm font-medium text-red-800">Processing failed</p>
							<p className="mt-1 text-sm text-red-700">
								{result.error_message || 'Please try uploading the document again.'}
							</p>
						</div>
					</div>
				)}

				{error && <p className="text-sm text-red-600">{error}</p>}

				<div className="flex justify-end gap-2 pt-2">
					<button
						type="button"
						onClick={onClose}
						disabled={isBusy}
						className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
					>
						{phase === 'done' ? 'Close' : 'Cancel'}
					</button>
				</div>
			</div>
		</ModalShell>
	)
}
