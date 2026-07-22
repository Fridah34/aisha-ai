import { FileStack, Upload } from 'lucide-react'

export default function EmptyDocumentsState({ onUploadClick, isFiltered }) {
	if (isFiltered) {
		return (
			<div className="rounded-2xl border border-slate-200 bg-slate-50 p-10 text-center">
				<p className="text-sm font-medium text-slate-600">No documents match your search</p>
				<p className="mt-1 text-sm text-slate-500">Try a different keyword or filter.</p>
			</div>
		)
	}

	return (
		<div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
			<span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-600">
				<FileStack size={26} />
			</span>
			<h3 className="mt-4 text-base font-semibold text-slate-800">No documents uploaded yet</h3>
			<p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
				Upload business documents like price lists, menus, company policies, or product catalogues to help
				AISHA answer customer questions accurately.
			</p>
			<button
				type="button"
				onClick={onUploadClick}
				className="mt-5 inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
			>
				<Upload size={16} />
				Upload Document
			</button>
		</div>
	)
}
