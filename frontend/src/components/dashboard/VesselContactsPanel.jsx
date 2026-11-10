import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Activity,
  Anchor,
  Crosshair,
  Navigation,
  Radio,
  Radar,
  Signal,
} from 'lucide-react'

export default function VesselContactsPanel({
  contacts = [],
  selectedVessel,
  onSelectVessel,
}) {
  const { t } = useTranslation()

  const sortedContacts = useMemo(
    () => [...contacts].sort((a, b) => a.id.localeCompare(b.id)),
    [contacts],
  )

  return (
    <section className="rounded-xl border border-cyan-400/15 bg-[#081321] p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-cyan-400/10 p-2">
            <Radar size={17} className="text-cyan-400" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              {t('vessels.title')}
            </h3>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              {t('vessels.subtitle')}
            </p>
          </div>
        </div>

        <span className="flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-2.5 py-1 text-[10px] text-cyan-300">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
          {contacts.length} {t('vessels.contacts')}
        </span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] text-slate-500">
            <Signal size={12} />
            {t('vessels.simulatedContacts')}
          </div>
          <div className="text-xl font-semibold tabular-nums text-white">
            {String(contacts.length).padStart(2, '0')}
          </div>
        </div>

        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] text-slate-500">
            <Activity size={12} />
            {t('vessels.source')}
          </div>
          <div className="text-sm font-semibold text-cyan-300">
            {t('vessels.simulation')}
          </div>
        </div>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          {t('vessels.contactList')}
        </span>
        <span className="text-[10px] text-slate-600">
          {t('vessels.selectToLocate')}
        </span>
      </div>

      {selectedVessel && (
        <div className="mb-4 rounded-xl border border-cyan-400/30 bg-cyan-400/5 p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-cyan-300">
              {t('vessels.selected')}
            </span>
            <Crosshair size={16} className="text-cyan-400" />
          </div>

          <h4 className="text-lg font-bold text-white">
            {selectedVessel.id}
          </h4>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-slate-500">
                {t('vessels.simulatedSpeed')}
              </p>
              <p className="mt-1 text-sm font-semibold text-cyan-300">
                {selectedVessel.speed} kn
              </p>
            </div>

            <div>
              <p className="text-[10px] text-slate-500">
                {t('vessels.simulatedHeading')}
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {selectedVessel.heading}°
              </p>
            </div>

            <div>
              <p className="text-[10px] text-slate-500">
                {t('vessels.longitude')}
              </p>
              <p className="mt-1 text-xs text-slate-300">
                {selectedVessel.coordinates?.[0]?.toFixed(4) ?? '—'}
              </p>
            </div>

            <div>
              <p className="text-[10px] text-slate-500">
                {t('vessels.latitude')}
              </p>
              <p className="mt-1 text-xs text-slate-300">
                {selectedVessel.coordinates?.[1]?.toFixed(4) ?? '—'}
              </p>
            </div>
          </div>

          <p className="mt-3 border-t border-cyan-400/10 pt-3 text-[10px] text-slate-500">
            {t('vessels.demoWarning')}
          </p>
        </div>
      )}

      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {sortedContacts.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-700 p-5 text-center">
            <Radio className="mx-auto mb-2 text-slate-600" size={22} />
            <p className="text-xs text-slate-400">
              {t('vessels.waiting')}
            </p>
          </div>
        ) : (
          sortedContacts.map((contact) => {
            const isSelected = selectedVessel?.id === contact.id

            return (
              <button
                key={contact.id}
                type="button"
                onClick={() => onSelectVessel?.(contact)}
                className={`group flex w-full items-center justify-between rounded-xl border p-3 text-left transition-all ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-400/10'
                    : 'border-white/10 bg-white/[0.03] hover:border-cyan-400/40'
                }`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className={`rounded-lg p-2 ${
                      isSelected
                        ? 'bg-cyan-400/20 text-cyan-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Anchor size={16} />
                  </div>

                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-100">
                      {contact.id}
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500">
                      {contact.speed} kn · {t('vessels.simulatedHeading')} {contact.heading}°
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                  <Crosshair
                    size={15}
                    className="text-slate-500 transition-colors group-hover:text-cyan-300"
                  />
                </div>
              </button>
            )
          })
        )}
      </div>

      <div className="mt-3 flex items-center gap-2 border-t border-slate-800 pt-3">
        <Navigation size={12} className="text-cyan-500" />
        <p className="text-[10px] leading-relaxed text-slate-500">
          {t('vessels.positionWarning')}
        </p>
      </div>
    </section>
  )
}