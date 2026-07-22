import { Pencil } from 'lucide-react'
import SaveStatus from '../../common/SaveStatus'

/**
 * Shared card frame for Business Information sections: header with a single
 * Edit action, a view/edit body, and a Save/Cancel footer while editing.
 */
export default function CardShell({
	title,
	description,
	isEditing,
	onEdit,
	onCancel,
	onSave,
	saveStatus,
	savedAt,
	disableSave = false,
	children,
}) {
	return (
		<div className="bg-white border border-slate-200 rounded-2xl p-6">
			<div className="mb-4 flex items-start justify-between gap-3">
				<div>
					<h3 className="text-base font-semibold text-slate-800">{title}</h3>
					{description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
				</div>

				{!isEditing && (
					<button
						type="button"
						onClick={onEdit}
						className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-amber-400"
					>
						<Pencil size={13} />
						Edit
					</button>
				)}
			</div>

			{children}

			{isEditing && (
				<div className="mt-5 flex items-center justify-between gap-3 border-t border-slate-200 pt-4">
					<SaveStatus status={saveStatus} />
					<div className="flex gap-2">
						<button
							type="button"
							onClick={onCancel}
							className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-amber-400"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={onSave}
							disabled={disableSave}
							className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
						>
							Save Changes
						</button>
					</div>
				</div>
			)}

			{!isEditing && savedAt && (
				<div className="mt-4 border-t border-slate-200 pt-3">
					<SaveStatus savedAt={savedAt} />
				</div>
			)}
		</div>
	)
}
