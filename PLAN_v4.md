# HALUZ GitHub Profile v4 — Plan de Implementación

## Resumen
Rediseño completo del perfil a v4: estética cyberpunk más profesional, datos 100% reales vía
GitHub GraphQL API, ASCII art skull reemplaza al holograma anime, sin datos inventados.

---

## Archivos a crear / modificar

### 1. `.github/workflows/update-uptime.yml` → MODIFICAR

**Migración REST → GraphQL API v4** para obtener todo en una sola llamada:

```graphql
query {
  user(login: "aaronestradabonilla777") {
    repositories(first: 100, isFork: false)  { totalCount }
    followers                                 { totalCount }
    following                                 { totalCount }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name, description, stargazerCount, forkCount
          primaryLanguage { name, color }
        }
      }
    }
    contributionsCollection(from: "2026-01-01T00:00:00Z") {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
```

**Nuevos datos calculados en Python:**
- `CURRENT_STREAK` — días consecutivos con actividad (calculado del calendario)
- `LONGEST_STREAK` — racha más larga del año
- `CONTRIBUTIONS_2026` — total de contribuciones en 2026
- `TOTAL_STARS` — suma de estrellas en todos los repos
- `TOTAL_FORKS` — suma de forks
- `PINNED_REPOS` — lista de hasta 6 repos con nombre, lenguaje, color, stars, forks
- `RECENT_COMMITS` — últimos 5 commits vía REST Events API (hash corto + mensaje)

**Método de sustitución:** usar placeholders `{{PLACEHOLDER}}` en los SVGs
en vez del regex frágil actual. Python hace `svg.replace("{{VAR}}", valor)`.

**Frecuencia:** mantener cada 6 horas (sin cambio).

---

### 2. `header_v4.svg` → CREAR NUEVO (reemplaza header_v3.svg en README)
**Dimensiones:** 900 × 280 px

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌─────────────────────────────┐  ┌──────┐  ┌─────────────┐  │
│  │          │  │  HALUZ             [purple]  │  │  QR  │  │ REPOS   13  │  │
│  │  ASCII   │  │  ID: aaronestradabonilla777  │  │VERIF │  │ FOLLOW   5  │  │
│  │  SKULL   │  │  [NETRUNNER LVL.50][MEXICO]  │  │      │  │ FOLLWNG  9  │  │
│  │  pixel   │  │                              │  │ 3Y   │  │ STARS    0  │  │
│  │   art    │  │  STREAK:  ▓▓▓  {{CURR}}d     │  │ 255D │  │ FORKS    0  │  │
│  │          │  │  MAX:     ▓▓▓▓ {{MAX}}d      │  │  13H │  │ PRs      0  │  │
│  │NEURAL_ID │  │  2026:    ████ {{CONTRIB}}   │  │      │  │ API_OK      │  │
│  └──────────┘  └─────────────────────────────┘  └──────┘  └─────────────┘  │
│  [DATA STREAM ───────────────────────────────────────────────────────────]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**ASCII Skull** — pixel art de ~120×190px hecho con rectángulos SVG de 4×4px,
  colores cyan (#00f3ff) con scan line animado horizontal.
  Etiqueta inferior `NEURAL_ID v4.0` con blink verde.

**Identity Panel** — HALUZ con glow animado purple (igual que v3).
  3 métricas reales en mini-bars:
  - `STREAK` actual en cyan
  - `STREAK_MAX` en naranja
  - `CONTRIB_2026` en verde

**QR + Uptime** — igual que v3 pero con placeholder `{{YEARS}}Y {{DAYS}}D {{HOURS}}H`.

**Network Metrics** — 6 valores reales: REPOS, FOLLOWERS, FOLLOWING, STARS, FORKS, PRS_MERGED.
  Sin "THREAT ASSESSMENT" ficticio.

---

### 3. `core_v4.svg` → CREAR NUEVO (reemplaza core_v3.svg en README)
**Dimensiones:** 900 × 640 px

```
┌────────────────┬────────────────┬────────────────────────────────────────────┐
│ FRONTEND_OPS   │ BACKEND_SYS    │ INFRA_STACK                                │
│ TypeScript 95% │ Node.js    85% │ Linux       90%                            │
│ React/Next  90%│ Python     75% │ Git/GitHub  95%                            │
│ JavaScript  88%│ Java       60% │ Docker      65%                            │
│ HTML5/CSS3  92%│ Firebase   70% │ Vercel      80%                            │
│ TailwindCSS 85%│ MongoDB    55% │ CI/CD       70%                            │
│ React Native78%│ C++        50% │ Azure/AWS   50%                            │
│ Three.js    70%│ PostgreSQL 65% │ K8s         45%                            │
├────────────────┴────────┬───────┴──────────────────────┬─────────────────────┤
│ LANG_DISTRIBUTION       │ SKILL_RADAR (hexagonal)      │ PINNED_REPOS        │
│ Donut chart real        │ FRONTEND BACKEND DEVOPS      │ ┌──────────────────┐│
│ (lenguajes del API)     │ MOBILE   SECURITY  AI/ML     │ │ repo-name  ⭐ 0  ││
│                         │                              │ │ TypeScript  🍴 0 ││
│                         │                              │ └──────────────────┘│
│                         │                              │ ┌──────────────────┐│
│                         │                              │ │ repo-name  ⭐ 0  ││
│                         │                              │ └──────────────────┘│
│                         │                              │ (hasta 6 repos)     │
├─────────────────────────┴──────────────────────────────┴─────────────────────┤
│ COMMIT_HEATMAP — 52 semanas × 7 días (año 2026 completo)                     │
│ TOTAL: {{CONTRIBUTIONS_2026}} contributions this year                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

**PINNED_REPOS** — Reemplaza el panel de "E$ Eurodollars" y "GEO_TRACKING".
  Mini-cards por repo, borde del color del lenguaje primario, datos reales del API.
  Si no hay repos fijados, muestra los más recientes con actividad.

**Heatmap** — igual que v3 pero con el total real de 2026 en el header.

---

### 4. `footer_v4.svg` → CREAR NUEVO (reemplaza footer_v3.svg en README)
**Dimensiones:** 900 × 220 px (más compacto que v3)

```
┌──────────────────┬─────────────────────────────────┬─────────────────────────┐
│ NETWORK_TRAFFIC  │ RECENT_COMMITS (typewriter)      │ SYSTEM_LOG              │
│ sparklines IN    │ > git log --oneline              │ > HALUZ_PROTOCOL v5.0   │
│ sparklines OUT   │ [a7f3c2b] feat: heatmap gen      │ > [OK] API Connected    │
│                  │ [78b8c18] fix: repair SVG         │ > [OK] Neural Loaded    │
│                  │ [921a847] chore: bust cache       │ > [WARN] P1S OFFLINE    │
│                  │ [aa45725] Update README           │ > Skills Matrix Synced  │
│                  │ [8f7a73a] fix: XML tags           │ > Ready... _            │
├──────────────────┴─────────────────────────────────┴─────────────────────────┤
│ [CURRENT_TASK: FULL STACK DEV] [SESSION] [PROC/MEM/CPU] [EXECUTE] [ONLINE]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2026 NIGHT CITY NETWORKS // HALUZ PROTOCOL  |  github.com/aaronestradabonilla777│
└──────────────────────────────────────────────────────────────────────────────┘
```

**RECENT_COMMITS** — Reemplaza SERVER_RACK. Los 5 commits más recientes del API
  con hash corto + mensaje. Animación typewriter (igual que el terminal actual).
  Placeholder `{{COMMIT_1}}` hasta `{{COMMIT_5}}` sustituidos por el workflow.

---

### 5. `README.md` → MODIFICAR
- Cambiar referencias `header_v3.svg?v=3.8` → `header_v4.svg?v=4.0`, etc.
- Agregar `?v={{VERSION}}` como cache-bust dinámico manejado por el workflow.

---

## Orden de implementación

1. **Workflow** — actualizar `.github/workflows/update-uptime.yml` con GraphQL + nuevos datos
2. **header_v4.svg** — crear con ASCII skull + métricas reales + placeholders
3. **core_v4.svg** — crear con PINNED_REPOS + heatmap 52 semanas
4. **footer_v4.svg** — crear con recent commits reales
5. **README.md** — actualizar referencias a v4
6. **Commit + push** — el workflow se ejecuta en el push y sustituye todos los placeholders

---

## Paleta de colores (sin cambios)

| Elemento     | Color     |
|--------------|-----------|
| Cyan (UI)    | `#00f3ff` |
| Purple (ID)  | `#bf00ff` |
| Red (alert)  | `#ff003c` |
| Green (ok)   | `#0aff0a` |
| Orange (warn)| `#ff9500` |
| Background   | `#050505` |
| Text dim     | `#778899` |

---

## Qué NO cambia
- Estética cyberpunk / Night City
- Animaciones CSS (fadeIn, pulse, blink, glitch, etc.)
- Colores y tipografía
- Frecuencia de actualización (6h)
- Skill bars del core (valores hardcodeados por el dueño del perfil)
