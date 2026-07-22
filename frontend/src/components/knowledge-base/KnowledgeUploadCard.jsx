import { useState } from 'react'
import { BookOpen } from 'lucide-react'
import { uploadKnowledgeBase } from '../../services/knowledgeBaseService'
import useKnowledgeBaseConfig from '../../hooks/useKnowledgeBaseConfig'
import UploadDropzone from './UploadDropzone'
import UploadStatus from './UploadStatus'

export default function KnowledgeUploadCard() {
	const { config } = useKnowledgeBaseConfig()
	const [status, setStatus] = useState('idle')
	const [fileName, setFileName] = useState('')
	const [message, setMessage] = useState('')

	async function handleFileSelected(file) {
		setFileName(file.name)
		setMessage('')
		setStatus('uploading')

		try {
			const response = await uploadKnowledgeBase(file)
			setMessage(response?.message || response?.detail || 'Your knowledge base file was uploaded successfully.')
			setStatus('success')
		} catch (error) {
			setMessage(error instanceof Error ? error.message : 'The file could not be uploaded. Please try again.')
			setStatus('failed')
		}
	}

	function handleValidationError(errorMessage) {
		setFileName('')
		setMessage(errorMessage)
		setStatus('failed')
	}

	function handleReset() {
		setFileName('')
		setMessage('')
		setStatus('idle')
	}

	return (
		<section className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
			<div className="mb-5 flex items-start gap-3">
				<span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
					<BookOpen size={21} />
				</span>
				<div>
					<h2 className="text-base font-semibold text-slate-800">Upload knowledge base</h2>
					<p className="mt-1 text-sm text-slate-500">
						Add product information, policies, or frequently asked questions for AISHA.
					</p>
				</div>
			</div>

			<UploadDropzone
				config={config}
				disabled={status === 'uploading'}
				onFileSelected={handleFileSelected}
				onValidationError={handleValidationError}
			/>
			<UploadStatus
				status={status}
				fileName={fileName}
				message={message}
				onReset={handleReset}
			/>
		</section>
	)
}
