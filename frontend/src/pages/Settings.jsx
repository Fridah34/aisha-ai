import HandoverNotifications from '../components/settings/HandoverNotifications'

export default function Settings() {
  return (
    <section className="max-w-6xl p-5 sm:p-8" aria-labelledby="settings-title">
      <header className="mb-8">
        <h1 id="settings-title" className="text-2xl font-semibold text-slate-800">
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage how AISHA works for your business.
        </p>
      </header>

      <div className="space-y-6">
        <HandoverNotifications />
      </div>
    </section>
  )
}