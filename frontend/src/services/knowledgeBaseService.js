import { getCurrentBusinessId } from '../api/client'

export async function uploadKnowledgeBase(file) {
	if (!(file instanceof File)) {
		throw new Error('Please choose a file to upload.')
	}

	const formData = new FormData()
	formData.append('file', file)

	let response
	const businessId = getCurrentBusinessId()

	try {
		response = await fetch(
			`/api/knowledge-base/upload?business_id=${encodeURIComponent(businessId)}`,
			{
				method: 'POST',
				body: formData,
			}
		)
	} catch {
		throw new Error(
			'Unable to reach the server. Check your connection and try again.'
		)
	}

	const payload = await response.json().catch(() => null)

	if (!response.ok) {
		const message = payload?.detail || payload?.message || `Upload failed (HTTP ${response.status}).`
		throw new Error(message)
	}

	return payload
}
