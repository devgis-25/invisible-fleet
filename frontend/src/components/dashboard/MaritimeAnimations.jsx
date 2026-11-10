import { Popup } from 'maplibre-gl'
const routes = [
  { id: 'r1', coordinates: [[-20.8, 12.8], [-20.1, 13.1], [-19.4, 13.5], [-18.7, 14.0]] },
  { id: 'r2', coordinates: [[-20.6, 14.2], [-19.9, 14.0], [-19.3, 13.7], [-18.8, 13.5]] },
  { id: 'r3', coordinates: [[-20.5, 15.4], [-19.8, 15.1], [-19.2, 14.8], [-18.7, 14.5]] },
  { id: 'r4', coordinates: [[-20.7, 16.1], [-19.9, 15.9], [-19.3, 15.6], [-18.8, 15.3]] },
  { id: 'r5', coordinates: [[-20.4, 12.9], [-19.8, 13.3], [-19.3, 13.8], [-18.8, 14.2]] },
  { id: 'r6', coordinates: [[-20.8, 14.8], [-20.0, 14.6], [-19.4, 14.3], [-18.9, 14.0]] },
  { id: 'r7', coordinates: [[-20.6, 15.9], [-19.9, 15.6], [-19.3, 15.3], [-18.8, 15.0]] },
  { id: 'r8', coordinates: [[-20.5, 13.7], [-19.9, 14.0], [-19.3, 14.4], [-18.8, 14.8]] },
]

// ========================================
// VALIDATION GÉOGRAPHIQUE DE LA ZEE
// ========================================

function pointInRing(point, ring) {
  const [x, y] = point
  let inside = false

  for (
    let i = 0, j = ring.length - 1;
    i < ring.length;
    j = i++
  ) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]

    const intersects =
      (yi > y) !== (yj > y) &&
      x < ((xj - xi) * (y - yi)) / (yj - yi) + xi

    if (intersects) inside = !inside
  }

  return inside
}

function pointInPolygon(point, polygon) {
  if (!polygon?.length) return false

  // Le point doit être dans le contour extérieur
  if (!pointInRing(point, polygon[0])) return false

  // Il ne doit pas être dans un trou
  for (let i = 1; i < polygon.length; i++) {
    if (pointInRing(point, polygon[i])) {
      return false
    }
  }

  return true
}

function pointInGeometry(point, geojson) {
  if (!geojson) return false

  const geometry =
    geojson.type === 'Feature'
      ? geojson.geometry
      : geojson.type === 'FeatureCollection'
        ? null
        : geojson

  if (geojson.type === 'FeatureCollection') {
    return geojson.features.some((feature) =>
      pointInGeometry(point, feature),
    )
  }

  if (!geometry) return false

  if (geometry.type === 'Polygon') {
    return pointInPolygon(point, geometry.coordinates)
  }

  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.some((polygon) =>
      pointInPolygon(point, polygon),
    )
  }

  return false
}

// Découpe les routes en segments situés dans la ZEE
function clipRoutesToGeometry(sourceRoutes, geometry) {
  const clippedRoutes = []

  sourceRoutes.forEach((route) => {
    let currentSegment = []
    let segmentIndex = 0

    const saveSegment = () => {
      if (currentSegment.length >= 2) {
        clippedRoutes.push({
          id: `${route.id}-${segmentIndex++}`,
          coordinates: currentSegment,
        })
      }

      currentSegment = []
    }

    for (let i = 0; i < route.coordinates.length - 1; i++) {
      const start = route.coordinates[i]
      const end = route.coordinates[i + 1]

      const samples = 500

      for (let j = 0; j <= samples; j++) {
        if (i > 0 && j === 0) continue

        const point = interpolate(
          start,
          end,
          j / samples,
        )

        if (pointInGeometry(point, geometry)) {
          currentSegment.push(point)
        } else {
          saveSegment()
        }
      }
    }

    saveSegment()
  })

  return clippedRoutes
}

const interpolate = (a, b, t) => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
]


function positionAlongRoute(coords, progress) {
  const segments = coords.length - 1
  const scaled = progress * segments
  const index = Math.min(Math.floor(scaled), segments - 1)
  return interpolate(coords[index], coords[index + 1], scaled - index)
}

function calculateBearing(a, b) {
  const dx = b[0] - a[0]
  const dy = b[1] - a[1]
  return (Math.atan2(dx, dy) * 180) / Math.PI
}

function createVesselIcon() {
  const canvas = document.createElement('canvas')
  canvas.width = 64
  canvas.height = 64
  const ctx = canvas.getContext('2d')

  ctx.translate(32, 32)

  ctx.shadowColor = '#00e5ff'
  ctx.shadowBlur = 18

  ctx.fillStyle = '#00e5ff'
  ctx.beginPath()
  ctx.moveTo(0, -23)
  ctx.lineTo(13, 13)
  ctx.lineTo(0, 7)
  ctx.lineTo(-13, 13)
  ctx.closePath()
  ctx.fill()

  ctx.shadowBlur = 0
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 1.5
  ctx.stroke()

  return ctx.getImageData(0, 0, 64, 64)
}

export function addMaritimeAnimations(
  map,
  { onVesselsUpdate, getZoneGeometry } = {},
) {
  if (map.hasImage('vessel-icon')) {
    map.removeImage('vessel-icon')
  }

  map.addImage('vessel-icon', createVesselIcon(), {
    pixelRatio: 2,
  })

  // Routes lumineuses progressives
  map.addSource('animated-routes', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })

  map.addLayer({
    id: 'animated-routes-glow',
    type: 'line',
    source: 'animated-routes',
    paint: {
      'line-color': '#00d9ff',
      'line-width': 5,
      'line-opacity': 0.22,
      'line-blur': 4,
    },
  })

  map.addLayer({
    id: 'animated-routes-line',
    type: 'line',
    source: 'animated-routes',
    paint: {
      'line-color': '#00e5ff',
      'line-width': 1.5,
      'line-opacity': 0.85,
    },
  })

  // Navires
  map.addSource('animated-vessels', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })

  map.addLayer({
    id: 'animated-vessels-layer',
    type: 'symbol',
    source: 'animated-vessels',
    layout: {
      'icon-image': 'vessel-icon',
      'icon-size': 0.48,
      'icon-rotate': ['get', 'heading'],
      'icon-rotation-alignment': 'map',
      'icon-allow-overlap': true,
    },
  })


  // ========================================
// INTERACTION NAVIRES
// ========================================

let vesselPopup = null

const showVesselPopup = (event) => {
  const feature = event.features?.[0]

  if (!feature) return

  const properties = feature.properties
  const coordinates = feature.geometry.coordinates.slice()

  const heading = Number(properties.heading)
  const speed = Number(properties.speed)

  const direction =
    heading >= 0 && heading < 90
      ? 'Nord-Est'
      : heading >= 90 && heading < 180
        ? 'Sud-Est'
        : heading >= 180 && heading < 270
          ? 'Sud-Ouest'
          : 'Nord-Ouest'

  const content = `
    <div style="
      width:230px;
      padding:14px;
      background:#07111f;
      color:#e2f7ff;
      font-family:Inter, sans-serif;
      border:1px solid rgba(0,229,255,.35);
      border-radius:12px;
    ">
      <div style="
        color:#00e5ff;
        font-size:10px;
        letter-spacing:2px;
        margin-bottom:8px;
      ">
        CONTACT MARITIME SIMULÉ
      </div>

      <div style="
        font-size:19px;
        font-weight:700;
        margin-bottom:12px;
      ">
        ${properties.id}
      </div>

      <div style="
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:10px;
        font-size:12px;
      ">
        <div>
          <div style="color:#64748b">Vitesse</div>
          <strong>${speed} kn</strong>
        </div>

        <div>
          <div style="color:#64748b">Cap</div>
          <strong>${heading}°</strong>
        </div>

        <div>
          <div style="color:#64748b">Direction</div>
          <strong>${direction}</strong>
        </div>

        <div>
          <div style="color:#64748b">Statut</div>
          <strong style="color:#00e5ff">SIMULÉ</strong>
        </div>
      </div>

      <div style="
        margin-top:12px;
        padding-top:10px;
        border-top:1px solid rgba(255,255,255,.08);
        color:#94a3b8;
        font-size:10px;
      ">
        Position illustrative · Non AIS réel
      </div>
    </div>
  `

  vesselPopup?.remove()

  vesselPopup = new Popup({
    closeButton: true,
    closeOnClick: false,
    offset: 18,
    className: 'maritime-vessel-popup',
  })
    .setLngLat(coordinates)
    .setHTML(content)
    .addTo(map)
}

const setVesselCursor = () => {
  map.getCanvas().style.cursor = 'pointer'
}

const resetVesselCursor = () => {
  map.getCanvas().style.cursor = ''
}

map.on('click', 'animated-vessels-layer', showVesselPopup)
map.on('mouseenter', 'animated-vessels-layer', setVesselCursor)
map.on('mouseleave', 'animated-vessels-layer', resetVesselCursor)

  // Radar central offshore
 let radarCenter = [-19.4, 14.4]

  map.addSource('maritime-radar', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })

  // Faisceau radar rotatif
map.addSource('radar-sweep', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: [],
  },
})

map.addLayer({
  id: 'radar-sweep-glow',
  type: 'line',
  source: 'radar-sweep',
  paint: {
    'line-color': '#00ffcc',
    'line-width': 5,
    'line-opacity': 0.25,
    'line-blur': 5,
  },
})

map.addLayer({
  id: 'radar-sweep-line',
  type: 'line',
  source: 'radar-sweep',
  paint: {
    'line-color': '#aaffee',
    'line-width': 1.5,
    'line-opacity': 0.95,
  },
})


map.addSource('radar-contacts', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: [],
  },
})

map.addLayer({
  id: 'radar-contacts-glow',
  type: 'circle',
  source: 'radar-contacts',
  paint: {
    'circle-radius': 9,
    'circle-color': '#00e5ff',
    'circle-opacity': 0.2,
    'circle-blur': 0.8,
  },
})

map.addLayer({
  id: 'radar-contacts-core',
  type: 'circle',
  source: 'radar-contacts',
  paint: {
    'circle-radius': 3,
    'circle-color': '#ffffff',
    'circle-opacity': 0.95,
  },
})

  map.addLayer({
    id: 'maritime-radar-glow',
    type: 'circle',
    source: 'maritime-radar',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': '#00e5ff',
      'circle-opacity': 0.04,
      'circle-stroke-color': '#00e5ff',
      'circle-stroke-width': 2,
      'circle-stroke-opacity': 0.55,
    },
  })

  map.addLayer({
    id: 'maritime-radar-ring',
    type: 'circle',
    source: 'maritime-radar',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': 'rgba(0,0,0,0)',
      'circle-stroke-color': '#00e5ff',
      'circle-stroke-width': 1.2,
      'circle-stroke-opacity': 0.75,
    },
  })

  let animationFrame
  let startTime = null
  let lastContactsUpdate = 0
let activeRoutes = []
let lastZoneGeometry = null
  const animate = (now) => {
    if (!startTime) startTime = now

    const elapsed = (now - startTime) / 1000
// Récupération de la géométrie réelle de la ZEE
const zoneGeometry = getZoneGeometry?.()

// Recalcul uniquement lorsque la géométrie change
if (zoneGeometry && zoneGeometry !== lastZoneGeometry) {
  lastZoneGeometry = zoneGeometry

  activeRoutes = clipRoutesToGeometry(
    routes,
    zoneGeometry,
  )

  if (activeRoutes.length > 0) {
  const firstRoute = activeRoutes[0]

  radarCenter =
    firstRoute.coordinates[
      Math.floor(firstRoute.coordinates.length / 2)
    ]
}

  console.info(
    `[MARITIME] ${activeRoutes.length} segments de routes validés dans la ZEE.`,
  )
}
    // 24 navires : 3 par corridor
// ========================================
// NAVIRES SIMULÉS : 24 CONTACTS
// ========================================

const vesselFeatures = activeRoutes.length
  ? Array.from({ length: 24 }, (_, vesselIndex) => {
      const routeIndex = vesselIndex % activeRoutes.length

      const route = activeRoutes[routeIndex]

      const speed = 0.018 + routeIndex * 0.0012

      const progress = (
        elapsed * speed +
        Math.floor(vesselIndex / activeRoutes.length) / 3 +
        routeIndex * 0.037
      ) % 1

      const candidatePosition = positionAlongRoute(
  route.coordinates,
  progress,
)

const position = pointInGeometry(
  candidatePosition,
  lastZoneGeometry,
)
  ? candidatePosition
  : route.coordinates[0]

const candidateNextPosition = positionAlongRoute(
  route.coordinates,
  Math.min(progress + 0.006, 0.999),
)

const nextPosition = pointInGeometry(
  candidateNextPosition,
  lastZoneGeometry,
)
  ? candidateNextPosition
  : position

      const heading =
        calculateBearing(position, nextPosition) +
        Math.sin(elapsed * 0.7 + routeIndex) * 3

      return {
        type: 'Feature',
        properties: {
          id: `SN-${String(vesselIndex + 1).padStart(3, '0')}`,
          heading: Number(heading.toFixed(1)),
          speed: Number(
            (8 + Math.sin(elapsed + routeIndex) * 2).toFixed(1),
          ),
          status: 'SIMULATED',
          route: route.id,
        },
        geometry: {
          type: 'Point',
          coordinates: position,
        },
      }
    })
  : []

    // Contacts visibles sur le radar
const radarContacts = vesselFeatures
  .filter((_, index) => index % 3 === 0)
  .map((vessel) => ({
    id: vessel.properties.id,
    heading: vessel.properties.heading,
    speed: vessel.properties.speed,
    status: 'SIMULÉ',
    coordinates: vessel.geometry.coordinates,
  }))

map.getSource('radar-contacts')?.setData({
  type: 'FeatureCollection',
  features: radarContacts.map((contact) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: contact.coordinates,
    },
    properties: {
      id: contact.id,
    },
  })),
})

// Mise à jour de la liste React : une fois par seconde
if (!lastContactsUpdate || now - lastContactsUpdate >= 1000) {
  lastContactsUpdate = now
  onVesselsUpdate?.(radarContacts)
}

    map.getSource('animated-vessels')?.setData({
      type: 'FeatureCollection',
      features: vesselFeatures,
    })

    // Trajectoires qui se dessinent progressivement
    const routeFeatures = activeRoutes.map((route, index) => {
      const progress = Math.min(
  elapsed * 0.025 + index * 0.12,
  1,
)
      const coords = route.coordinates
      const segmentCount = coords.length - 1
      const scaled = progress * segmentCount
      const completeSegments = Math.floor(scaled)
      const partial = scaled - completeSegments

      const drawnCoordinates = coords.slice(0, completeSegments + 1)

      if (completeSegments < segmentCount) {
        drawnCoordinates.push(
          interpolate(
            coords[completeSegments],
            coords[completeSegments + 1],
            partial,
          ),
        )
      }

      if (drawnCoordinates.length < 2) {
        drawnCoordinates.push(coords[1])
      }

      return {
        type: 'Feature',
        properties: { id: route.id },
        geometry: {
          type: 'LineString',
          coordinates: drawnCoordinates,
        },
      }
    })

    map.getSource('animated-routes')?.setData({
      type: 'FeatureCollection',
      features: routeFeatures,
    })

    // Radar pulsant
    const pulse = (elapsed * 0.65) % 1
    const radius = 20 + pulse * 150

    map.getSource('maritime-radar')?.setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { radius },
          geometry: {
            type: 'Point',
            coordinates: radarCenter,
          },
        },
        {
          type: 'Feature',
          properties: { radius: 20 + ((pulse + 0.5) % 1) * 150 },
          geometry: {
            type: 'Point',
            coordinates: radarCenter,
          },
        },
      ],
    })


    // ========================================
// RADAR : balayage rotatif
// ========================================

const sweepAngle = (elapsed * 45) % 360
const angleRad = (sweepAngle * Math.PI) / 180

const radarDistance = 0.85

const sweepEnd = [
  radarCenter[0] + Math.sin(angleRad) * radarDistance,
  radarCenter[1] + Math.cos(angleRad) * radarDistance,
]

map.getSource('radar-sweep')?.setData({
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [radarCenter, sweepEnd],
      },
      properties: {},
    },
  ],
})

// ========================================
// RADAR : contacts simulés
// ========================================

// const contacts = vesselFeatures
//   .filter((_, index) => {
//     // Quelques navires sont affichés comme contacts radar
//     return index % 3 === 0
//   })
//   .map((vessel) => ({
//     type: 'Feature',
//     geometry: vessel.geometry,
//     properties: {
//       intensity: 0.5 + Math.random() * 0.5,
//     },
//   }))

// map.getSource('radar-contacts')?.setData({
//   type: 'FeatureCollection',
//   features: contacts,
// })

    animationFrame = requestAnimationFrame(animate)
  }

  animationFrame = requestAnimationFrame(animate)

  return () => {
  cancelAnimationFrame(animationFrame)

  map.off('click', 'animated-vessels-layer', showVesselPopup)
  map.off('mouseenter', 'animated-vessels-layer', setVesselCursor)
  map.off('mouseleave', 'animated-vessels-layer', resetVesselCursor)

  vesselPopup?.remove()
}
}
