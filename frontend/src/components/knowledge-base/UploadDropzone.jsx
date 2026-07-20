import { useRef, useState } from 'react'
import { FileUp, UploadCloud } from 'lucide-react'

const ACCEPTED_EXTENSIONS = new Set(['pdf', 'docx', 'md', 'txt'])
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

function getExtension(fileName) {
	return fileName.split('.').pop()?.toLowerCase()
}

function validateFile(file) {
	const extension = getExtension(file.name)

	if (!ACCEPTED_EXTENSIONS.has(extension)) {
		return 'Choose a PDF, DOCX, Markdown, or text file.'
	}

	if (file.size > MAX_FILE_SIZE_BYTES) {
		return 'Choose a file smaller than 10 MB.'
	}

	return null
}

export default function UploadDropzone({ onFileSelected, onValidationError, disabled = false }) {
	const inputRef = useRef(null)
	const [isDragging, setIsDragging] = useState(false)

	function handleFile(file) {
		const validationError = validateFile(file)

		if (validationError) {
			onValidationError(validationError)
			return
		}

		onFileSelected(file)
	}

	function handleDrop(event) {
		event.preventDefault()
		setIsDragging(false)

		if (!disabled) {
			const [file] = event.dataTransfer.files
			if (file) handleFile(file)
		}
	}

	function openFilePicker() {
		if (!disabled) inputRef.current?.click()
	}

	return (
		<div>
			<button
				type="button"
				disabled={disabled}
				onClick={openFilePicker}
				onDragOver={event => {
					event.preventDefault()
					if (!disabled) setIsDragging(true)
				}}
				onDragLeave={() => setIsDragging(false)}
				onDrop={handleDrop}
				className={`flex min-h-60 w-full flex-col items-center justify-center gap-4
										rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors
										focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2
										${disabled ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-60' : 'cursor-pointer'}
										${isDragging
											? 'border-amber-400 bg-amber-50'
											: 'border-slate-300 bg-white hover:border-amber-300 hover:bg-slate-50'}`}
			>
				<span className="flex h-14 w-14 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
					{isDragging ? <FileUp size={26} /> : <UploadCloud size={26} />}
				</span>
				<span>
					<span className="block text-sm font-semibold text-slate-800">
						{isDragging ? 'Drop your file here' : 'Drag and drop your knowledge-base file'}
					</span>
					<span className="mt-1 block text-sm text-slate-500">
						or <span className="font-medium text-amber-600">browse files</span>
					</span>
					<span className="mt-3 block text-xs text-slate-400">
						PDF, DOCX, MD, or TXT up to 10 MB
					</span>
				</span>
			</button>

			<input
				ref={inputRef}
				type="file"
				accept=".pdf,.docx,.md,.txt"
				className="hidden"
				disabled={disabled}
				onChange={event => {
					const [file] = event.target.files
					if (file) handleFile(file)
					event.target.value = ''
				}}
			/>
		</div>
	)
}
