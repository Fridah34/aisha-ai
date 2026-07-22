import { useEffect, useState } from 'react'
import { getConfig } from '../services/knowledgeBaseService'

/**
 * Loads the backend's Knowledge Base upload configuration (max file size,
 * supported formats). The backend is the single source of truth for these
 * values, so components must render/validate uploads from this hook instead
 * of hardcoding limits.
 */
export default function useKnowledgeBaseConfig() {
	const [config, setConfig] = useState(null)
	const [error, setError] = useState('')

	useEffect(() => {
		let cancelled = false

		getConfig()
			.then(data => {
				if (!cancelled) setConfig(data)
			})
			.catch(err => {
				if (!cancelled) {
					setError(err instanceof Error ? err.message : 'Could not load upload settings.')
				}
			})

		return () => {
			cancelled = true
		}
	}, [])

	return { config, isLoading: !config && !error, error }
}
