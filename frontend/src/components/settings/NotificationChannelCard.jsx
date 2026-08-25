import Toggle from '../common/Toggle'

const MIN_DELAY_MINUTES = 1
const MAX_DELAY_MINUTES = 120

function clampDelayMinutes(value) {
	if (!Number.isFinite(value)) return MIN_DELAY_MINUTES
	return Math.min(MAX_DELAY_MINUTES, Math.max(MIN_DELAY_MINUTES, Math.round(value)))
}

function timingSummary(delayMinutes) {
	if (!delayMinutes || delayMinutes <= 0) return 'Immediately'
	return `After ${delayMinutes} minute${delayMinutes === 1 ? '' : 's'}`
}

/**
 * One notification channel (Dashboard, WhatsApp, Email). Configuration
 * (label/description/icon) differs per channel; behavior and markup are
 * shared so all three channels stay in sync.
 *
 * `value` follows the backend shape: { enabled, delay_minutes }.
 * `delay_minutes === 0` means "Immediately"; a positive value means
 * "After N Minutes".
 */
export default function NotificationChannelCard({
	idPrefix,
	icon: Icon,
	label,
	description,
	value,
	isEditing,
	onChange,
}) {
	const { enabled, delay_minutes: delayMinutes } = value
	const timingMode = delayMinutes > 0 ? 'delayed' : 'immediate'

	function handleToggle() {
		onChange({ enabled: !enabled })
	}

	function handleTimingChange(mode) {
		if (mode === 'immediate') {
			onChange({ delay_minutes: 0 })
		} else {
			onChange({ delay_minutes: clampDelayMinutes(delayMinutes > 0 ? delayMinutes : 5) })
		}
	}

	function handleDelayInputChange(event) {
		const raw = Number(event.target.value)
		if (Number.isNaN(raw)) return
		onChange({ delay_minutes: clampDelayMinutes(raw) })
	}

	const toggleId = `${idPrefix}-toggle`
	const immediateId = `${idPrefix}-immediate`
	const delayedId = `${idPrefix}-delayed`
	const delayInputId = `${idPrefix}-delay-minutes`

	return (
		<div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
			<div className="flex items-start justify-between gap-3">
				<div className="flex items-start gap-3">
					<span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
						<Icon size={18} />
					</span>
					<div>
						<label htmlFor={toggleId} className="text-sm font-semibold text-slate-800">
							{label}
						</label>
						{description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
					</div>
				</div>
				<Toggle id={toggleId} on={enabled} onToggle={handleToggle} disabled={!isEditing} ariaLabel={label} />
			</div>

			{!isEditing ? (
				<p className="mt-3 border-t border-slate-200 pt-3 text-xs text-slate-500">
					{enabled ? `Notify ${timingSummary(delayMinutes).toLowerCase()}` : 'Notifications disabled'}
				</p>
			) : (
				enabled && (
					<fieldset className="mt-4 border-t border-slate-200 pt-4">
						<legend className="text-xs font-semibold uppercase tracking-wide text-slate-400">
							Notification Timing
						</legend>
						<div className="mt-2 space-y-2">
							<label htmlFor={immediateId} className="flex items-center gap-2 text-sm text-slate-700">
								<input
									id={immediateId}
									type="radio"
									name={`${idPrefix}-timing`}
									checked={timingMode === 'immediate'}
									onChange={() => handleTimingChange('immediate')}
									className="h-4 w-4 text-amber-500 focus:ring-amber-400"
								/>
								Immediately
							</label>
							<div className="flex flex-wrap items-center gap-2">
								<label htmlFor={delayedId} className="flex items-center gap-2 text-sm text-slate-700">
									<input
										id={delayedId}
										type="radio"
										name={`${idPrefix}-timing`}
										checked={timingMode === 'delayed'}
										onChange={() => handleTimingChange('delayed')}
										className="h-4 w-4 text-amber-500 focus:ring-amber-400"
									/>
									After
								</label>
								{timingMode === 'delayed' && (
									<>
										<label htmlFor={delayInputId} className="sr-only">
											{label} delay in minutes
										</label>
										<input
											id={delayInputId}
											type="number"
											inputMode="numeric"
											min={MIN_DELAY_MINUTES}
											max={MAX_DELAY_MINUTES}
											step={1}
											value={delayMinutes}
											onChange={handleDelayInputChange}
											className="w-20 rounded-lg border border-slate-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
										/>
										<span className="text-sm text-slate-700">Minutes</span>
									</>
								)}
							</div>
						</div>
					</fieldset>
				)
			)}
		</div>
	)
}
