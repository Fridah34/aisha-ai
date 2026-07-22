import { useEffect, useMemo, useRef, useState } from 'react'
import { Upload, Lightbulb } from 'lucide-react'
import {
	deleteDocument,
	listDocuments,
	retryDocument,
	uploadDocument,
} from '../../services/knowledgeBaseService'
import { useToast } from '../../context/ToastContext'
import { SkeletonList } from '../common/Skeleton'
import ConfirmDialog from '../common/ConfirmDialog'
import UploadDropzone from './UploadDropzone'
import DocumentFilterBar from './documents/DocumentFilterBar'
import DocumentListItem from './documents/DocumentListItem'
import EmptyDocumentsState from './documents/EmptyDocumentsState'
import DocumentViewModal from './documents/DocumentViewModal'
import DocumentEditModal from './documents/DocumentEditModal'
import DocumentReplaceModal from './documents/DocumentReplaceModal'
import { matchesFilter, matchesSearch } from './documents/documentUtils'
import useKnowledgeBaseConfig from '../../hooks/useKnowledgeBaseConfig'

// Cosmetic display labels only — the actual list of supported extensions
// and the upload limit always come from the backend config (single source
// of truth), never hardcoded here.
const FORMAT_LABELS = { pdf: 'PDF', docx: 'DOCX', md: 'Markdown', txt: 'TXT' }

const BUSINESS_KNOWLEDGE_EXAMPLES = [
	'Product Catalogues',
	'Price Lists',
	'Menus',
	'Product Specifications',
	'Company Policies',
	'Delivery Information',
	'Return & Refund Policies',
	'Service Brochures',
	'User Manuals',
	'Frequently Asked Questions',
	'Marketing Materials',
	'Warranty Information',
	'Company Profile',
	'Terms & Conditions',
	'Operating Procedures',
]

function UploadStepToast({ title, description }) {
	return (
		<span>
			<span className="block font-semibold">{title}</span>
			<span className="mt-0.5 block text-xs font-normal opacity-80">{description}</span>
		</span>
	)
}


export default function Documents() {
	const { showToast } = useToast()
	const uploadSectionRef = useRef(null)
	const { config } = useKnowledgeBaseConfig()

	const [documents, setDocuments] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [loadError, setLoadError] = useState('')

	const [searchQuery, setSearchQuery] = useState('')
	const [activeFilter, setActiveFilter] = useState('all')

	const [viewingDocument, setViewingDocument] = useState(null)
	const [editingDocument, setEditingDocument] = useState(null)
	const [replacingDocument, setReplacingDocument] = useState(null)
	const [pendingDeleteDocument, setPendingDeleteDocument] = useState(null)

	async function refreshDocuments() {
		setIsLoading(true)
		setLoadError('')
		try {
			const rows = await listDocuments()
			setDocuments(rows || [])
		} catch (error) {
			setLoadError(error instanceof Error ? error.message : 'Could not load your documents.')
		} finally {
			setIsLoading(false)
		}
	}

	useEffect(() => {
		refreshDocuments()
	}, [])

	async function handleFileSelected(file) {
		const placeholderId = `uploading-${crypto.randomUUID()}`
		const placeholder = {
			id: placeholderId,
			display_name: file.name,
			file_type: (file.name.split('.').pop() || '').toUpperCase(),
			file_size: file.size,
			status: 'uploading',
			created_at: new Date().toISOString(),
		}
		setDocuments(current => [placeholder, ...current])
		showToast(
			<UploadStepToast title="✓ Upload successful" description="AISHA is learning from your document..." />,
			{ variant: 'success' }
		)

		try {
			const created = await uploadDocument(file)
			setDocuments(current => current.map(doc => (doc.id === placeholderId ? created : doc)))

			if (created.status === 'ready') {
				showToast(
					<UploadStepToast title="✓ Ready" description="AISHA can now answer questions using this document." />,
					{ variant: 'success' }
				)
			} else if (created.status === 'failed') {
				showToast(created.error_message || 'AISHA could not learn from this document.', { variant: 'error' })
			}
		} catch (error) {
			setDocuments(current => current.filter(doc => doc.id !== placeholderId))
			showToast(error instanceof Error ? error.message : 'The file could not be uploaded. Please try again.', {
				variant: 'error',
			})
		}
	}

	function handleValidationError(message) {
		showToast(message, { variant: 'error' })
	}

	async function handleRetry(document) {
		setDocuments(current =>
			current.map(doc => (doc.id === document.id ? { ...doc, status: 'learning' } : doc))
		)
		try {
			const updated = await retryDocument(document.id)
			setDocuments(current => current.map(doc => (doc.id === document.id ? updated : doc)))
			if (updated.status === 'ready') {
				showToast(
					<UploadStepToast title="✓ Ready" description="AISHA can now answer questions using this document." />,
					{ variant: 'success' }
				)
			} else {
				showToast(updated.error_message || 'Processing failed again.', { variant: 'error' })
			}
		} catch (error) {
			setDocuments(current => current.map(doc => (doc.id === document.id ? document : doc)))
			showToast(error instanceof Error ? error.message : 'Could not retry this document.', { variant: 'error' })
		}
	}

	async function handleConfirmDelete() {
		const document = pendingDeleteDocument
		setPendingDeleteDocument(null)
		try {
			await deleteDocument(document.id)
			setDocuments(current => current.filter(doc => doc.id !== document.id))
			showToast('✓ Document deleted successfully.', { variant: 'success' })
		} catch (error) {
			showToast(error instanceof Error ? error.message : 'Could not delete this document.', { variant: 'error' })
		}
	}

	function handleReplaced(updated) {
		setDocuments(current => current.map(doc => (doc.id === updated.id ? updated : doc)))
	}

	function handleEdited(updated) {
		setDocuments(current => current.map(doc => (doc.id === updated.id ? updated : doc)))
		setEditingDocument(null)
		showToast('✓ Document details saved', { variant: 'success' })
	}

	const filteredDocuments = useMemo(
		() =>
			documents.filter(document => matchesFilter(document, activeFilter) && matchesSearch(document, searchQuery)),
		[documents, activeFilter, searchQuery]
	)

	const hasAnyDocuments = documents.length > 0
	const isFiltered = searchQuery.trim().length > 0 || activeFilter !== 'all'

	return (
		<div className="space-y-6">
			{/* Header */}
			<div>
				<h2 className="text-xl font-semibold text-slate-800">
					Documents
				</h2>
				<p className="text-sm text-slate-500 mt-1">
					Upload product information, policies, and other documents that AISHA should know about.
				</p>
			</div>

			{/* Upload Section */}
			<div ref={uploadSectionRef} className="bg-white border border-slate-200 rounded-2xl p-6 space-y-6">
				<div className="flex items-start gap-3">
					<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
						<Upload size={20} />
					</div>
					<div>
						<h3 className="text-base font-semibold text-slate-800">Upload Business Knowledge</h3>
						<p className="text-sm text-slate-500 mt-0.5">
							Upload documents that help AISHA understand your business and answer customer questions more
							accurately.
						</p>
					</div>
				</div>

				<UploadDropzone
					config={config}
					compact
					showFormatsHint={false}
					title="Upload Business Documents"
					description="Drag & drop your files here, or click to browse your computer."
					onFileSelected={handleFileSelected}
					onValidationError={handleValidationError}
				/>

				{/* Supported formats — kept low-key, not the focus of the section */}
				<div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
					<span className="font-medium text-slate-500">Supported formats:</span>
					{(config?.supported_formats ?? []).map(format => (
						<span key={format} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-500">
							{FORMAT_LABELS[format] ?? format.toUpperCase()}
						</span>
					))}
					{config && <span className="ml-1">· Maximum size: {config.max_upload_size_mb} MB per document</span>}
				</div>

				{/* Examples of what you can upload */}
				<div>
					<p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
						Examples of what you can upload
					</p>
					<div className="mt-2 flex flex-wrap gap-2">
						{BUSINESS_KNOWLEDGE_EXAMPLES.map(example => (
							<span
								key={example}
								className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600"
							>
								{example}
							</span>
						))}
					</div>
				</div>

				{/* Helpful tip */}
				<div className="flex items-start gap-2.5 rounded-xl border border-amber-100 bg-amber-50 p-4">
					<Lightbulb size={16} className="mt-0.5 shrink-0 text-amber-500" />
					<p className="text-sm text-amber-800">
						<span className="font-semibold">Tip:</span> Upload several focused documents (like a Product
						Catalogue, a Price List, and a Delivery Policy) instead of one giant file — AISHA learns from
						each document independently, so smaller, well-organized documents work best.
					</p>
				</div>
			</div>

			{/* Document Manager */}
			<div className="space-y-4">
				{hasAnyDocuments && (
					<DocumentFilterBar
						searchQuery={searchQuery}
						onSearchChange={setSearchQuery}
						activeFilter={activeFilter}
						onFilterChange={setActiveFilter}
					/>
				)}

				{isLoading ? (
					<SkeletonList rows={3} />
				) : loadError ? (
					<div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
						{loadError}
					</div>
				) : filteredDocuments.length === 0 ? (
					<EmptyDocumentsState
						isFiltered={isFiltered && hasAnyDocuments}
						onUploadClick={() => uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
					/>
				) : (
					<ul className="space-y-3">
						{filteredDocuments.map(document => (
							<DocumentListItem
								key={document.id}
								document={document}
								onView={() => setViewingDocument(document)}
								onEdit={() => setEditingDocument(document)}
								onReplace={() => setReplacingDocument(document)}
								onDelete={() => setPendingDeleteDocument(document)}
								onRetry={() => handleRetry(document)}
							/>
						))}
					</ul>
				)}
			</div>

			{viewingDocument && (
				<DocumentViewModal document={viewingDocument} onClose={() => setViewingDocument(null)} />
			)}

			{editingDocument && (
				<DocumentEditModal
					document={editingDocument}
					onClose={() => setEditingDocument(null)}
					onSaved={handleEdited}
				/>
			)}

			{replacingDocument && (
				<DocumentReplaceModal
					document={replacingDocument}
					config={config}
					onClose={() => setReplacingDocument(null)}
					onReplaced={handleReplaced}
				/>
			)}

			<ConfirmDialog
				open={pendingDeleteDocument !== null}
				title="Delete Document?"
				description="Removing this document means AISHA will no longer use its information when answering customer questions."
				confirmLabel="Delete Document"
				tone="danger"
				onConfirm={handleConfirmDelete}
				onCancel={() => setPendingDeleteDocument(null)}
			/>
		</div>
	)
}

