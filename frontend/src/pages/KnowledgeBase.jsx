import KnowledgeUploadCard from '../components/knowledge-base/KnowledgeUploadCard'

export default function KnowledgeBase() {
	return (
		<section className="max-w-6xl p-5 sm:p-8" aria-labelledby="knowledge-base-title">
			<header className="mb-7">
				<h1 id="knowledge-base-title" className="text-2xl font-semibold text-slate-800">
					Knowledge Base
				</h1>
				<p className="mt-1 text-sm text-slate-500">
					Upload business documents to train AISHA&apos;s Knowledge Base.
				</p>
			</header>

			<KnowledgeUploadCard />
		</section>
	)
}
