export type Candidate = { name: string; source: string; imageUrl?: string | null }
export type Pagination = { page: number; pageSize: number; total: number; totalPages: number; hasPrevious: boolean; hasMore: boolean }
export type CandidatePayload = { selectionRequired: true; query: string; candidates: Candidate[]; pagination?: Pagination }
export type Listing = {
  source: string
  currency: string
  setNumber: string | null
  setName: string | null
  rarity: string | null
  condition: string | null
  priceJpy: number | null
  priceUsd?: number | null
  priceIdr: number | null
  onSale: boolean | null
  inStock: boolean | null
  stockText?: string | null
  imageUrl: string | null
  sourceUrl: string | null
}
export type CardResult = {
  query: string
  aePending?: boolean
  card: { canonicalName: string; resolvedTitle?: string; japaneseBaseName: string; englishText?: string; imageUrl?: string | null; sourceUrl: string }
  exchangeRate: { base: string; target: string; rates: Record<string, number>; retrievedAt: string } | null
  filters: { rarities: string[]; sets: string[] }
  listings: Listing[]
  warnings: string[]
  yuyuteiSearchUrl: string
  tcgCornerSearchUrl?: string
}

export const API_BASE = import.meta.env.VITE_API_BASE_URL

export const money = (value: number | null, currency: string) => value == null ? '—' : new Intl.NumberFormat('en-US', {
  style: 'currency', currency, maximumFractionDigits: 0,
}).format(value)
