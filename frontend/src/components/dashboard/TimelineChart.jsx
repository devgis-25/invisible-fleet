
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

const numberFormat = new Intl.NumberFormat('fr-FR')

function formatNumber(value) {
  return numberFormat.format(Number(value || 0))
}

function formatPeriod(period) {
  if (!period) return ''

  const [year, month] = period.split('-')
  const date = new Date(Number(year), Number(month) - 1, 1)

  return date.toLocaleDateString('fr-FR', {
    month: 'short',
    year: '2-digit',
  })
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null

  const item = payload[0]?.payload

  return (
    <div className="min-w-[190px] rounded-xl border border-white/10 bg-[#101f31] p-3 shadow-2xl">
      <p className="mb-3 text-xs font-semibold text-white">
        {formatPeriod(label)}
      </p>

      <div className="space-y-2">
        <p className="flex justify-between gap-4 text-[11px] text-cyan-300">
          <span>Heures AIS</span>
          <strong>{formatNumber(item.ais_hours)}</strong>
        </p>

        <p className="flex justify-between gap-4 text-[11px] text-blue-300">
          <span>Observations AIS</span>
          <strong>{formatNumber(item.ais_observations)}</strong>
        </p>

        <p className="flex justify-between gap-4 text-[11px] text-orange-300">
          <span>Détections SAR</span>
          <strong>{formatNumber(item.sar_total)}</strong>
        </p>

        <p className="flex justify-between gap-4 text-[11px] text-emerald-300">
          <span>SAR appariées</span>
          <strong>{formatNumber(item.sar_matched)}</strong>
        </p>

        <p className="flex justify-between gap-4 text-[11px] text-rose-300">
          <span>SAR non appariées</span>
          <strong>{formatNumber(item.sar_unmatched)}</strong>
        </p>

        <p className="flex justify-between gap-4 border-t border-white/10 pt-2 text-[11px] text-slate-400">
          <span>Taux non apparié</span>
          <strong>
            {Number(item.sar_unmatched_rate_percent || 0)
              .toFixed(2)
              .replace('.', ',')}%
          </strong>
        </p>
      </div>
    </div>
  )
}

export default function TimelineChart({
  data,
  loading = false,
  error = null,
}) {
  const results = Array.isArray(data)
    ? data
    : data?.results || []

  const chartData = results.map((item) => ({
    ...item,
    period: item.period,
    ais_hours: Number(item.ais_hours || 0),
    ais_observations: Number(item.ais_observations || 0),
    sar_matched: Number(item.sar_matched || 0),
    sar_unmatched: Number(item.sar_unmatched || 0),
    sar_total: Number(
      item.sar_total ??
      (Number(item.sar_matched || 0) +
        Number(item.sar_unmatched || 0))
    ),
  }))

  return (
    <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0b1827]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400" />
            <h3 className="text-sm font-semibold text-white">
              Historical maritime activity
            </h3>
          </div>

          <p className="mt-1 text-[10px] text-slate-500">
            Évolution mensuelle des observations AIS et détections SAR
          </p>
        </div>

        <div className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 py-2">
          <p className="text-[9px] uppercase tracking-wider text-slate-500">
            Couverture historique
          </p>
          <p className="mt-1 text-xs font-semibold text-cyan-300">
            {chartData.length} mois · 2024–2026
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center text-xs text-slate-500">
          Chargement de la chronologie...
        </div>
      ) : error ? (
        <div className="p-6 text-xs text-orange-300">
          Impossible de charger la chronologie : {error}
        </div>
      ) : chartData.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
          <p className="text-sm font-medium text-slate-300">
            Aucune donnée chronologique
          </p>
          <p className="text-xs text-slate-500">
            L'API n'a retourné aucun résultat mensuel.
          </p>
        </div>
      ) : (
        <div className="space-y-8 p-4">
          {/* AIS activity */}
          <div>
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-cyan-300">
                AIS · Présence maritime
              </h4>
              <p className="mt-1 text-[10px] text-slate-500">
                Heures de présence cumulées par mois
              </p>
            </div>

            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="aisGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#22d3ee"
                        stopOpacity={0.28}
                      />
                      <stop
                        offset="95%"
                        stopColor="#22d3ee"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>

                  <CartesianGrid
                    stroke="#ffffff"
                    strokeOpacity={0.06}
                    vertical={false}
                  />

                  <XAxis
                    dataKey="period"
                    tickFormatter={formatPeriod}
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={3}
                  />

                  <YAxis
                    tickFormatter={(value) =>
                      value >= 1000
                        ? `${(value / 1000).toFixed(0)}k`
                        : value
                    }
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={45}
                  />

                  <Tooltip
                    content={<CustomTooltip />}
                    cursor={{ stroke: '#22d3ee', strokeOpacity: 0.3 }}
                  />

                  <Area
                    type="monotone"
                    dataKey="ais_hours"
                    name="Heures AIS"
                    stroke="#22d3ee"
                    strokeWidth={2}
                    fill="url(#aisGradient)"
                    activeDot={{ r: 5, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* SAR detections */}
          <div>
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-orange-300">
                SAR · Détections satellitaires
              </h4>
              <p className="mt-1 text-[10px] text-slate-500">
                Comparaison mensuelle des détections appariées et non appariées
              </p>
            </div>

            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    stroke="#ffffff"
                    strokeOpacity={0.06}
                    vertical={false}
                  />

                  <XAxis
                    dataKey="period"
                    tickFormatter={formatPeriod}
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={3}
                  />

                  <YAxis
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={45}
                  />

                  <Tooltip
                    content={<CustomTooltip />}
                    cursor={{ fill: '#ffffff', fillOpacity: 0.03 }}
                  />

                  <Legend
                    wrapperStyle={{
                      fontSize: '10px',
                      color: '#94a3b8',
                    }}
                  />

                  <Bar
                    dataKey="sar_matched"
                    name="Appariées"
                    stackId="sar"
                    fill="#22d3ee"
                    radius={[0, 0, 0, 0]}
                  />

                  <Bar
                    dataKey="sar_unmatched"
                    name="Non appariées"
                    stackId="sar"
                    fill="#fb923c"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <p className="border-t border-white/[0.06] pt-3 text-[10px] leading-relaxed text-slate-500">
            Les données représentent des agrégations mensuelles historiques.
            Une détection SAR non appariée ne constitue pas, à elle seule,
            une preuve d'activité illégale.
          </p>
        </div>
      )}
    </section>
  )
}
