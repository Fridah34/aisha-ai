import { useCallback, useEffect, useState } from 'react'

/**
 * Guards navigation away from a form with unsaved edits.
 * - Blocks browser tab close/refresh via `beforeunload` while dirty.
 * - Exposes `requestNavigation(action)` for in-app navigation (e.g. switching
 *   Knowledge Base tabs): if dirty, the action is deferred and a
 *   confirmation prompt is shown instead of running immediately.
 */
export function useUnsavedChangesGuard(isDirty) {
	const [pendingAction, setPendingAction] = useState(null)

	useEffect(() => {
		function handleBeforeUnload(event) {
			if (!isDirty) return
			event.preventDefault()
			event.returnValue = ''
		}

		window.addEventListener('beforeunload', handleBeforeUnload)
		return () => window.removeEventListener('beforeunload', handleBeforeUnload)
	}, [isDirty])

	const requestNavigation = useCallback(
		action => {
			if (isDirty) {
				setPendingAction(() => action)
			} else {
				action()
			}
		},
		[isDirty]
	)

	const confirmLeave = useCallback(() => {
		setPendingAction(current => {
			current?.()
			return null
		})
	}, [])

	const cancelLeave = useCallback(() => {
		setPendingAction(null)
	}, [])

	return {
		isPromptOpen: pendingAction !== null,
		requestNavigation,
		confirmLeave,
		cancelLeave,
	}
}
