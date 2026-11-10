import {
  Anchor,
  Globe2,
  RefreshCw,
  Languages,
} from 'lucide-react'

import { useTranslation } from 'react-i18next'

export default function Header({ loading, onRefresh }) {
  const { t, i18n } = useTranslation()

  const currentLanguage = i18n.language?.startsWith('en') ? 'en' : 'fr'

  const changeLanguage = (language) => {
    i18n.changeLanguage(language)
    localStorage.setItem('invisible-fleet-language', language)
  }

  return (
<header className="sticky top-0 z-50 flex min-h-[68px] items-center justify-between gap-3 border-b border-white/[0.07] bg-[#091625]/95 px-4 backdrop-blur sm:px-6">
      {/* LOGO ET IDENTITÉ */}
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-400/20 bg-cyan-400/[0.08]">
          <Anchor className="h-5 w-5 text-cyan-400" />
        </div>

        <div className="min-w-0">
          <h1 className="truncate text-sm font-bold tracking-[0.16em] text-white sm:text-base">
            THE INVISIBLE FLEET
          </h1>

          <p className="mt-0.5 text-[9px] tracking-[0.18em] text-slate-500">
            MARITIME INTELLIGENCE SYSTEM
          </p>
        </div>
      </div>

      {/* INFORMATIONS */}
      <div className="hidden items-center gap-6 lg:flex">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Globe2 size={14} className="text-cyan-400" />
          SENEGAL EEZ
        </div>

        <div className="h-5 w-px bg-slate-700" />

        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-xs text-slate-400">
            {t('dashboard.historical')}
          </span>
        </div>
      </div>

      {/* ACTIONS */}
      <div className="flex shrink-0 items-center gap-2">

        {/* SÉLECTEUR DE LANGUE */}
        <div className="flex items-center gap-1 rounded-lg border border-white/[0.08] bg-white/[0.03] p-1">
          <Languages size={14} className="mx-1 text-cyan-400" />

          <button
            onClick={() => changeLanguage('fr')}
            aria-label="Passer en français"
            aria-pressed={currentLanguage === 'fr'}
            className={`rounded-md px-2.5 py-1.5 text-[10px] font-bold transition ${
              currentLanguage === 'fr'
                ? 'bg-cyan-400/15 text-cyan-300'
                : 'text-slate-500 hover:text-white'
            }`}
          >
            FR
          </button>

          <button
            onClick={() => changeLanguage('en')}
            aria-label="Switch to English"
            aria-pressed={currentLanguage === 'en'}
            className={`rounded-md px-2.5 py-1.5 text-[10px] font-bold transition ${
              currentLanguage === 'en'
                ? 'bg-cyan-400/15 text-cyan-300'
                : 'text-slate-500 hover:text-white'
            }`}
          >
            EN
          </button>
        </div>

        {/* ACTUALISATION */}
        <button
          onClick={onRefresh}
          disabled={loading}
          title={t('dashboard.refresh')}
          className="flex h-9 shrink-0 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 text-xs text-slate-300 transition hover:border-cyan-400/30 hover:text-cyan-300 disabled:opacity-50"
        >
          <RefreshCw
            size={14}
            className={loading ? 'animate-spin' : ''}
          />

          <span className="hidden sm:inline">
            {t('dashboard.refresh')}
          </span>
        </button>
      </div>
    </header>
  )
}