import { useEffect, useRef, useState } from 'react'
import { MoreVertical, Eye, Pencil, RefreshCcw, Trash2 } from 'lucide-react'

export default function DocumentActionsMenu({ onView, onEdit, onReplace, onDelete }) {
	const [isOpen, setIsOpen] = useState(false)
	const containerRef = useRef(null)

	useEffect(() => {
		if (!isOpen) return

		function handleClickOutside(event) {
			if (containerRef.current && !containerRef.current.contains(event.target)) {
				setIsOpen(false)
			}
		}

		document.addEventListener('mousedown', handleClickOutside)
		return () => document.removeEventListener('mousedown', handleClickOutside)
	}, [isOpen])

	function runAndClose(action) {
		setIsOpen(false)
		action()
	}

	const items = [
		{ label: 'View', icon: Eye, onClick: onView },
		{ label: 'Edit', icon: Pencil, onClick: onEdit },
		{ label: 'Replace', icon: RefreshCcw, onClick: onReplace },
		{ label: 'Delete', icon: Trash2, onClick: onDelete, danger: true },
	]

	return (
		<div className="relative" ref={containerRef}>
			<button
				type="button"
				onClick={() => setIsOpen(prev => !prev)}
				aria-haspopup="menu"
				aria-expanded={isOpen}
				aria-label="Document actions"
				className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-400"
			>
				<MoreVertical size={18} />
			</button>

			{isOpen && (
				<div
					role="menu"
					className="absolute right-0 z-20 mt-1 w-40 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg"
				>
					{items.map(({ label, icon: Icon, onClick, danger }) => (
						<button
							key={label}
							type="button"
							role="menuitem"
							onClick={() => runAndClose(onClick)}
							className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
								danger ? 'text-red-600 hover:bg-red-50' : 'text-slate-700 hover:bg-slate-50'
							}`}
						>
							<Icon size={15} />
							{label}
						</button>
					))}
				</div>
			)}
		</div>
	)
}
