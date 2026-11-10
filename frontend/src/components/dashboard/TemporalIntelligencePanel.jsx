/* eslint-disable no-unused-vars */

import { useMemo, useState} from 'react'
import {
  Activity,
  Clock3,
  TrendingUp,
  TrendingDown,
  Minus,
  MapPin,
  Waves,
  RefreshCw,
  AlertTriangle,
  ChevronRight,
  BarChart3,
} from 'lucide-react'

const numberFormat = new Intl.NumberFormat('fr-FR')
import { useTranslation } from 'react-i18next'
function formatNumber(value) {
  return numberFormat.format(Number(value ?? 0))
}

function formatScore(value) {
  return Number(value ?? 0).toFixed(1).replace('.', ',')
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(1).replace('.', ',')} %`
}

function getRecurrenceStyle(recurrence, t) {
  const styles = {
    persistent: {
      label: t('temporal.persistentLabel'),
      className: 'bg-rose-400/10 text-rose-300 border-rose-400/20',
    },
    recurring: {
      label: t('temporal.recurringLabel'),
      className: 'bg-amber-400/10 text-amber-300 border-amber-400/20',
    },
    occasional: {
      label: t('temporal.occasionalLabel'),
      className: 'bg-cyan-400/10 text-cyan-300 border-cyan-400/20',
    },
  }

  return styles[recurrence] ?? styles.occasional
}

function TrendIndicator({ trend }) {
    const { t } = useTranslation()
  if (trend === 'increasing') {
    return (
      <span className="flex items-center gap-1 text-rose-300">
        <TrendingUp size={12} />
        {t('temporal.rising')}
      </span>
    )
  }

  if (trend === 'decreasing') {
    return (
      <span className="flex items-center gap-1 text-teal-300">
        <TrendingDown size={12} />
        {t('temporal.falling')}
      </span>
    )
  }

  return (
    <span className="flex items-center gap-1 text-slate-400">
      <Minus size={12} />
      {t('temporal.stable')}
    </span>
  )
}

function Sparkline({ history = [] }) {
  const values = history.map(item => Number(item.score ?? 0))
    const { t } = useTranslation()
  if (values.length < 2) {
    return (
      <div className="flex h-20 items-center justify-center text-[10px] text-slate-500">
        {t('temporal.insufficientHistory')}
      </div>
    )
  }

  const width = 300
  const height = 80
  const padding = 8

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const points = values.map((value, index) => {
    const x = padding +
      (index / (values.length - 1)) * (width - padding * 2)

    const y = height - padding -
      ((value - min) / range) * (height - padding * 2)

    return { x, y }
  })

  const path = points
    .map((point, index) =>
      `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`
    )
    .join(' ')

  const areaPath = [
    path,
    `L ${points[points.length - 1].x} ${height}`,
    `L ${points[0].x} ${height}`,
    'Z',
  ].join(' ')

  return (
    <div className="mt-3">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-20 w-full overflow-visible"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient
            id="temporal-gradient"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
          </linearGradient>
        </defs>

        {[20, 40, 60].map(y => (
          <line
            key={y}
            x1="0"
            y1={y}
            x2={width}
            y2={y}
            stroke="rgba(148,163,184,0.12)"
            strokeDasharray="3 4"
          />
        ))}

        <path d={areaPath} fill="url(#temporal-gradient)" />

        <path
          d={path}
          fill="none"
          stroke="#22d3ee"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {points.map((point, index) => (
          index === points.length - 1 && (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r="3.5"
              fill="#22d3ee"
              stroke="#0d1b2b"
              strokeWidth="2"
            />
          )
        ))}
      </svg>

      <div className="flex justify-between text-[8px] text-slate-500">
        <span>{history[0]?.period}</span>
        <span>{history[history.length - 1]?.period}</span>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, description, color }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0d1b2b] p-3">
      <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className={`mt-2 text-xl font-bold ${color}`}>
        {value}
      </p>

      <p className="mt-1 text-[9px] text-slate-500">
        {description}
      </p>
    </div>
  )
}

export default function TemporalIntelligencePanel({
  data,
  loading,
  error,
  selectedCell: externalSelectedCell,
  onSelectCell,
}) {
  const [selectedId, setSelectedId] = useState(null)
const { t } = useTranslation()
  const cells = data?.cells ?? []
  const monthly = data?.monthly ?? []

const selectedCell = useMemo(() => {
  if (!externalSelectedCell) {
    return cells[0] ?? null
  }

  return (
    cells.find(
      cell => String(cell.cell_id) === String(externalSelectedCell.cell_id)
    ) ??
    externalSelectedCell
  )
}, [cells, externalSelectedCell])

  const statistics = useMemo(() => {
    return {
      persistent: cells.filter(
        cell => cell.recurrence === 'persistent'
      ).length,

      recurring: cells.filter(
        cell => cell.recurrence === 'recurring'
      ).length,

      occasional: cells.filter(
        cell => cell.recurrence === 'occasional'
      ).length,
    }
  }, [cells])

  const eligibleMonths = Number(data?.meta?.eligible_months ?? 0)

function selectCell(cell) {
  onSelectCell?.(cell)
}

  if (loading) {
    return (
      <section className="rounded-xl border border-white/[0.07] bg-[#0d1b2b] p-5">
        <div className="flex items-center gap-2 text-cyan-300">
          <RefreshCw size={15} className="animate-spin" />
          <span className="text-[10px] font-semibold">
            {t('temporal.calculating')}...
          </span>
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="rounded-xl border border-rose-400/15 bg-rose-400/[0.04] p-4">
        <div className="flex items-center gap-2 text-rose-300">
          <AlertTriangle size={15} />
          <span className="text-[10px] font-semibold">{error}</span>
        </div>
      </section>
    )
  }

  if (cells.length === 0) {
    return (
      <section className="rounded-xl border border-white/[0.07] bg-[#0d1b2b] p-4">
        <p className="text-center text-[10px] text-slate-500">
          {t('temporal.noData')}.
        </p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-xl border border-white/[0.07] bg-[#0d1b2b]">

      {/* HEADER */}
      <div className="border-b border-white/[0.06] p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-violet-400/10 p-2">
              <Activity size={16} className="text-violet-300" />
            </div>

            <div>
              <h3 className="text-[11px] font-bold text-white">
                {t('temporal.title')}
              </h3>

              <p className="mt-0.5 text-[9px] text-slate-500">
                {t('temporal.subtitle')}
              </p>
            </div>
          </div>

          <span className="rounded-md border border-violet-400/15 bg-violet-400/[0.06] px-2 py-1 text-[9px] text-violet-300">
            {t('temporal.history')}
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between text-[9px] text-slate-500">
          <span className="flex items-center gap-1">
            <Clock3 size={11} />
            Jan. 2025 — Oct. 2026
          </span>

          <span>{eligibleMonths} {t('temporal.exploitableMonths')}</span>
        </div>
      </div>

      {/* SUMMARY */}
      <div className="grid grid-cols-3 gap-2 p-3">
        <SummaryCard
          label="{t('temporal.persistent')}"
          value={statistics.persistent}
          description={t('temporal.months60')}
          color="text-rose-300"
        />

        <SummaryCard
          label="{t('temporal.recurring')}"
          value={statistics.recurring}
          description={t('temporal.months30')}
          color="text-amber-300"
        />

        <SummaryCard
          label="{t('temporal.occasional')}"
          value={statistics.occasional}
          description={t('temporal.monthsBelow30')}
          color="text-cyan-300"
        />
      </div>

      {/* RANKING */}
      <div className="border-t border-white/[0.06] p-3">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-300">
            <BarChart3 size={13} className="text-cyan-400" />
            {t('temporal.zones')}
          </h4>

          <span className="text-[9px] text-slate-500">
            {cells.length} {t('temporal.cells')}
          </span>
        </div>

        <div className="max-h-[330px] space-y-1 overflow-y-auto pr-1">
          {cells.map((cell, index) => {
            const active = selectedCell?.cell_id === cell.cell_id
            const style = getRecurrenceStyle(cell.recurrence, t)

            return (
              <button
                key={cell.cell_id}
                onClick={() => selectCell(cell)}
                className={`group w-full rounded-lg border p-2.5 text-left transition ${
                  active
                    ? 'border-cyan-400/30 bg-cyan-400/[0.07]'
                    : 'border-transparent hover:border-white/[0.07] hover:bg-white/[0.03]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/[0.05] text-[9px] font-bold text-slate-400">
                    {String(index + 1).padStart(2, '0')}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] font-semibold text-slate-200">
                        {t('temporal.cell')} #{cell.cell_id}
                      </span>

                      <span className={`rounded border px-1.5 py-0.5 text-[8px] ${style.className}`}>
                        {style.label}
                      </span>
                    </div>

                    <div className="mt-1.5 flex items-center gap-2 text-[9px] text-slate-500">
                      <span>
                        {cell.priority_months}/{cell.observed_months} {t('temporal.months')}
                      </span>

                      <span className="text-slate-700">·</span>

                      <span className="font-semibold text-cyan-300">
                        {formatPercent(cell.persistence_rate_percent)}
                      </span>
                    </div>

                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-cyan-400"
                        style={{
                          width: `${Math.min(100, cell.persistence_rate_percent)}%`,
                        }}
                      />
                    </div>
                  </div>

                  <ChevronRight
                    size={13}
                    className="shrink-0 text-slate-600 transition group-hover:text-cyan-300"
                  />
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* SELECTED CELL */}
      {selectedCell && (
        <div className="border-t border-white/[0.06] bg-[#091625] p-3">
          <div className="flex items-center justify-between">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-300">
              {t('temporal.cell')} #{selectedCell.cell_id}
            </h4>

            <button
              onClick={() => onSelectCell?.(selectedCell)}
              className="flex items-center gap-1 rounded-md border border-cyan-400/15 bg-cyan-400/[0.06] px-2 py-1.5 text-[9px] font-semibold text-cyan-300 transition hover:bg-cyan-400/15"
            >
              <MapPin size={11} />
              {t('temporal.viewMap')}
            </button>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white/[0.03] p-2">
              <p className="text-[8px] text-slate-500">
                {t('temporal.meanScore')}
              </p>
              <p className="mt-1 text-base font-bold text-cyan-300">
                {formatScore(selectedCell.mean_attention_index)}
              </p>
            </div>

            <div className="rounded-lg bg-white/[0.03] p-2">
              <p className="text-[8px] text-slate-500">
                {t('temporal.peakScore')}
              </p>
              <p className="mt-1 text-base font-bold text-amber-300">
                {formatScore(selectedCell.peak_attention_index)}
              </p>
            </div>

            <div className="rounded-lg bg-white/[0.03] p-2">
              <p className="text-[8px] text-slate-500">
                {t('temporal.coverage')}
              </p>
              <p className="mt-1 text-sm font-bold text-slate-200">
                {formatPercent(selectedCell.coverage_rate_percent)}
              </p>
            </div>

            <div className="rounded-lg bg-white/[0.03] p-2">
              <p className="text-[8px] text-slate-500">
                {t('temporal.scoreTrend')}
              </p>
              <div className="mt-1 text-sm font-bold">
                <TrendIndicator trend={selectedCell.trend} />
              </div>
            </div>
          </div>

          <div className="mt-4">
            <div className="flex items-center justify-between">
              <h5 className="text-[9px] font-semibold text-slate-300">
                {t('temporal.monthlyTrend')}
              </h5>

              <span className="text-[8px] text-slate-500">
                {selectedCell.monthly_history?.length ?? 0} {t('temporal.observations')}
              </span>
            </div>

            <Sparkline history={selectedCell.monthly_history ?? []} />
          </div>

          <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-400/10 bg-amber-400/[0.04] p-2">
            <Waves size={12} className="mt-0.5 shrink-0 text-amber-300" />

            <p className="text-[8px] leading-relaxed text-slate-400">
              {t('temporal.caution')}
            </p>
          </div>
        </div>
      )}

      {/* FOOTER */}
      <div className="border-t border-white/[0.06] px-3 py-2">
        <p className="text-[8px] leading-relaxed text-slate-500">
          {t('temporal.footer')}
        </p>
      </div>
    </section>
  )
}
