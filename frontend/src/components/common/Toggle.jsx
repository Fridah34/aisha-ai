/**
 * Reusable on/off switch. Shared across Settings, Categories, and Products
 * so the interaction and styling stay identical everywhere a toggle appears.
 */
export default function Toggle({ on, onToggle, disabled = false, id, ariaLabel }) {
	return (
		<button
			type="button"
			id={id}
			onClick={onToggle}
			disabled={disabled}
			role="switch"
			aria-checked={on}
			aria-label={ariaLabel}
			className={`relative inline-flex w-11 h-6 rounded-full shrink-0
                  transition-colors duration-200 ease-in-out
                  focus:outline-none focus:ring-2 focus:ring-amber-400
                  focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
                  ${on ? 'bg-emerald-500' : 'bg-slate-300'}`}
		>
			<span
				className={`absolute top-[3px] left-[3px] w-[18px] h-[18px]
                    bg-white rounded-full shadow-sm
                    transition-transform duration-200 ease-in-out
                    ${on ? 'translate-x-[20px]' : 'translate-x-0'}`}
			/>
		</button>
	)
}
