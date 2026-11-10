
import { lazy, Suspense, useCallback, useEffect, useState } from 'react'

const MaritimeMap = lazy(() =>
  import('./components/dashboard/MaritimeMap')
)

import DashboardLayout from './components/layout/DashboardLayout'
import TimelineChart from './components/dashboard/TimelineChart'

import {
  getOverview,
  getTimeline,
  getRanking,
  getTemporal,
} from './services/api'

function App() {
  const [overview, setOverview] = useState(null)
  const [timeline, setTimeline] = useState([])

  const [ranking, setRanking] = useState({
    rankings: {
      attention_index: [],
      ais_presence: [],
      sar_unmatched: [],
    },
  })

  const [temporal, setTemporal] = useState({
    monthly: [],
    cells: [],
    meta: {},
  })

  const [temporalLoading, setTemporalLoading] = useState(true)
  const [temporalError, setTemporalError] = useState('')

  const [period, setPeriod] = useState('2026-10')
  const [classification, setClassification] = useState('all')

  // Sélection centrale partagée entre carte et panneau.
  const [selectedCell, setSelectedCell] = useState(null)

  const [vesselContacts, setVesselContacts] = useState([])
  const [selectedVessel, setSelectedVessel] = useState(null)

  const [loading, setLoading] = useState(true)
  const [timelineLoading, setTimelineLoading] = useState(true)

  const [error, setError] = useState('')
  const [timelineError, setTimelineError] = useState('')

  const liveSelectedVessel = selectedVessel
    ? vesselContacts.find(
        vessel => vessel.id === selectedVessel.id
      ) ?? selectedVessel
    : null

  // Sélectionner une cellule depuis n'importe quel composant.
  const handleSelectCell = useCallback((cell) => {
    if (!cell?.cell_id) return

    setSelectedCell(cell)
  }, [])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setTimelineLoading(true)

    const [overviewResult, timelineResult] =
      await Promise.allSettled([
        getOverview({ classification: 'all' }),
        getTimeline(),
      ])

    if (overviewResult.status === 'fulfilled') {
      const data = overviewResult.value

      setOverview({
        ais_hours: data.ais?.presence_hours ?? 0,
        ais_observations: data.ais?.observation_count ?? 0,
        sar_total_detections: data.sar?.total_detections ?? 0,
        sar_matched_detections: data.sar?.matched_detections ?? 0,
        sar_unmatched_detections: data.sar?.unmatched_detections ?? 0,
        sar_unmatched_rate_percent:
          data.sar?.unmatched_rate_percent ?? 0,
        active_cells: data.spatial?.active_cells ?? 0,
        months_covered: data.spatial?.months_covered ?? 0,
      })

      setError('')
    } else {
      setOverview(null)
      setError('Impossible de récupérer les statistiques.')
    }

    setLoading(false)

    if (timelineResult.status === 'fulfilled') {
      const data = timelineResult.value
      const results = Array.isArray(data)
        ? data
        : data?.results ?? []

      setTimeline(results)
      setTimelineError(
        results.length === 0 ? 'Aucune donnée mensuelle.' : ''
      )
    } else {
      setTimeline([])
      setTimelineError(
        'Impossible de récupérer la chronologie.'
      )
    }

    setTimelineLoading(false)
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  // Classement mensuel.
  useEffect(() => {
    let cancelled = false

    async function loadRanking() {
      try {
        const data = await getRanking({
          period,
          classification,
          limit: 10,
        })

        if (cancelled) return

        setRanking({
          rankings: {
            attention_index: data.rankings?.attention_index ?? [],
            ais_presence: data.rankings?.ais_presence ?? [],
            sar_unmatched: data.rankings?.sar_unmatched ?? [],
          },
          meta: data.meta,
          filters: data.filters,
        })
      } catch (err) {
        console.error('Erreur ranking:', err)

        if (!cancelled) {
          setRanking({
            rankings: {
              attention_index: [],
              ais_presence: [],
              sar_unmatched: [],
            },
          })
        }
      }
    }

    loadRanking()

    return () => {
      cancelled = true
    }
  }, [period, classification])

  // Intelligence temporelle MAAI.
  useEffect(() => {
    let cancelled = false

    async function loadTemporal() {
      setTemporalLoading(true)
      setTemporalError('')

      try {
        const data = await getTemporal({
          start_period: '2025-01',
          end_period: '2026-10',
          classification,
          top_n: 10,
          limit: 20,
        })

        if (cancelled) return

        const nextTemporal = {
          monthly: data.monthly ?? [],
          cells: data.cells ?? [],
          meta: data.meta ?? {},
        }

        setTemporal(nextTemporal)

        // Si les filtres changent, conserver la sélection
        // seulement si la cellule existe encore dans les résultats.
        setSelectedCell(current => {
          if (!current) return null

          return (
            nextTemporal.cells.find(
              cell => cell.cell_id === current.cell_id
            ) ?? null
          )
        })
      } catch (err) {
        console.error('Erreur intelligence temporelle:', err)

        if (!cancelled) {
          setTemporal({
            monthly: [],
            cells: [],
            meta: {},
          })

          setTemporalError(
            "Impossible de charger l'analyse temporelle."
          )
        }
      } finally {
        if (!cancelled) {
          setTemporalLoading(false)
        }
      }
    }

    loadTemporal()

    return () => {
      cancelled = true
    }
  }, [classification])

  return (
    <DashboardLayout
  overview={overview}
  temporal={temporal}
  temporalLoading={temporalLoading}
  temporalError={temporalError}
  selectedCell={selectedCell} // AJOUT
  vesselContacts={vesselContacts}
  selectedVessel={liveSelectedVessel}
  onSelectVessel={setSelectedVessel}
  ranking={ranking}
  rankingPeriod={period}
  onSelectCell={setSelectedCell}
  loading={loading}
  error={error}
  onRefresh={loadDashboard}
  timeline={
    <TimelineChart
      data={timeline}
      loading={timelineLoading}
      error={timelineError}
    />
  }
>
      <Suspense
        fallback={
          <div className="flex min-h-[600px] items-center justify-center rounded-xl bg-[#07111f] text-sm text-slate-400">
            Chargement du système cartographique...
          </div>
        }
      >
        <MaritimeMap
  period={period}
  setPeriod={setPeriod}
  classification={classification}
  setClassification={setClassification}
  selectedCell={selectedCell}
  onSelectCell={setSelectedCell} // AJOUT
  ranking={ranking}
  temporal={temporal}
  onVesselsUpdate={setVesselContacts}
  selectedVessel={liveSelectedVessel}
/>
      </Suspense>
    </DashboardLayout>
  )
}

export default App
