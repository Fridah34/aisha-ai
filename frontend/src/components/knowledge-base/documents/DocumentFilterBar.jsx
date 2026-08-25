import { Search } from 'lucide-react'
import { FILTERS } from './documentUtils'

export default function DocumentFilterBar({ searchQuery, onSearchChange, activeFilter, onFilterChange }) {
	return (
		<div className="space-y-3">
			<div className="relative">
				<Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
				<input
					type="search"
					value={searchQuery}
					onChange={event => onSearchChange(event.target.value)}
					placeholder="Search by document name, category, or file type"
					className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
				/>
			</div>

			<div className="flex flex-wrap gap-2">
				{FILTERS.map(filter => (
					<button
						key={filter.id}
						type="button"
						onClick={() => onFilterChange(filter.id)}
						className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 ${
							activeFilter === filter.id
								? 'border-amber-300 bg-amber-100 text-amber-700'
								: 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
						}`}
					>
						{filter.label}
					</button>
				))}
			</div>
		</div>
	)
}
