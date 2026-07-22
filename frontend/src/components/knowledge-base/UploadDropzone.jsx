import { useRef, useState } from 'react'
import { FileUp, UploadCloud } from 'lucide-react'

function getExtension(fileName) {
	return fileName.split('.').pop()?.toLowerCase()
}

function validateFile(file, config) {
	const extension = getExtension(file.name)
	const acceptedExtensions = new Set(config.supported_formats)
	const maxUploadBytes = config.max_upload_size_mb * 1024 * 1024

	if (!acceptedExtensions.has(extension)) {
		return "This file type isn't supported. Please upload a PDF, DOCX, Markdown, or TXT file."
	}

	if (file.size > maxUploadBytes) {
		return `The selected file exceeds the ${config.max_upload_size_mb} MB upload limit.`
	}

	return null
}

/**
 * `config` must be the object returned by the backend's
 * `/api/knowledge-base/config` endpoint (see `useKnowledgeBaseConfig`
 * hook) — the backend is the single source of truth for upload limits and
 * supported formats, so this component never hardcodes its own.
 */
export default function UploadDropzone({
	config,
	onFileSelected,
	onValidationError,
	disabled = false,
	title = 'Drag and drop your file',
	description = 'or click to browse your computer',
	showFormatsHint = true,
	compact = false,
}) {
	const inputRef = useRef(null)
	const [isDragging, setIsDragging] = useState(false)
	const isReady = Boolean(config)
	const isDisabled = disabled || !isReady

	function handleFile(file) {
		if (!isReady) return

		const validationError = validateFile(file, config)

		if (validationError) {
			onValidationError(validationError)
			return
		}

		onFileSelected(file)
	}

	function handleDrop(event) {
		event.preventDefault()
		setIsDragging(false)

		if (!isDisabled) {
			const [file] = event.dataTransfer.files
			if (file) handleFile(file)
		}
	}

	function openFilePicker() {
		if (!isDisabled) inputRef.current?.click()
	}

	return (
		<div>
			<button
				type="button"
				disabled={isDisabled}
				onClick={openFilePicker}
				onDragOver={event => {
					event.preventDefault()
					if (!isDisabled) setIsDragging(true)
				}}
				onDragLeave={() => setIsDragging(false)}
				onDrop={handleDrop}
				className={`flex w-full flex-col items-center justify-center gap-3
										rounded-xl border-2 border-dashed px-6 text-center transition-colors
										focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2
										${compact ? 'min-h-32 py-6' : 'min-h-48 py-8'}
										${isDisabled ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-60' : 'cursor-pointer'}
										${isDragging
											? 'border-amber-400 bg-amber-50'
											: 'border-slate-300 bg-white hover:border-amber-300 hover:bg-slate-50'}`}
			>
				<span className={`flex items-center justify-center rounded-lg bg-amber-100 text-amber-600 ${compact ? 'h-10 w-10' : 'h-12 w-12'}`}>
					{isDragging ? <FileUp size={compact ? 20 : 24} /> : <UploadCloud size={compact ? 20 : 24} />}
				</span>
				<span>
					<span className="block text-sm font-semibold text-slate-800">
						{isDragging ? 'Drop your file here' : title}
					</span>
					<span className="mt-1 block text-xs text-slate-500">
						{isReady ? description : 'Loading upload settings…'}
					</span>
					{showFormatsHint && isReady && (
						<span className="mt-2 block text-xs text-slate-400">
							{config.supported_formats.map(format => format.toUpperCase()).join(', ')} up to{' '}
							{config.max_upload_size_mb} MB
						</span>
					)}
				</span>
			</button>

			<input
				ref={inputRef}
				type="file"
				accept={isReady ? config.supported_formats.map(format => `.${format}`).join(',') : undefined}
				className="hidden"
				disabled={isDisabled}
				onChange={event => {
					const [file] = event.target.files
					if (file) handleFile(file)
					event.target.value = ''
				}}
			/>
		</div>
	)
}
