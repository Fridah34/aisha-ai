const ROOT = '/api/knowledge-base'
const BASE = `${ROOT}/documents`

function documentUrl(documentId) {
	return `${BASE}/${documentId}`
}

/** Builds the URL used to preview/download a document's original file. */
export function getDocumentFileUrl(documentId) {
	return `${BASE}/${documentId}/file`
}

async function parseJsonResponse(response) {
	const payload = await response.json().catch(() => null)

	if (!response.ok) {
		const message = payload?.detail || payload?.message || `Request failed (HTTP ${response.status}).`
		throw new Error(message)
	}

	return payload
}

async function requestJson(url, options) {
	let response

	try {
		response = await fetch(url, options)
	} catch {
		throw new Error('Unable to reach the server. Check your connection and try again.')
	}

	return parseJsonResponse(response)
}

/**
 * Fetches the backend's Knowledge Base upload configuration (max file size,
 * supported formats). This is the single source of truth — the frontend
 * must never hardcode these values, so callers should always go through
 * this function instead of duplicating limits locally. Cached in-memory
 * since the config doesn't change during a session.
 */
let configPromise = null

export async function getConfig() {
	if (!configPromise) {
		configPromise = requestJson(`${ROOT}/config`).catch(error => {
			configPromise = null
			throw error
		})
	}
	return configPromise
}

export async function listDocuments() {
	return requestJson(BASE)
}

export async function getDocument(documentId) {
	return requestJson(documentUrl(documentId))
}

export async function updateDocument(documentId, updates) {
	return requestJson(documentUrl(documentId), {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates),
	})
}

export async function deleteDocument(documentId) {
	return requestJson(documentUrl(documentId), { method: 'DELETE' })
}

export async function retryDocument(documentId) {
	return requestJson(`${BASE}/${documentId}/retry`, {
		method: 'POST',
	})
}

/**
 * Uploads via XHR (instead of fetch) so real upload progress is available.
 * This lets the UI distinguish "Uploading..." (bytes still transferring)
 * from "AISHA is learning..." (server has the file and is processing it).
 */
function uploadWithProgress({ url, method, file, onProgress }) {
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest()
		const formData = new FormData()
		formData.append('file', file)

		xhr.open(method, url)

		xhr.upload.onprogress = event => {
			if (event.lengthComputable && onProgress) {
				onProgress(event.loaded / event.total)
			}
		}

		xhr.onload = () => {
			if (onProgress) onProgress(1)

			let payload = null
			try {
				payload = JSON.parse(xhr.responseText)
			} catch {
				payload = null
			}

			if (xhr.status >= 200 && xhr.status < 300) {
				resolve(payload)
			} else {
				const message = payload?.detail || payload?.message || `Upload failed (HTTP ${xhr.status}).`
				reject(new Error(message))
			}
		}

		xhr.onerror = () => {
			reject(new Error('Unable to reach the server. Check your connection and try again.'))
		}

		xhr.send(formData)
	})
}

function assertFile(file) {
	if (!(file instanceof File)) {
		throw new Error('Please choose a file to upload.')
	}
}

export async function uploadDocument(file, { onProgress } = {}) {
	assertFile(file)

	return uploadWithProgress({
		url: BASE,
		method: 'POST',
		file,
		onProgress,
	})
}

export async function replaceDocument(documentId, file, { onProgress } = {}) {
	assertFile(file)

	return uploadWithProgress({
		url: `${BASE}/${documentId}/replace`,
		method: 'PUT',
		file,
		onProgress,
	})
}

/** Legacy alias kept for KnowledgeUploadCard.jsx. */
export async function uploadKnowledgeBase(file) {
	return uploadDocument(file)
}

