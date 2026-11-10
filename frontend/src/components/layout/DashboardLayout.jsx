import { useState } from 'react'
import {
  Activity,
  Radio,
  Satellite,
  Anchor,
  Globe2,
  Waves,
  ShieldAlert,
  RefreshCw,
  Database,
  Radar,
  CalendarDays,
  TrendingUp,
  CircleDot,
  MapPin,
  Trophy
} from 'lucide-react'
import VesselContactsPanel from '../dashboard/VesselContactsPanel'
import Header from './Header'
import { useTranslation } from 'react-i18next'
import TemporalIntelligencePanel from '../dashboard/TemporalIntelligencePanel'
const numberFormat = new Intl.NumberFormat('fr-FR')

function formatNumber(value) {
  return numberFormat.format(Number(value ?? 0))
}

function formatHours(value) {
  const hours = Number(value ?? 0)

  if (hours >= 1_000_000) {
    return `${(hours / 1_000_000).toFixed(2).replace('.', ',')} M`
  }

  if (hours >= 1_000) {
    return `${(hours / 1_000).toFixed(1).replace('.', ',')} K`
  }

  return formatNumber(hours)
}

function Metric({ label, value, icon: Icon, color, description }) {
  return (
    <div className="group rounded-xl border border-white/[0.07] bg-[#0d1b2b] p-3.5 transition-all duration-200 hover:border-cyan-400/30 hover:bg-[#102238]">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[9px] font-semibold uppercase tracking-[0.13em] text-slate-500">
            {label}
          </p>

          <p className="mt-2 text-xl font-bold tracking-tight text-white sm:text-2xl">
            {value}
          </p>
        </div>

        <div className={`rounded-lg bg-white/[0.05] p-2 ${color}`}>
          <Icon size={17} strokeWidth={1.8} />
        </div>
      </div>

      {description && (
        <p className="mt-2 text-[9px] text-slate-500">
          {description}
        </p>
      )}
    </div>
  )
}

function SectionTitle({ children, icon: Icon }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={15} className="text-cyan-400" />
      <h4 className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-300">
        {children}
      </h4>
    </div>
  )
}

function ProgressRow({ label, value, total, color }) {
  const percentage = total > 0
    ? Math.min(100, Math.max(0, (value / total) * 100))
    : 0

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[10px]">
        <span className="text-slate-400">{label}</span>
        <span className="font-semibold text-slate-200">
          {formatNumber(value)}
        </span>
      </div>

      <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="mt-1 text-right text-[9px] text-slate-500">
        {percentage.toFixed(1).replace('.', ',')} %
      </p>
    </div>
  )
}




function RankingPanel({ ranking, rankingPeriod, onSelectCell }) {
  const [activeTab, setActiveTab] = useState('maai')
const { t, i18n } = useTranslation()
  const tabs = [
  { id: 'maai', label: 'MAAI', color: 'amber' },
  { id: 'ais', label: t('dashboard.observations'), color: 'cyan' },
  { id: 'sar', label: t('dashboard.unmatched'), color: 'rose' },
]

  const items = ranking?.rankings?.[activeTab === 'maai'
    ? 'attention_index'
    : activeTab === 'ais'
      ? 'ais_presence'
      : 'sar_unmatched'
  ] ?? []

  const formatScore = (value) =>
    Number(value ?? 0).toFixed(1).replace('.', ',')
const numberFormat = new Intl.NumberFormat(
  i18n.language === 'en' ? 'en-US' : 'fr-FR'
)
  const getScoreColor = (score) => {
    if (score >= 85) return 'text-rose-300 bg-rose-400/10'
    if (score >= 70) return 'text-amber-300 bg-amber-400/10'
    if (score >= 50) return 'text-cyan-300 bg-cyan-400/10'
    return 'text-slate-300 bg-slate-400/10'
  }

  return (
    <section className="overflow-hidden rounded-xl border border-white/[0.07] bg-[#0d1b2b]">

      {/* HEADER */}
      <div className="border-b border-white/[0.06] p-3">

        <div className="mb-3 flex items-center justify-between">
          <SectionTitle icon={Trophy}>
            Priorisation analytique
          </SectionTitle>

          <span className="text-[9px] text-slate-500">
            {rankingPeriod ?? 'OCT. 2026'}
          </span>
        </div>

        {/* TABS */}
        <div className="grid grid-cols-3 gap-1 rounded-lg bg-[#07111f] p-1">

          {tabs.map((tab) => {
            const active = activeTab === tab.id

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-md px-1.5 py-2 text-[9px] font-semibold transition ${
                  active
                    ? tab.id === 'maai'
                      ? 'bg-amber-400/15 text-amber-300'
                      : tab.id === 'ais'
                        ? 'bg-cyan-400/15 text-cyan-300'
                        : 'bg-rose-400/15 text-rose-300'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            )
          })}

        </div>
      </div>

      {/* LIST */}
      <div className="space-y-1 p-2">

        {items.length === 0 ? (
          <p className="px-3 py-6 text-center text-[10px] text-slate-500">
            Aucun résultat disponible.
          </p>
        ) : (
          items.map((cell) => {

            const score = Number(cell.attention_index ?? 0)

            return (
              <button
                key={cell.cell_id}
                onClick={() => onSelectCell?.(cell)}
                className="group w-full rounded-lg border border-transparent p-2.5 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/[0.04]"
              >

                <div className="flex items-start gap-2.5">

                  {/* RANK */}
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/[0.04] text-[10px] font-bold text-slate-400">
                    {String(cell.rank).padStart(2, '0')}
                  </span>

                  {/* CELL DETAILS */}
                  <div className="min-w-0 flex-1">

                    <div className="flex flex-wrap items-center gap-1.5">

                      <span className="text-[10px] font-semibold text-slate-200">
                        Cellule #{cell.cell_id}
                      </span>

                      <span className={`rounded px-1.5 py-0.5 text-[8px] uppercase ${
                        cell.classification === 'core'
                          ? 'bg-emerald-400/10 text-emerald-300'
                          : 'bg-amber-400/10 text-amber-300'
                      }`}>
                        {cell.classification}
                      </span>

                    </div>

                    <p className="mt-1 text-[9px] text-slate-500">
                      {Number(cell.latitude).toFixed(2)}° N ·{' '}
                      {Number(cell.longitude).toFixed(2)}° O
                    </p>

                    {/* SCORE */}
                    {activeTab === 'maai' && (
                      <div className="mt-2">

                        <div className="flex items-center justify-between">
                          <span className="text-[9px] text-slate-500">
                            Indice d'attention
                          </span>

                          <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${getScoreColor(score)}`}>
                            {formatScore(score)}
                          </span>
                        </div>

                        <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-800">
                          <div
                            className={`h-full rounded-full ${
                              score >= 85
                                ? 'bg-rose-400'
                                : score >= 70
                                  ? 'bg-amber-400'
                                  : 'bg-cyan-400'
                            }`}
                            style={{ width: `${Math.min(100, score)}%` }}
                          />
                        </div>

                        <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1">

                          <span className="text-[9px] text-slate-400">
                            AIS : {formatHours(cell.ais_hours)}
                          </span>

                          <span className="text-[9px] text-rose-300">
                            SAR− : {formatNumber(cell.sar_unmatched)}
                          </span>

                          <span className="text-[9px] text-cyan-300">
                            Évolution : {Number(cell.ais_relative_increase_percent ?? 0) > 0
                              ? `+${formatScore(cell.ais_relative_increase_percent)} %`
                              : `${formatScore(cell.ais_relative_increase_percent)} %`}
                          </span>

                          <span className="text-[9px] text-slate-500">
                            Baseline : {cell.baseline_months ?? 0} mois
                          </span>

                        </div>
                      </div>
                    )}

                    {/* AIS */}
                    {activeTab === 'ais' && (
                      <p className="mt-1.5 text-[9px] text-cyan-300">
                        {formatHours(cell.ais_hours)} heures AIS
                      </p>
                    )}

                    {/* SAR */}
                    {activeTab === 'sar' && (
                      <p className="mt-1.5 text-[9px] text-rose-300">
                        {formatNumber(cell.sar_unmatched)} détections non appariées
                      </p>
                    )}

                  </div>

                  {/* MAP ACTION */}
                  <MapPin
                    size={14}
                    className="mt-1 shrink-0 text-slate-600 transition group-hover:text-cyan-300"
                  />

                </div>

              </button>
            )
          })
        )}

      </div>

      {/* FOOTER */}
      <div className="border-t border-white/[0.06] px-3 py-2">

        <p className="text-[9px] leading-relaxed text-slate-500">
          {activeTab === 'maai'
  ? t('dashboard.maaiDescription')
  : activeTab === 'ais'
    ? t('dashboard.aisDescription')
    : t('dashboard.sarDescriptionRanking')}
        </p>

      </div>

    </section>
  )
}




export default function DashboardLayout({
  children,
  timeline,
  overview,
  ranking,
  rankingPeriod,
  selectedCell,
  onSelectCell,
  loading,
  error,
  onRefresh,
  vesselContacts,
selectedVessel,
onSelectVessel,
temporal,
temporalLoading,
temporalError,
}) {
    const { t } = useTranslation()
  const aisHours = Number(overview?.ais_hours ?? 0)
  const aisObservations = Number(overview?.ais_observations ?? 0)

  const sarMatched = Number(overview?.sar_matched_detections ?? 0)
  const sarUnmatched = Number(overview?.sar_unmatched_detections ?? 0)

  const sarTotal = Number(
    overview?.sar_total_detections ??
    sarMatched + sarUnmatched
  )

  const activeCells = Number(overview?.active_cells ?? 0)

  const unmatchedRate = Number(
    overview?.sar_unmatched_rate_percent ?? 0
  )

  const matchedRate = sarTotal > 0
    ? (sarMatched / sarTotal) * 100
    : 0

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#07111f] text-slate-200">

      <Header
        loading={loading}
        onRefresh={onRefresh}
      />

      <main className="mx-auto max-w-[2200px] p-3 sm:p-4 lg:p-5">

        {/* EN-TÊTE DU TABLEAU DE BORD */}
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">

          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              <p className="text-[9px] font-bold uppercase tracking-[0.22em] text-cyan-400">
                {t('dashboard.surveillance')}
              </p>
            </div>

            <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              {t('dashboard.title')}
            </h2>

            <p className="mt-1 text-[11px] text-slate-500">
              Analyse de la présence des navires et des détections satellitaires dans la ZEE sénégalaise.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-lg border border-white/[0.07] bg-[#0c1929] px-3 py-2 sm:flex">
              <CalendarDays size={14} className="text-cyan-400" />
              <div>
                <p className="text-[8px] uppercase tracking-wider text-slate-500">
                  {t('dashboard.coverage')}
                </p>
                <p className="mt-0.5 text-[10px] font-semibold text-slate-200">
                  Jan. 2024 — Oct. 2026
                </p>
              </div>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.07] px-3 py-2 text-[10px] font-semibold text-cyan-300 transition hover:bg-cyan-400/15 disabled:opacity-50"
            >
              <RefreshCw
                size={13}
                className={loading ? 'animate-spin' : ''}
              />
              {t('dashboard.refresh')}
            </button>
          </div>
        </div>

        {/* DISPOSITION PRINCIPALE : 75 / 25 */}
        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(300px,1fr)]">

          {/* COLONNE GAUCHE : CARTE + CHRONOLOGIE */}
          <div className="min-w-0 space-y-4">

            <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0b1827]">

              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3">

                <div className="flex items-center gap-2.5">
                  <div className="rounded-lg bg-cyan-400/10 p-2">
                    <Waves size={17} className="text-cyan-400" />
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-white">
                      {t('dashboard.mapTitle')}
                    </h3>
                    <p className="mt-0.5 text-[9px] text-slate-500">
                      AIS · SAR · Zone économique exclusive du Sénégal
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="rounded-md border border-white/[0.07] bg-white/[0.03] px-2 py-1 text-[9px] text-slate-400">
                    EPSG:4326
                  </span>

                  <span className="rounded-md border border-emerald-400/15 bg-emerald-400/[0.06] px-2 py-1 text-[9px] font-semibold text-emerald-300">
                    {t('dashboard.historical')}
                  </span>
                </div>
              </div>

              <div className="p-2 sm:p-3">
                {children}
              </div>
            </section>

            {timeline}
          </div>

          {/* COLONNE DROITE : INTELLIGENCE */}
          <aside className="min-w-0 space-y-3 xl:sticky xl:top-4">

            {/* TITRE DU PANNEAU */}
            <div className="flex items-center justify-between pb-1">
              <div>
                <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-cyan-400">
                  {t('dashboard.analysisCenter')}
                </p>

                <h3 className="mt-1 text-sm font-bold text-white">
                  {t('dashboard.situation')}
                </h3>
              </div>

              <div className="rounded-lg border border-cyan-400/10 bg-cyan-400/[0.05] p-2">
                <Radar size={19} className="text-cyan-400" />
              </div>
            </div>

            {error && (
              <div className="rounded-lg border border-orange-500/20 bg-orange-500/[0.06] p-3 text-[10px] text-orange-300">
                {error}
              </div>
            )}

            {/* INDICATEURS AIS / SAR */}
            <section>
              <SectionTitle icon={Activity}>
                {t('dashboard.keyIndicators')}
              </SectionTitle>

              <div className="grid grid-cols-2 gap-2">
                <Metric
                  label="Observations AIS"
                  value={formatNumber(aisObservations)}
                  icon={Radio}
                  color="text-cyan-400"
                  description="Observations agrégées"
                />

                <Metric
                  label="Heures de présence"
                  value={formatHours(aisHours)}
                  icon={Activity}
                  color="text-blue-400"
                  description="Heures cumulées"
                />

                <Metric
                  label="Détections SAR"
                  value={formatNumber(sarTotal)}
                  icon={Satellite}
                  color="text-orange-400"
                  description="Détections satellitaires"
                />

                <Metric
                  label="Cellules actives"
                  value={formatNumber(activeCells)}
                  icon={Anchor}
                  color="text-violet-400"
                  description="Cellules avec activité"
                />


                
              </div>
            </section>

            <VesselContactsPanel
  contacts={vesselContacts}
  selectedVessel={selectedVessel}
  onSelectVessel={onSelectVessel}
/>

            {/* ANALYSE SAR */}
            <section className="rounded-xl border border-white/[0.07] bg-[#0d1b2b] p-4">

              <SectionTitle icon={Satellite}>
                {t('dashboard.sarAnalysis')}
              </SectionTitle>
              <RankingPanel
  ranking={ranking}
  rankingPeriod={rankingPeriod}
  onSelectCell={onSelectCell}
/>

              <div className="space-y-4">

                <ProgressRow
                  label="Détections appariées"
                  value={sarMatched}
                  total={sarTotal}
                  color="bg-teal-400"
                />

                <ProgressRow
                  label="Détections non appariées"
                  value={sarUnmatched}
                  total={sarTotal}
                  color="bg-rose-400"
                />

              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 border-t border-white/[0.06] pt-3">

                <div>
                  <p className="text-[9px] text-slate-500">
                    Taux apparié
                  </p>
                  <p className="mt-1 text-lg font-bold text-teal-300">
                    {matchedRate.toFixed(2).replace('.', ',')}%
                  </p>
                </div>

                <div>
                  <p className="text-[9px] text-slate-500">
                    Taux non apparié
                  </p>
                  <p className="mt-1 text-lg font-bold text-rose-300">
                    {unmatchedRate.toFixed(2).replace('.', ',')}%
                  </p>
                </div>

              </div>
            </section>
                      {/* INTELLIGENCE TEMPORELLE */}
          <TemporalIntelligencePanel
  data={temporal}
  loading={temporalLoading}
  error={temporalError}
  selectedCell={selectedCell}
  onSelectCell={onSelectCell}
/>

          

            {/* LECTURE OPÉRATIONNELLE */}
            <section className="rounded-xl border border-cyan-400/10 bg-gradient-to-br from-cyan-400/[0.07] to-transparent p-4">

              <SectionTitle icon={TrendingUp}>
                {t('dashboard.reading')}
              </SectionTitle>

              <p className="text-[10px] leading-relaxed text-slate-400">
                Les données AIS permettent d'étudier la présence maritime déclarée.
                Les observations SAR apportent une source satellitaire complémentaire.
                Leur comparaison permet d'identifier les zones nécessitant une analyse approfondie.
              </p>

              <div className="mt-3 flex items-center gap-2 rounded-lg bg-white/[0.03] p-2.5">
                <CircleDot size={13} className="shrink-0 text-cyan-400" />
                <p className="text-[9px] leading-relaxed text-slate-400">
                  Les statistiques sont agrégées spatialement et temporellement.
                </p>
              </div>
            </section>

            {/* PRÉCAUTION SCIENTIFIQUE */}
            <section className="rounded-xl border border-amber-400/15 bg-amber-400/[0.04] p-4">

              <div className="flex items-center gap-2">
                <ShieldAlert size={15} className="text-amber-400" />
                <h4 className="text-[10px] font-bold text-amber-200">
                  {t('dashboard.caution')}
                </h4>
              </div>

              <p className="mt-2 text-[10px] leading-relaxed text-slate-400">
                Une détection SAR non appariée ne constitue pas une preuve
                d'activité illégale ou de désactivation volontaire de l'AIS.
                Une analyse complémentaire est nécessaire.
              </p>
            </section>

            {/* SOURCES */}
            <section className="rounded-xl border border-white/[0.07] bg-[#0d1b2b] p-4">

              <SectionTitle icon={Database}>
                {t('dashboard.sources')}
              </SectionTitle>

              <div className="space-y-3">

                <div className="flex items-center gap-3">
                  <Radio size={15} className="shrink-0 text-cyan-400" />
                  <div>
                    <p className="text-[10px] font-semibold text-slate-200">
                      Global Fishing Watch
                    </p>
                    <p className="text-[9px] text-slate-500">
                      AIS · Global presence v5.0
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Satellite size={15} className="shrink-0 text-orange-400" />
                  <div>
                    <p className="text-[10px] font-semibold text-slate-200">
                      Données satellitaires SAR
                    </p>
                    <p className="text-[9px] text-slate-500">
                      Détections appariées et non appariées
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Globe2 size={15} className="shrink-0 text-violet-400" />
                  <div>
                    <p className="text-[10px] font-semibold text-slate-200">
                      Marine Regions
                    </p>
                    <p className="text-[9px] text-slate-500">
                      World EEZ v12 · MRGID 8371
                    </p>
                  </div>
                </div>

              </div>
            </section>

            {/* MÉTADONNÉES */}
            <div className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-3">

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CalendarDays size={12} className="text-slate-500" />
                  <span className="text-[9px] text-slate-400">
                    Couverture : 34 mois
                  </span>
                </div>

                <span className="text-[9px] text-cyan-400">
                  2024 — 2026
                </span>
              </div>

              <div className="mt-3 flex items-center gap-2">
                <Database size={12} className="text-slate-600" />
                <p className="text-[9px] leading-relaxed text-slate-500">
                  Données historiques disponibles jusqu'en octobre 2026.
                  Ce tableau de bord ne constitue pas un flux de surveillance en temps réel.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between px-1 pb-2 text-[8px] tracking-wider text-slate-600">
              <span>THE INVISIBLE FLEET</span>
              <span>MARITIME INTELLIGENCE</span>
            </div>

          </aside>
        </div>
      </main>
    </div>
  )
}
