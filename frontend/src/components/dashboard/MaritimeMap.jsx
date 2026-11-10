import { useEffect, useRef, useState } from 'react'
import { addMaritimeAnimations } from './MaritimeAnimations'
import {
  Map,
  NavigationControl,
  ScaleControl,
  Popup,
} from 'maplibre-gl'

import {
  getMaritimeCells,
  getMaritimeZone,
} from '../../services/api'

const SATELLITE_TILES =
  'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/{z}/{y}/{x}.jpg'

const OSM_TILES =
  'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

const MONTHS = []

for (let year = 2024; year <= 2026; year++) {
  const lastMonth = year === 2026 ? 10 : 12

  for (let month = 1; month <= lastMonth; month++) {
    MONTHS.push(
      `${year}-${String(month).padStart(2, '0')}`,
    )
  }
}

const EMPTY_GEOJSON = {
  type: 'FeatureCollection',
  features: [],
}

function getGeoJSONBounds(geojson) {
  const coordinates = []

  function extract(coords) {
    if (
      typeof coords[0] === 'number' &&
      typeof coords[1] === 'number'
    ) {
      coordinates.push(coords)
      return
    }

    coords.forEach(extract)
  }

  const geometry = geojson.type === 'Feature'
    ? geojson.geometry
    : geojson

  if (!geometry?.coordinates) {
    throw new Error('Géométrie GeoJSON invalide.')
  }

  extract(geometry.coordinates)

  if (!coordinates.length) {
    throw new Error('Aucune coordonnée disponible.')
  }

  const longitudes = coordinates.map(point => point[0])
  const latitudes = coordinates.map(point => point[1])

  return [
    [
      Math.min(...longitudes),
      Math.min(...latitudes),
    ],
    [
      Math.max(...longitudes),
      Math.max(...latitudes),
    ],
  ]
}

function formatNumber(value) {
  return new Intl.NumberFormat('fr-FR').format(value ?? 0)
}

function createPopupContent(properties) {
  const container = document.createElement('div')

  container.style.minWidth = '235px'
  container.style.color = '#0f172a'
  container.style.fontFamily = 'Arial, sans-serif'

  const title = document.createElement('h3')
  title.textContent = `Cellule maritime ${properties.cell_id ?? 'non identifiée'}`

  title.style.fontWeight = '700'
  title.style.fontSize = '14px'
  title.style.marginBottom = '10px'

  container.appendChild(title)

const rows = [
  ...(properties.attention_index != null
    ? [
        ['Rang MAAI', `#${properties.rank}`],
        ['Score MAAI', `${properties.attention_index}/100`],
      ]
    : []),

  ['Classification', properties.classification],
  ['Recouvrement ZEE', `${properties.overlap_percentage ?? 0}%`],
  ['Heures AIS', formatNumber(properties.ais_hours)],
  ['Observations AIS', formatNumber(properties.ais_observations)],
  ['Pavillons actifs', formatNumber(properties.ais_flag_count)],
  ['SAR appariées', formatNumber(properties.sar_matched)],
  ['SAR non appariées', formatNumber(properties.sar_unmatched)],
  ['Total détections SAR', formatNumber(properties.sar_total)],
  [
    'Taux SAR non appariées',
    `${properties.sar_unmatched_rate_percent ?? 0}%`,
  ],

  ...(properties.attention_index != null
    ? [
        [
          'Augmentation AIS',
          `${properties.ais_relative_increase_percent ?? 0}%`,
        ],
        [
          'Médiane historique AIS',
          formatNumber(properties.ais_historical_median),
        ],
        ['Historique disponible', `${properties.baseline_months} mois`],
      ]
    : []),
]

  rows.forEach(([label, value]) => {
    const row = document.createElement('div')

    row.style.display = 'flex'
    row.style.justifyContent = 'space-between'
    row.style.gap = '15px'
    row.style.padding = '5px 0'
    row.style.borderBottom = '1px solid #e2e8f0'
    row.style.fontSize = '12px'

    const name = document.createElement('span')
    name.textContent = label

    const content = document.createElement('strong')
    content.textContent = value ?? '—'

    row.append(name, content)
    container.appendChild(row)
  })

  const note = document.createElement('p')

  note.textContent =
    "Position représentative du centre de la cellule, et non position exacte d'un navire."

  note.style.fontSize = '10px'
  note.style.lineHeight = '1.5'
  note.style.marginTop = '10px'
  note.style.color = '#64748b'

  container.appendChild(note)
if (properties.attention_index != null) {
  const disclaimer = document.createElement('p')

  disclaimer.textContent =
    "Le MAAI est un indice exploratoire de priorisation analytique. Un score élevé ne constitue pas une preuve d'activité illégale."

  disclaimer.style.fontSize = '10px'
  disclaimer.style.lineHeight = '1.5'
  disclaimer.style.marginTop = '10px'
  disclaimer.style.color = '#be123c'

  container.appendChild(disclaimer)
}
  return container
}


function createTemporalPopupContent(properties) {
  const container = document.createElement('div')

  container.style.minWidth = '245px'
  container.style.color = '#0f172a'
  container.style.fontFamily = 'Arial, sans-serif'

  const title = document.createElement('h3')
  title.textContent = `Cellule maritime ${properties.cell_id}`

  title.style.fontWeight = '700'
  title.style.fontSize = '14px'
  title.style.marginBottom = '10px'

  container.appendChild(title)

  const recurrenceLabels = {
    persistent: 'Persistante',
    recurring: 'Récurrente',
    occasional: 'Occasionnelle',
  }

  const trendLabels = {
    increasing: 'En augmentation',
    decreasing: 'En diminution',
    stable: 'Stable',
  }

  const rows = [
    [
      'Récurrence',
      recurrenceLabels[properties.recurrence] ?? 'Non classée',
    ],
    [
      'Mois prioritaires',
      `${properties.priority_months ?? 0}`,
    ],
    [
      'Mois observés',
      `${properties.observed_months ?? 0}`,
    ],
    [
      'Mois éligibles',
      `${properties.eligible_months ?? 0}`,
    ],
    [
      'Persistance',
      `${properties.persistence_rate_percent ?? 0}%`,
    ],
    [
      'Couverture historique',
      `${properties.coverage_rate_percent ?? 0}%`,
    ],
    [
      'Score MAAI moyen',
      `${properties.mean_attention_index ?? 0}/100`,
    ],
    [
      'Score MAAI maximal',
      `${properties.peak_attention_index ?? 0}/100`,
    ],
    [
      'Évolution première/dernière observation',
      trendLabels[properties.trend] ?? 'Non déterminée',
    ],
  ]

  rows.forEach(([label, value]) => {
    const row = document.createElement('div')

    row.style.display = 'flex'
    row.style.justifyContent = 'space-between'
    row.style.alignItems = 'flex-start'
    row.style.gap = '12px'
    row.style.padding = '6px 0'
    row.style.borderBottom = '1px solid #e2e8f0'
    row.style.fontSize = '11px'

    const name = document.createElement('span')
    name.textContent = label
    name.style.color = '#64748b'

    const content = document.createElement('strong')
    content.textContent = value
    content.style.textAlign = 'right'

    row.append(name, content)
    container.appendChild(row)
  })

  const note = document.createElement('p')

  note.textContent =
    "La récurrence indique la fréquence à laquelle une cellule apparaît parmi les cellules prioritaires pendant les mois observés. Elle ne démontre pas une activité illégale."

  note.style.fontSize = '10px'
  note.style.lineHeight = '1.5'
  note.style.marginTop = '10px'
  note.style.color = '#64748b'

  container.appendChild(note)

  return container
}
export default function MaritimeMap({
  selectedCell,
  ranking,
  period,
  setPeriod,
  temporal,
  classification,
  setClassification,
  onVesselsUpdate,
  selectedVessel,
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
const zoneGeometryRef = useRef(null)
  const [mapReady, setMapReady] = useState(false)

//   const [period, setPeriod] = useState('2026-10')
// const [classification, setClassification] = useState('all')
  const [baseMap, setBaseMap] = useState('satellite')
const [showAIS, setShowAIS] = useState(true)
const [showMAAI, setShowMAAI] = useState(true)
const [showSARMatched, setShowSARMatched] = useState(true)
const [showSARUnmatched, setShowSARUnmatched] = useState(true)
const [showTemporal, setShowTemporal] = useState(false)
  const [loading, setLoading] = useState(false)
  const [cellCount, setCellCount] = useState(0)
  const [error, setError] = useState('')

  // --------------------------------------------------
  // INITIALISATION DE LA CARTE
  // --------------------------------------------------

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new Map({
      container: containerRef.current,

      style: {
        version: 8,

        sources: {
          satellite: {
            type: 'raster',
            tiles: [SATELLITE_TILES],
            tileSize: 256,
            maxzoom: 21,
            attribution:
              '© EOX IT Services GmbH · Contains modified Copernicus Sentinel data (2025)',
          },

          osm: {
            type: 'raster',
            tiles: [OSM_TILES],
            tileSize: 256,
            maxzoom: 19,
            attribution: '© OpenStreetMap contributors',
          },
        },

        layers: [
          {
            id: 'satellite-base',
            type: 'raster',
            source: 'satellite',
            layout: {
              visibility: 'visible',
            },
            paint: {
              'raster-opacity': 1,
              'raster-fade-duration': 300,
            },
          },

          {
            id: 'osm-base',
            type: 'raster',
            source: 'osm',
            layout: {
              visibility: 'none',
            },
            paint: {
              'raster-opacity': 1,
              'raster-fade-duration': 300,
            },
          },
        ],
      },

      center: [-17.5, 14.5],
      zoom: 5,
      minZoom: 3,
      maxZoom: 16,

      attributionControl: {
        compact: true,
      },
    })

    mapRef.current = map
    let stopAnimations = null

    requestAnimationFrame(() => {
  map.resize()
})



    map.addControl(
      new NavigationControl({
        visualizePitch: true,
      }),
      'top-right',
    )

    map.addControl(
      new ScaleControl({
        maxWidth: 120,
        unit: 'metric',
      }),
      'bottom-left',
    )

    map.on('load', () => {
      // ----------------------------------------------
      // SOURCE ZEE
      // ----------------------------------------------

      map.addSource('senegal-eez', {
        type: 'geojson',
        data: EMPTY_GEOJSON,
      })

      // Remplissage léger de la ZEE
      map.addLayer({
        id: 'eez-fill',
        type: 'fill',
        source: 'senegal-eez',
        paint: {
          'fill-color': '#06b6d4',
          'fill-opacity': 0.09,
        },
      })

      // Halo lumineux du contour
      map.addLayer({
        id: 'eez-glow',
        type: 'line',
        source: 'senegal-eez',
        paint: {
          'line-color': '#22d3ee',
          'line-width': 7,
          'line-blur': 5,
          'line-opacity': 0.55,
        },
      })

      // Contour principal
      map.addLayer({
        id: 'eez-outline',
        type: 'line',
        source: 'senegal-eez',
        paint: {
          'line-color': '#67e8f9',
          'line-width': 2,
          'line-opacity': 1,
        },
      })

stopAnimations = addMaritimeAnimations(map, {
  onVesselsUpdate,
  getZoneGeometry: () => zoneGeometryRef.current,
})

// Source du navire sélectionné
map.addSource('selected-vessel-highlight', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: [],
  },
})

// Halo extérieur
map.addLayer({
  id: 'selected-vessel-halo',
  type: 'circle',
  source: 'selected-vessel-highlight',
  paint: {
    'circle-radius': 19,
    'circle-color': '#00e5ff',
    'circle-opacity': 0.15,
    'circle-stroke-color': '#00e5ff',
    'circle-stroke-width': 2,
    'circle-stroke-opacity': 0.9,
  },
})

// Centre du marqueur
map.addLayer({
  id: 'selected-vessel-center',
  type: 'circle',
  source: 'selected-vessel-highlight',
  paint: {
    'circle-radius': 5,
    'circle-color': '#ffffff',
    'circle-stroke-color': '#00e5ff',
    'circle-stroke-width': 2,
  },
})

      // ----------------------------------------------
      // SOURCE CELLULES MARITIMES
      // ----------------------------------------------

      map.addSource('maritime-cells', {
        type: 'geojson',
        data: EMPTY_GEOJSON,
      })
      map.addSource('selected-maritime-cell', {
  type: 'geojson',
  data: EMPTY_GEOJSON,
})

// Cellules prioritaires selon le MAAI
map.addSource('maai-cells', {
  type: 'geojson',
  data: EMPTY_GEOJSON,
})
// Cellules présentant une récurrence temporelle
map.addSource('temporal-cells', {
  type: 'geojson',
  data: EMPTY_GEOJSON,
})
// ----------------------------------------------
// INTERACTION AVEC LES CELLULES TEMPORELLES
// ----------------------------------------------

// map.on('click', 'temporal-cells-fill', (event) => {
//   const feature = event.features?.[0]

//   if (!feature) return

//   new Popup({
//     closeButton: true,
//     closeOnClick: true,
//     maxWidth: '350px',
//     offset: 12,
//   })
//     .setLngLat(event.lngLat)
//     .setDOMContent(
//       createTemporalPopupContent(feature.properties)
//     )
//     .addTo(map)
// })

// map.on('mouseenter', 'temporal-cells-fill', () => {
//   map.getCanvas().style.cursor = 'pointer'
// })

// map.on('mouseleave', 'temporal-cells-fill', () => {
//   map.getCanvas().style.cursor = ''
// })
      
      // ----------------------------------------------
      // VISUALISATION DES CELLULES MARITIMES
      // ----------------------------------------------

      // Intensité AIS : plus la présence est importante,
      // plus la cellule devient lumineuse et chaude.
      const aisIntensityColor = [
        'interpolate',
        ['linear'],
        ['coalesce', ['get', 'ais_hours'], 0],

        0, '#10283d',
        10, '#164e63',
        100, '#0e7490',
        1000, '#06b6d4',
        5000, '#38bdf8',
        20000, '#facc15',
        50000, '#fb923c',
        150000, '#ef4444',
      ]

      // Couleurs de classification
      const classificationColor = [
        'match',
        ['get', 'classification'],
        'core', '#22d3ee',
        'boundary', '#f59e0b',
        'outside', '#94a3b8',
        '#64748b',
      ]

      // ----------------------------------------------
      // 1. COUCHE PRINCIPALE : INTENSITÉ AIS
      // ----------------------------------------------

      map.addLayer({
        id: 'maritime-cells-fill',
        type: 'fill',
        source: 'maritime-cells',
        paint: {
          'fill-color': aisIntensityColor,
          'fill-opacity': [
            'interpolate',
            ['linear'],
            ['coalesce', ['get', 'ais_hours'], 0],
            0, 0.18,
            100, 0.38,
            1000, 0.52,
            10000, 0.68,
            50000, 0.78,
            150000, 0.85,
          ],
        },
      })

      // ----------------------------------------------
      // 2. CONTOURS DES CELLULES
      // ----------------------------------------------

      map.addLayer({
        id: 'maritime-cells-outline',
        type: 'line',
        source: 'maritime-cells',
        paint: {
          'line-color': classificationColor,
          'line-width': [
            'interpolate',
            ['linear'],
            ['zoom'],
            4, 0.25,
            6, 0.55,
            9, 0.9,
          ],
          'line-opacity': 0.65,
        },
      })

      // ----------------------------------------------
      // 3. SAR : DÉTECTIONS APPARIÉES
      // ----------------------------------------------

      map.addLayer({
        id: 'maritime-sar-matched',
        type: 'line',
        source: 'maritime-cells',
        filter: [
          '>',
          ['coalesce', ['get', 'sar_matched'], 0],
          0,
        ],
        paint: {
          'line-color': '#2dd4bf',
          'line-width': [
            'interpolate',
            ['linear'],
            ['coalesce', ['get', 'sar_matched'], 0],
            1, 0.8,
            10, 1.4,
            50, 2.2,
            100, 3,
          ],
          'line-opacity': 0.95,
        },
      })

      // ----------------------------------------------
      // 4. SAR : DÉTECTIONS NON APPARIÉES
      // ----------------------------------------------

      map.addLayer({
        id: 'maritime-sar-unmatched',
        type: 'line',
        source: 'maritime-cells',
        filter: [
          '>',
          ['coalesce', ['get', 'sar_unmatched'], 0],
          0,
        ],
        paint: {
          'line-color': '#fb7185',
          'line-width': [
            'interpolate',
            ['linear'],
            ['coalesce', ['get', 'sar_unmatched'], 0],
            1, 1,
            10, 1.6,
            50, 2.4,
            100, 3.2,
          ],
          'line-opacity': 1,
        },
      })

      // ----------------------------------------------
// COUCHE MAAI : CELLULES À FORTE PRIORITÉ
// ----------------------------------------------

map.addLayer({
  id: 'maai-cells-fill',
  type: 'fill',
  source: 'maai-cells',
  paint: {
    'fill-color': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'attention_index'], 0],
      0, '#164e63',
      40, '#0891b2',
      60, '#facc15',
      75, '#fb923c',
      85, '#f43f5e',
      95, '#be123c',
      100, '#881337',
    ],
    'fill-opacity': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'attention_index'], 0],
      0, 0.10,
      60, 0.25,
      75, 0.38,
      90, 0.52,
      100, 0.65,
    ],
  },
})
// Halo lumineux des cellules prioritaires
map.addLayer({
  id: 'maai-cells-glow',
  type: 'line',
  source: 'maai-cells',
  paint: {
    'line-color': [
      'interpolate',
      ['linear'],
      ['get', 'attention_index'],
      60, '#facc15',
      75, '#fb923c',
      85, '#f43f5e',
      100, '#be123c',
    ],
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 7,
      7, 11,
      10, 15,
    ],
    'line-blur': 5,
    'line-opacity': 0.55,
  },
})
map.addLayer({
  id: 'maai-cells-outline',
  type: 'line',
  source: 'maai-cells',
  paint: {
    'line-color': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'attention_index'], 0],
      0, '#164e63',
      60, '#facc15',
      75, '#fb923c',
      85, '#f43f5e',
      100, '#881337',
    ],
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 1,
      7, 2,
      10, 3,
    ],
    'line-opacity': 0.95,
  },
})

// Rang des cellules prioritaires
map.addLayer({
  id: 'maai-cells-labels',
  type: 'symbol',
  source: 'maai-cells',
  layout: {
    'text-field': [
      'concat',
      '#',
      ['to-string', ['get', 'rank']],
    ],
    'text-size': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 9,
      7, 12,
      10, 14,
    ],
    'text-font': [
      'Open Sans Bold',
      'Arial Unicode MS Bold',
    ],
    'text-allow-overlap': true,
    'text-ignore-placement': true,
  },
  paint: {
    'text-color': '#ffffff',
    'text-halo-color': '#450a0a',
    'text-halo-width': 2,
    'text-halo-blur': 1,
  },
})

// ----------------------------------------------
// INTELLIGENCE TEMPORELLE : RÉCURRENCE
// ----------------------------------------------

const recurrenceColor = [
  'match',
  ['get', 'recurrence'],
  'persistent', '#e879f9',
  'recurring', '#fbbf24',
  'occasional', '#22d3ee',
  '#64748b',
]

// Remplissage des cellules récurrentes
map.addLayer({
  id: 'temporal-cells-fill',
  type: 'fill',
  source: 'temporal-cells',
  paint: {
    'fill-color': recurrenceColor,
    'fill-opacity': [
      'interpolate',
      ['linear'],
      ['coalesce', ['get', 'persistence_rate_percent'], 0],
      0, 0.08,
      20, 0.18,
      40, 0.30,
      60, 0.42,
      100, 0.55,
    ],
  },
})

// Halo des cellules récurrentes
map.addLayer({
  id: 'temporal-cells-glow',
  type: 'line',
  source: 'temporal-cells',
  paint: {
    'line-color': recurrenceColor,
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 4,
      7, 7,
      10, 10,
    ],
    'line-blur': 4,
    'line-opacity': 0.55,
  },
})

// Contour principal
map.addLayer({
  id: 'temporal-cells-outline',
  type: 'line',
  source: 'temporal-cells',
  paint: {
    'line-color': recurrenceColor,
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 1,
      7, 2,
      10, 3,
    ],
    'line-opacity': 1,
  },
})

// Numéro de cellule
map.addLayer({
  id: 'temporal-cells-labels',
  type: 'symbol',
  source: 'temporal-cells',
  layout: {
    'text-field': [
      'to-string',
      ['get', 'cell_id'],
    ],
    'text-size': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 8,
      7, 10,
      10, 12,
    ],
    'text-font': [
      'Open Sans Bold',
      'Arial Unicode MS Bold',
    ],
    'text-allow-overlap': false,
  },
  paint: {
    'text-color': '#ffffff',
    'text-halo-color': '#0f172a',
    'text-halo-width': 2,
  },
})

// ----------------------------------------------
// INTERACTIONS AVEC LES CELLULES TEMPORELLES
// ----------------------------------------------

map.on('click', 'temporal-cells-fill', (event) => {
  const feature = event.features?.[0]

  if (!feature) return

  new Popup({
    closeButton: true,
    closeOnClick: true,
    maxWidth: '350px',
    offset: 12,
  })
    .setLngLat(event.lngLat)
    .setDOMContent(
      createTemporalPopupContent(feature.properties)
    )
    .addTo(map)
})

map.on('mouseenter', 'temporal-cells-fill', () => {
  map.getCanvas().style.cursor = 'pointer'
})

map.on('mouseleave', 'temporal-cells-fill', () => {
  map.getCanvas().style.cursor = ''
})
// ----------------------------------------------
// 5. CELLULE SÉLECTIONNÉE : HIGHLIGHT
// ----------------------------------------------

map.addLayer({
  id: 'selected-cell-fill',
  type: 'fill',
  source: 'selected-maritime-cell',
  paint: {
    'fill-color': '#ffffff',
    'fill-opacity': 0.12,
  },
})

map.addLayer({
  id: 'selected-cell-outline',
  type: 'line',
  source: 'selected-maritime-cell',
  paint: {
    'line-color': '#ffffff',
    'line-width': [
      'interpolate',
      ['linear'],
      ['zoom'],
      4, 1.5,
      7, 3,
      10, 4,
    ],
    'line-opacity': 1,
  },
})
      // ----------------------------------------------
      // 5. INTERACTIONS
      // ----------------------------------------------

      map.on('click', 'maritime-cells-fill', (event) => {
        const feature = event.features?.[0]

        if (!feature) return

        new Popup({
          closeButton: true,
          closeOnClick: true,
          maxWidth: '340px',
          offset: 12,
        })
          .setLngLat(event.lngLat)
          .setDOMContent(
            createPopupContent(feature.properties),
          )
          .addTo(map)
      })
// Clic sur une cellule prioritaire MAAI
map.on('click', 'maai-cells-fill', (event) => {
  const feature = event.features?.[0]

  if (!feature) return

  new Popup({
    closeButton: true,
    closeOnClick: true,
    maxWidth: '340px',
    offset: 12,
  })
    .setLngLat(event.lngLat)
    .setDOMContent(
      createPopupContent(feature.properties)
    )
    .addTo(map)
})

map.on('mouseenter', 'maai-cells-fill', () => {
  map.getCanvas().style.cursor = 'pointer'
})

map.on('mouseleave', 'maai-cells-fill', () => {
  map.getCanvas().style.cursor = ''
})
      map.on('mouseenter', 'maritime-cells-fill', () => {
        map.getCanvas().style.cursor = 'pointer'
      })

      map.on('mouseleave', 'maritime-cells-fill', () => {
        map.getCanvas().style.cursor = ''
      })


      setMapReady(true)
    })

    map.on('error', (event) => {
      console.error('Erreur MapLibre :', event.error)

      if (event.error?.message) {
        setError(event.error.message)
      }
    })

    return () => {
  stopAnimations?.()
  map.remove()
  mapRef.current = null
  setMapReady(false)
}
  }, [])

// useEffect(() => {
//   if (!mapReady || !mapRef.current) return

//   const map = mapRef.current
//   const source = map.getSource('selected-vessel-highlight')

//   if (!source) return

//   if (!selectedVessel?.coordinates) {
//     source.setData({
//       type: 'FeatureCollection',
//       features: [],
//     })
//     return
//   }

//   const coordinates = selectedVessel.coordinates

//   source.setData({
//     type: 'FeatureCollection',
//     features: [
//       {
//         type: 'Feature',
//         properties: {
//           id: selectedVessel.id,
//         },
//         geometry: {
//           type: 'Point',
//           coordinates,
//         },
//       },
//     ],
//   })

//   map.flyTo({
//     center: coordinates,
//     zoom: Math.max(map.getZoom(), 7),
//     speed: 0.8,
//     curve: 1.4,
//     essential: true,
//   })
// }, [selectedVessel?.id, mapReady])
//   useEffect(() => {
//   if (!selectedVessel || !mapReady || !mapRef.current) return

//   mapRef.current.flyTo({
//     center: selectedVessel.coordinates,
//     zoom: Math.max(mapRef.current.getZoom(), 7),
//     speed: 0.8,
//     curve: 1.4,
//     essential: true,
//   })
// }, [selectedVessel, mapReady])
  // --------------------------------------------------
  // CHANGEMENT DU FOND CARTOGRAPHIQUE
  // --------------------------------------------------

  useEffect(() => {
    if (!mapReady || !mapRef.current) return

    const map = mapRef.current

    map.setLayoutProperty(
      'satellite-base',
      'visibility',
      baseMap === 'satellite' ? 'visible' : 'none',
    )

    map.setLayoutProperty(
      'osm-base',
      'visibility',
      baseMap === 'osm' ? 'visible' : 'none',
    )
  }, [baseMap, mapReady])

  // --------------------------------------------------
  // CHARGEMENT DE LA ZEE
  // --------------------------------------------------
// --------------------------------------------------
// SYNCHRONISATION DU NAVIRE SÉLECTIONNÉ
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current
  const source = map.getSource('selected-vessel-highlight')

  if (!source) return

  const coordinates = selectedVessel?.coordinates

  if (
    !Array.isArray(coordinates) ||
    coordinates.length < 2 ||
    !Number.isFinite(Number(coordinates[0])) ||
    !Number.isFinite(Number(coordinates[1]))
  ) {
    source.setData(EMPTY_GEOJSON)
    return
  }

  const longitude = Number(coordinates[0])
  const latitude = Number(coordinates[1])

  source.setData({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {
          id: selectedVessel.id,
        },
        geometry: {
          type: 'Point',
          coordinates: [longitude, latitude],
        },
      },
    ],
  })

  map.flyTo({
    center: [longitude, latitude],
    zoom: Math.max(map.getZoom(), 7),
    speed: 0.8,
    curve: 1.4,
    essential: true,
  })
}, [
  selectedVessel?.id,
  selectedVessel?.coordinates?.[0],
  selectedVessel?.coordinates?.[1],
  mapReady,
])
  useEffect(() => {
    if (!mapReady) return

    let cancelled = false

    async function loadZone() {
      try {
        const zone = await getMaritimeZone()
        zoneGeometryRef.current = zone

        if (cancelled) return

        const source = mapRef.current?.getSource('senegal-eez')

        if (source) {
  source.setData(zone)

  const bounds = getGeoJSONBounds(zone)

  mapRef.current?.fitBounds(bounds, {
    padding: {
      top: 90,
      bottom: 80,
      left: 80,
      right: 80,
    },
    maxZoom: 6,
    duration: 1200,
  })
}
      } catch (err) {
        console.error('Erreur chargement ZEE :', err)

        if (!cancelled) {
          setError(
            'Impossible de charger la géométrie de la ZEE.',
          )
        }
      }
    }

    loadZone()

    return () => {
      cancelled = true
    }
  }, [mapReady])

  // --------------------------------------------------
  // CHARGEMENT DES CELLULES AIS / SAR
  // --------------------------------------------------

  useEffect(() => {
    if (!mapReady) return

    let cancelled = false

    async function loadCells() {
      setLoading(true)
      setError('')

      try {
        const data = await getMaritimeCells({
          period,
          classification,
        })

        if (cancelled) return

        const source = mapRef.current?.getSource('maritime-cells')

        if (source) {
          source.setData(data)
        }

        setCellCount(data.features?.length ?? 0)
      } catch (err) {
        console.error('Erreur chargement cellules :', err)

        if (!cancelled) {
          setError(
            'Impossible de charger les données maritimes.',
          )
          setCellCount(0)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadCells()

    return () => {
      cancelled = true
    }
  }, [mapReady, period, classification])
// --------------------------------------------------
// VISIBILITÉ DE LA COUCHE MAAI
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current

  const layers = [
    'maai-cells-fill',
    'maai-cells-glow',
    'maai-cells-outline',
    'maai-cells-labels',
  ]

  layers.forEach((layerId) => {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(
        layerId,
        'visibility',
        showMAAI ? 'visible' : 'none'
      )
    }
  })
}, [showMAAI, mapReady])

// --------------------------------------------------
// VISIBILITÉ DE LA COUCHE TEMPORELLE
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current

  const layers = [
    'temporal-cells-fill',
    'temporal-cells-glow',
    'temporal-cells-outline',
    'temporal-cells-labels',
  ]

  layers.forEach(layerId => {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(
        layerId,
        'visibility',
        showTemporal ? 'visible' : 'none'
      )
    }
  })
}, [showTemporal, mapReady])
  // --------------------------------------------------
  // INTERFACE
  // --------------------------------------------------
// --------------------------------------------------
// SÉLECTION DEPUIS LE CLASSEMENT
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current || !selectedCell) {
    return
  }

  const map = mapRef.current

  if (
  selectedCell.longitude == null ||
  selectedCell.latitude == null ||
  selectedCell.longitude === '' ||
  selectedCell.latitude === ''
) {
  return
}

const longitude = Number(selectedCell.longitude)
const latitude = Number(selectedCell.latitude)

  if (
    !Number.isFinite(longitude) ||
    !Number.isFinite(latitude)
  ) {
    return
  }

  const source = map.getSource('selected-maritime-cell')

  if (!source) return

  const halfSize = 0.05

  source.setData({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {
          cell_id: selectedCell.cell_id,
        },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [longitude - halfSize, latitude - halfSize],
            [longitude + halfSize, latitude - halfSize],
            [longitude + halfSize, latitude + halfSize],
            [longitude - halfSize, latitude + halfSize],
            [longitude - halfSize, latitude - halfSize],
          ]],
        },
      },
    ],
  })

  map.flyTo({
    center: [longitude, latitude],
    zoom: 8,
    duration: 1400,
    essential: true,
  })
}, [selectedCell, mapReady])


// Synchronisation du navire sélectionné
// ----------------------------------------------
// SYNCHRONISATION DU NAVIRE SÉLECTIONNÉ
// ----------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current
  const source = map.getSource('selected-vessel-highlight')

  if (!source) return

  if (!selectedVessel?.coordinates) {
    source.setData(EMPTY_GEOJSON)
    return
  }

  const coordinates = selectedVessel.coordinates

  source.setData({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {
          id: selectedVessel.id,
        },
        geometry: {
          type: 'Point',
          coordinates,
        },
      },
    ],
  })

  map.flyTo({
    center: coordinates,
    zoom: Math.max(map.getZoom(), 7),
    speed: 0.8,
    curve: 1.4,
    essential: true,
  })

}, [
  selectedVessel?.id,
  selectedVessel?.coordinates?.[0],
  selectedVessel?.coordinates?.[1],
  mapReady,
])

useEffect(() => {
  if (!mapReady || !mapRef.current) return
  if (!selectedVessel?.coordinates) return

  const map = mapRef.current

  map.flyTo({
    center: selectedVessel.coordinates,
    zoom: Math.max(map.getZoom(), 7),
    speed: 0.8,
    curve: 1.4,
    essential: true,
  })
}, [selectedVessel?.id, mapReady])

// --------------------------------------------------
// CHARGEMENT DES CELLULES PRIORITAIRES MAAI
// --------------------------------------------------
// --------------------------------------------------
// VISIBILITÉ DE LA COUCHE AIS
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current

  if (map.getLayer('maritime-cells-fill')) {
    map.setLayoutProperty(
      'maritime-cells-fill',
      'visibility',
      showAIS ? 'visible' : 'none'
    )
  }

  if (map.getLayer('maritime-cells-outline')) {
    map.setLayoutProperty(
      'maritime-cells-outline',
      'visibility',
      showAIS ? 'visible' : 'none'
    )
  }
}, [showAIS, mapReady])

// --------------------------------------------------
// VISIBILITÉ DES COUCHES SAR
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const map = mapRef.current

  const layers = [
    {
      id: 'maritime-sar-matched',
      visible: showSARMatched,
    },
    {
      id: 'maritime-sar-unmatched',
      visible: showSARUnmatched,
    },
  ]

  layers.forEach(({ id, visible }) => {
    if (map.getLayer(id)) {
      map.setLayoutProperty(
        id,
        'visibility',
        visible ? 'visible' : 'none'
      )
    }
  })
}, [showSARMatched, showSARUnmatched, mapReady])
useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const source = mapRef.current.getSource('maai-cells')
  if (!source) return

  const items = ranking?.rankings?.attention_index ?? []

  const features = items
    .filter(item =>
  item.longitude != null &&
  item.latitude != null &&
  item.longitude !== '' &&
  item.latitude !== '' &&
  Number.isFinite(Number(item.longitude)) &&
  Number.isFinite(Number(item.latitude))
)
    .map(item => {
      const longitude = Number(item.longitude)
      const latitude = Number(item.latitude)
      const halfSize = 0.05

      return {
        type: 'Feature',
        properties: {
          cell_id: item.cell_id,
          rank: item.rank,
          attention_index: Number(item.attention_index ?? 0),
          ais_hours: Number(item.ais_hours ?? 0),
          ais_historical_median: Number(
            item.ais_historical_median ?? 0
          ),
          ais_relative_increase_percent: Number(
            item.ais_relative_increase_percent ?? 0
          ),
          sar_matched: Number(item.sar_matched ?? 0),
          sar_unmatched: Number(item.sar_unmatched ?? 0),
          sar_unmatched_rate_percent: Number(
            item.sar_unmatched_rate_percent ?? 0
          ),
          sar_confidence: Number(item.sar_confidence ?? 0),
          baseline_months: Number(item.baseline_months ?? 0),
          classification: item.classification,
        },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [longitude - halfSize, latitude - halfSize],
            [longitude + halfSize, latitude - halfSize],
            [longitude + halfSize, latitude + halfSize],
            [longitude - halfSize, latitude + halfSize],
            [longitude - halfSize, latitude - halfSize],
          ]],
        },
      }
    })

  source.setData({
    type: 'FeatureCollection',
    features,
  })
}, [ranking?.rankings?.attention_index, mapReady])


// --------------------------------------------------
// CHARGEMENT DES CELLULES D'INTELLIGENCE TEMPORELLE
// --------------------------------------------------

useEffect(() => {
  if (!mapReady || !mapRef.current) return

  const source = mapRef.current.getSource('temporal-cells')

  if (!source) return

  const items = temporal?.cells ?? []

  const features = items
    .filter(item =>
      Number.isFinite(Number(item.longitude)) &&
      Number.isFinite(Number(item.latitude))
    )
    .map(item => {
      const longitude = Number(item.longitude)
      const latitude = Number(item.latitude)
      const halfSize = 0.05

      return {
        type: 'Feature',

        properties: {
          cell_id: item.cell_id,

          priority_months: Number(
            item.priority_months ?? 0
          ),

          observed_months: Number(
            item.observed_months ?? 0
          ),

          eligible_months: Number(
            item.eligible_months ?? 0
          ),

          persistence_rate_percent: Number(
            item.persistence_rate_percent ?? 0
          ),

          coverage_rate_percent: Number(
            item.coverage_rate_percent ?? 0
          ),

          mean_attention_index: Number(
            item.mean_attention_index ?? 0
          ),

          peak_attention_index: Number(
            item.peak_attention_index ?? 0
          ),

          trend: item.trend ?? 'stable',
          recurrence: item.recurrence ?? 'occasional',
        },

        geometry: {
          type: 'Polygon',

          coordinates: [[
            [longitude - halfSize, latitude - halfSize],
            [longitude + halfSize, latitude - halfSize],
            [longitude + halfSize, latitude + halfSize],
            [longitude - halfSize, latitude + halfSize],
            [longitude - halfSize, latitude - halfSize],
          ]],
        },
      }
    })

  source.setData({
    type: 'FeatureCollection',
    features,
  })

}, [temporal?.cells, mapReady])
  return (
    <section className="w-full space-y-4">

      {/* En-tête */}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">

        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee]" />

            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-400">
              Maritime intelligence system
            </span>
          </div>

          <h2 className="text-xl font-semibold tracking-tight text-white">
            Cartographie maritime
          </h2>

          <p className="mt-1 text-xs text-slate-400">
            Analyse spatiale AIS · Détections satellitaires SAR · ZEE Sénégal
          </p>
        </div>

        <div className="flex flex-wrap gap-3">

          <div>
            <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Période d'analyse
            </label>

            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none transition focus:border-cyan-500"
            >
              {MONTHS.map((month) => (
                <option key={month} value={month}>
                  {month}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Classification
            </label>

            <select
              value={classification}
              onChange={(event) => setClassification(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-xs text-white outline-none transition focus:border-cyan-500"
            >
              <option value="all">Toutes les cellules</option>
              <option value="core">Zone centrale</option>
              <option value="boundary">Zone frontière</option>
              <option value="outside">Hors ZEE</option>
            </select>
          </div>

        </div>
      </div>

      {/* Statut des données */}

      <div className="flex flex-wrap items-center justify-between gap-3">

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span
            className={`h-2 w-2 rounded-full ${
              loading
                ? 'animate-pulse bg-amber-400'
                : 'bg-emerald-400'
            }`}
          />

          {loading
            ? 'Actualisation des données maritimes...'
            : `${formatNumber(cellCount)} cellules affichées`}
        </div>

        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
          <span>Zone d'étude</span>
          <span className="text-cyan-400">Sénégal · Atlantique</span>
        </div>

      </div>

      {error && (
        <div className="rounded-lg border border-orange-500/20 bg-orange-500/10 px-3 py-2 text-xs text-orange-300">
          {error}
        </div>
      )}

      {/* CARTE */}

      <div className="relative isolate h-[600px] w-full overflow-hidden rounded-2xl border border-slate-700/80 bg-[#071522] shadow-2xl shadow-black/30">

<div className="absolute left-4 top-4 z-20 w-64 max-w-[calc(100%-2rem)]">
  <div className="max-h-[calc(600px-2rem)] overflow-y-auto rounded-xl border border-white/10 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-xl">

    <div className="mb-4 flex items-center justify-between">
      <span className="text-xs font-bold uppercase tracking-widest text-white">
        Couches cartographiques
      </span>

      <span className="rounded-md border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-[9px] text-cyan-300">
  HISTORIQUE
</span>
    </div>

    <div className="flex flex-col gap-4">

      {/* MAAI */}

      <label className="flex cursor-pointer items-center gap-3 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={showMAAI}
          onChange={(e) => setShowMAAI(e.target.checked)}
          className="accent-rose-400"
        />

        <span className="h-2 w-2 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]" />

        Priorités MAAI
      </label>

      {/* INTELLIGENCE TEMPORELLE */}

      <div className="border-t border-white/10 pt-3">

        <label className="flex cursor-pointer items-center gap-3 text-xs text-slate-200">
          <input
            type="checkbox"
            checked={showTemporal}
            onChange={(e) => setShowTemporal(e.target.checked)}
            className="accent-fuchsia-400"
          />

          <span className="h-2 w-2 rounded-full bg-fuchsia-400 shadow-[0_0_8px_#e879f9]" />

          Récurrence temporelle
        </label>

        {showTemporal && (
          <div className="mt-3 rounded-lg bg-white/[0.03] p-3">

            <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.18em] text-fuchsia-300">
              Fréquence de récurrence
            </p>

            <div className="flex flex-col gap-3 text-[10px] text-slate-300">

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-fuchsia-400" />
                  Persistante
                </span>
                <span className="text-slate-500">Forte</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-amber-400" />
                  Récurrente
                </span>
                <span className="text-slate-500">Moyenne</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-sm bg-cyan-400" />
                  Occasionnelle
                </span>
                <span className="text-slate-500">Faible</span>
              </div>

            </div>

            <p className="mt-3 text-[9px] leading-relaxed text-slate-500">
              Fréquence d'apparition dans les cellules prioritaires
              pendant la période historique analysée.
            </p>

          </div>
        )}

      </div>

      {/* AIS */}

      <label className="flex cursor-pointer items-center gap-3 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={showAIS}
          onChange={(e) => setShowAIS(e.target.checked)}
          className="accent-cyan-400"
        />

        <span className="h-2 w-2 rounded-full bg-cyan-400" />
        Présence AIS
      </label>

      {/* SAR APPARIÉ */}

      <label className="flex cursor-pointer items-center gap-3 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={showSARMatched}
          onChange={(e) => setShowSARMatched(e.target.checked)}
          className="accent-teal-400"
        />

        <span className="h-2 w-2 rounded-full bg-teal-400" />
        SAR apparié
      </label>

      {/* SAR NON APPARIÉ */}

      <label className="flex cursor-pointer items-center gap-3 text-xs text-slate-200">
        <input
          type="checkbox"
          checked={showSARUnmatched}
          onChange={(e) => setShowSARUnmatched(e.target.checked)}
          className="accent-rose-400"
        />

        <span className="h-2 w-2 rounded-full bg-rose-400" />
        SAR non apparié
      </label>

    </div>
  </div>
</div>


<div className="absolute bottom-8 left-4 z-20 w-64 max-w-[calc(100%-2rem)] rounded-xl border border-white/10 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-xl">

  {/* MAAI */}

  <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-rose-300">
    Indice de priorité MAAI
  </p>

  <div
    className="mb-2 h-2 rounded-full"
    style={{
      background:
        'linear-gradient(to right, #164e63, #0891b2, #facc15, #fb923c, #f43f5e, #881337)',
    }}
  />

  <div className="flex justify-between text-[9px] text-slate-400">
    <span>Faible</span>
    <span>Modéré</span>
    <span>Élevé</span>
    <span>Critique</span>
  </div>

  <p className="mt-2 text-[9px] leading-relaxed text-slate-500">
    Le MAAI est un indice exploratoire de priorisation analytique,
    et non une preuve d'activité illégale.
  </p>

  <div className="my-3 border-t border-white/10" />

  {/* AIS */}

  <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">
    Intensité de présence AIS
  </p>

  <div
    className="mb-2 h-2 rounded-full"
    style={{
      background:
        'linear-gradient(to right, #10283d, #164e63, #0e7490, #06b6d4, #38bdf8, #facc15, #fb923c, #ef4444)',
    }}
  />

  <div className="flex justify-between text-[9px] text-slate-400">
    <span>Faible</span>
    <span>Modérée</span>
    <span>Élevée</span>
  </div>

  <div className="my-3 border-t border-white/10" />

  {/* SAR */}

  <div className="flex flex-col gap-2 text-[10px] text-slate-300">

    <div className="flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-teal-400" />
      Détections SAR appariées
    </div>

    <div className="flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-rose-400" />
      Détections SAR non appariées
    </div>

  </div>

  <p className="mt-3 text-[9px] leading-relaxed text-slate-500">
    Données agrégées par cellule spatiale. Les couleurs représentent
    des indicateurs analytiques et non des positions exactes de navires.
  </p>

</div>

        <div
  ref={containerRef}
  className="absolute inset-0 h-full w-full"
/>

        {/* Contrôle du fond cartographique */}

        <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">

          <div className="rounded-xl border border-white/10 bg-[#071522]/90 p-1.5 shadow-xl backdrop-blur-xl">

            <div className="px-2 pb-2 pt-1 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">
              Fond cartographique
            </div>

            <div className="flex gap-1">

              <button
                type="button"
                onClick={() => setBaseMap('satellite')}
                className={`rounded-lg px-3 py-2 text-[11px] font-semibold transition ${
                  baseMap === 'satellite'
                    ? 'bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20'
                    : 'text-slate-300 hover:bg-white/10'
                }`}
              >
                Satellite
              </button>

              <button
                type="button"
                onClick={() => setBaseMap('osm')}
                className={`rounded-lg px-3 py-2 text-[11px] font-semibold transition ${
                  baseMap === 'osm'
                    ? 'bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20'
                    : 'text-slate-300 hover:bg-white/10'
                }`}
              >
                Standard
              </button>

            </div>
          </div>

          {baseMap === 'satellite' && (
            <div className="w-fit rounded-lg border border-cyan-400/20 bg-[#071522]/90 px-3 py-2 backdrop-blur-xl">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />

                <span className="text-[10px] font-semibold text-cyan-300">
                  SENTINEL-2 · MOSAÏQUE 2025
                </span>
              </div>

              <p className="mt-1 text-[9px] text-slate-400">
                Imagerie de référence · Non temps réel
              </p>
            </div>
          )}

        </div>

        {/* Indicateur de chargement */}

        {loading && (
          <div className="absolute bottom-4 right-4 z-10 rounded-lg border border-white/10 bg-[#071522]/90 px-3 py-2 text-[10px] text-cyan-300 backdrop-blur-xl">
            Chargement des données...
          </div>
        )}

      </div>

      {/* LÉGENDE */}

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">

        <div className="mb-3 flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
            Légende cartographique
          </span>

          <span className="text-[9px] text-slate-500">
            Cellules spatiales GFW · 0,1°
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-7 gap-y-3">

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="h-3 w-3 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
            Zone centrale (≥ 75 %)
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="h-3 w-3 rounded-full bg-orange-400 shadow-[0_0_8px_#fb923c]" />
            Zone frontière (0–75 %)
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="h-3 w-3 rounded-full bg-slate-400" />
            Hors ZEE
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="h-3 w-3 rounded-full border-2 border-cyan-300 shadow-[0_0_8px_#22d3ee]" />
            Limite officielle de la ZEE
          </div>

        </div>
      </div>

      {/* NOTE SCIENTIFIQUE ET ATTRIBUTION */}

      <div className="space-y-2 text-[10px] leading-relaxed text-slate-500">

        <p>
  Les polygones représentent les cellules spatiales de la grille
  Global Fishing Watch de 0,1°. La couleur de la couche AIS
  représente l'intensité des heures de présence agrégées dans
  chaque cellule. Ces géométries ne représentent pas les positions
  exactes des navires. La classification repose sur le seuil
  opérationnel de recouvrement de 75 % avec la ZEE.
</p>

        <p>
          Fond satellite : Sentinel-2 Cloudless 2025 · EOX IT Services GmbH
          · Données Copernicus Sentinel modifiées. Cette mosaïque annuelle
          ne constitue pas une observation en temps réel.
        </p>

      </div>

    </section>
  )
}