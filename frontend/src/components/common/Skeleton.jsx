/** Basic pulsing placeholder block used to build skeleton loaders. */
export function SkeletonBlock({ className = '' }) {
	return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} aria-hidden="true" />
}

export function SkeletonCard({ lines = 3 }) {
	return (
		<div className="rounded-2xl border border-slate-200 bg-white p-6" aria-hidden="true">
			<SkeletonBlock className="h-3 w-24 mb-4" />
			<SkeletonBlock className="h-5 w-40 mb-3" />
			{Array.from({ length: lines }).map((_, index) => (
				<SkeletonBlock key={index} className="h-3 w-full mb-2" />
			))}
		</div>
	)
}

export function SkeletonRow() {
	return (
		<div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4" aria-hidden="true">
			<SkeletonBlock className="h-10 w-10 shrink-0 rounded-lg" />
			<div className="min-w-0 flex-1 space-y-2">
				<SkeletonBlock className="h-3.5 w-1/3" />
				<SkeletonBlock className="h-3 w-1/2" />
			</div>
			<SkeletonBlock className="h-6 w-20 rounded-full" />
		</div>
	)
}

export function SkeletonList({ rows = 3 }) {
	return (
		<ul className="space-y-3" aria-hidden="true">
			{Array.from({ length: rows }).map((_, index) => (
				<li key={index}>
					<SkeletonRow />
				</li>
			))}
		</ul>
	)
}
