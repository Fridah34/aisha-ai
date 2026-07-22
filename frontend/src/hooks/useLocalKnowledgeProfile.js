import { useCallback, useEffect, useState } from 'react'
import { getCurrentBusinessId } from '../api/client'

/**
 * Frontend-only persistence for Knowledge Base sections that don't have a
 * backend field yet (Business Operations, AI Instructions, Custom Knowledge
 * Sources, FAQs). Backed by localStorage, scoped per business, so the UX for
 * these sections is fully usable ahead of the backend work that will
 * eventually replace this with real API calls.
 */

const DEFAULT_PROFILE = {
	businessProfile: { description: '' },
	operations: { address: '', contact: '', hours: '', deliveryAreas: '', paymentMethods: '' },
	aiInstructions: { personality: '', greetingStyle: '', tone: '', escalationRules: '', restrictedResponses: '' },
	knowledgeSources: [],
	faqs: [],
	updatedAt: {},
}

function storageKey(businessId) {
	return `aisha_kb_profile_${businessId}`
}

function loadProfile(businessId) {
	try {
		const raw = localStorage.getItem(storageKey(businessId))
		if (!raw) return structuredClone(DEFAULT_PROFILE)
		const parsed = JSON.parse(raw)
		return { ...structuredClone(DEFAULT_PROFILE), ...parsed }
	} catch {
		return structuredClone(DEFAULT_PROFILE)
	}
}

function saveProfile(businessId, profile) {
	localStorage.setItem(storageKey(businessId), JSON.stringify(profile))
}

export function useLocalKnowledgeProfile() {
	const businessId = getCurrentBusinessId()
	const [profile, setProfile] = useState(() => loadProfile(businessId))

	useEffect(() => {
		saveProfile(businessId, profile)
	}, [businessId, profile])

	const updateSection = useCallback((section, value) => {
		setProfile(current => ({
			...current,
			[section]: value,
			updatedAt: { ...current.updatedAt, [section]: new Date().toISOString() },
		}))
	}, [])

	const addFaq = useCallback(faq => {
		setProfile(current => ({
			...current,
			faqs: [{ id: crypto.randomUUID(), ...faq }, ...current.faqs],
			updatedAt: { ...current.updatedAt, faqs: new Date().toISOString() },
		}))
	}, [])

	const updateFaq = useCallback((id, faq) => {
		setProfile(current => ({
			...current,
			faqs: current.faqs.map(item => (item.id === id ? { ...item, ...faq } : item)),
			updatedAt: { ...current.updatedAt, faqs: new Date().toISOString() },
		}))
	}, [])

	const deleteFaq = useCallback(id => {
		setProfile(current => ({
			...current,
			faqs: current.faqs.filter(item => item.id !== id),
			updatedAt: { ...current.updatedAt, faqs: new Date().toISOString() },
		}))
	}, [])

	const addKnowledgeSource = useCallback(source => {
		setProfile(current => ({
			...current,
			knowledgeSources: [{ id: crypto.randomUUID(), status: 'learning', ...source }, ...current.knowledgeSources],
			updatedAt: { ...current.updatedAt, knowledgeSources: new Date().toISOString() },
		}))
	}, [])

	const updateKnowledgeSourceStatus = useCallback((id, status) => {
		setProfile(current => ({
			...current,
			knowledgeSources: current.knowledgeSources.map(item => (item.id === id ? { ...item, status } : item)),
		}))
	}, [])

	const deleteKnowledgeSource = useCallback(id => {
		setProfile(current => ({
			...current,
			knowledgeSources: current.knowledgeSources.filter(item => item.id !== id),
			updatedAt: { ...current.updatedAt, knowledgeSources: new Date().toISOString() },
		}))
	}, [])

	return {
		profile,
		updateSection,
		addFaq,
		updateFaq,
		deleteFaq,
		addKnowledgeSource,
		updateKnowledgeSourceStatus,
		deleteKnowledgeSource,
	}
}
