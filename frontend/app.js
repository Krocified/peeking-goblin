const API_BASE = import.meta.env.VITE_API_BASE_URL
const form = document.querySelector('#search-form')
const input = document.querySelector('#card-name')
const status = document.querySelector('#status')
const results = document.querySelector('#results')
const imageDialog = document.querySelector('#image-dialog')
const imagePreview = document.querySelector('#image-preview')
const imageCaption = document.querySelector('#image-caption')
const closeImage = document.querySelector('#close-image')
let data = null

const money = (value, currency) => value == null ? '—' : new Intl.NumberFormat('en-US', {
  style: 'currency', currency, maximumFractionDigits: currency === 'JPY' ? 0 : 0,
}).format(value)

function setStatus(message, type = '') {
  status.className = `status ${type}`
  status.textContent = message
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]))
}

function optionList(values, selected) {
  return values.map((value) => `<option value="${escapeHtml(value)}" ${selected.has(value) ? 'selected' : ''}>${escapeHtml(value)}</option>`).join('')
}

function showImage(url, alt) {
  imagePreview.src = url
  imagePreview.alt = alt
  imageCaption.textContent = alt
  imageDialog.showModal()
}

function render() {
  if (!data) return
  const rarity = new Set([...results.querySelector('#rarity-filter').selectedOptions].map((option) => option.value))
  const set = new Set([...results.querySelector('#set-filter').selectedOptions].map((option) => option.value))
  const sort = results.querySelector('#sort').value
  const listings = data.listings.filter((listing) =>
    (!rarity.size || rarity.has(listing.rarity)) &&
    (!set.size || set.has(listing.setName)),
  ).sort((a, b) => {
    if (sort === 'high') return b.priceJpy - a.priceJpy
    if (sort === 'rarity') return (a.rarity || '').localeCompare(b.rarity || '')
    if (sort === 'set') return (a.setName || '').localeCompare(b.setName || '')
    return a.priceJpy - b.priceJpy
  })
  results.querySelector('#result-count').textContent = `${listings.length} listing${listings.length === 1 ? '' : 's'}`
  results.querySelector('#listing-body').innerHTML = listings.map((listing) => `
    <article class="listing">
      ${listing.imageUrl ? `<button class="image-button listing-image" data-image="${escapeHtml(listing.imageUrl)}" data-image-alt="${escapeHtml(listing.setNumber || 'Card image')}" type="button"><img src="${escapeHtml(listing.imageUrl)}" alt="" loading="lazy" /></button>` : '<div class="listing-image placeholder" aria-hidden="true"></div>'}
      <div class="listing-main">
        <span class="rarity">${escapeHtml(listing.rarity || 'Rarity unknown')}</span>
        <strong>${escapeHtml(listing.setNumber || 'Set number unknown')}</strong>
        <span class="muted">${escapeHtml(listing.setName || 'Set unknown')}${listing.condition ? ` · ${escapeHtml(listing.condition)}` : ''}</span>
      </div>
      <div class="price-stack"><strong>${money(listing.priceIdr, 'IDR')}</strong><span>${money(listing.priceJpy, 'JPY')}${listing.onSale ? ' · sale' : ''}</span></div>
      <a class="source-link" href="${escapeHtml(listing.sourceUrl || data.yuyuteiSearchUrl)}" target="_blank" rel="noreferrer">Source ↗</a>
    </article>`).join('') || '<p class="empty">No listings match these filters.</p>'
}

function renderResults() {
  const { card, filters, exchangeRate, warnings } = data
  const cardImage = card.imageUrl || data.listings.find((listing) => listing.imageUrl)?.imageUrl
  results.hidden = false
  results.innerHTML = `
    <div class="card-header">
      ${cardImage ? `<button class="image-button card-image" data-image="${escapeHtml(cardImage)}" data-image-alt="${escapeHtml(card.canonicalName)} card image" type="button"><img src="${escapeHtml(cardImage)}" alt="${escapeHtml(card.canonicalName)} card image" /></button>` : ''}
      <div class="card-identity"><p class="eyebrow">Resolved card</p><h2>${escapeHtml(card.canonicalName)}</h2><p class="japanese">${escapeHtml(card.japaneseBaseName)}</p></div>
      <div class="card-actions">${card.englishText ? '<button id="toggle-text" class="text-toggle" type="button" aria-expanded="false">Show English text</button>' : ''}<a class="wiki-link" href="${escapeHtml(card.sourceUrl)}" target="_blank" rel="noreferrer">Yugipedia ↗</a></div>
    </div>
    ${card.englishText ? `<div id="card-text" class="card-text" hidden><p class="eyebrow">English card text · latest Yugipedia version</p><p>${escapeHtml(card.englishText)}</p></div>` : ''}
    <div class="meta-row"><span>${exchangeRate ? `1 JPY = ${exchangeRate.value} IDR · ${exchangeRate.retrievedAt}` : 'IDR rate unavailable'}</span><a href="${escapeHtml(data.yuyuteiSearchUrl)}" target="_blank" rel="noreferrer">Open Yuyu-tei search ↗</a></div>
    <div class="controls">
      <div class="filter-control"><label for="rarity-filter">Rarity</label><select id="rarity-filter" multiple>${optionList(filters.rarities, new Set())}</select><button class="clear-filter" data-clear-filter="rarity-filter" type="button">Clear rarity</button></div>
      <div class="filter-control"><label for="set-filter">Set</label><select id="set-filter" multiple>${optionList(filters.sets, new Set())}</select><button class="clear-filter" data-clear-filter="set-filter" type="button">Clear set</button></div>
      <div class="filter-control sort-control"><label for="sort">Sort</label><select id="sort"><option value="low">Lowest price</option><option value="high">Highest price</option><option value="rarity">Rarity</option><option value="set">Set</option></select></div>
      <button id="clear-filters" class="clear" type="button">Clear all filters</button>
    </div>
    <div class="results-line"><strong id="result-count"></strong><span>${escapeHtml(warnings.join(' '))}</span></div>
    <div id="listing-body" class="listing-list"></div>`
  results.querySelectorAll('select').forEach((control) => control.addEventListener('change', render))
  results.querySelectorAll('[data-image]').forEach((button) => button.addEventListener('click', () => showImage(button.dataset.image, button.dataset.imageAlt)))
  results.querySelectorAll('[data-clear-filter]').forEach((button) => button.addEventListener('click', () => {
    results.querySelector(`#${button.dataset.clearFilter}`).selectedIndex = -1
    render()
  }))
  results.querySelector('#toggle-text')?.addEventListener('click', (event) => {
    const text = results.querySelector('#card-text')
    const expanded = event.currentTarget.getAttribute('aria-expanded') === 'true'
    event.currentTarget.setAttribute('aria-expanded', String(!expanded))
    event.currentTarget.textContent = expanded ? 'Show English text' : 'Hide English text'
    text.hidden = expanded
  })
  results.querySelector('#clear-filters').addEventListener('click', () => {
    results.querySelector('#rarity-filter').selectedIndex = -1
    results.querySelector('#set-filter').selectedIndex = -1
    results.querySelector('#sort').value = 'low'
    render()
  })
  render()
}

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  const name = input.value.trim()
  if (!name) return
  form.querySelector('button').disabled = true
  results.hidden = true
  setStatus('Resolving the Japanese name and checking Yuyu-tei…', 'loading')
  try {
    const response = await fetch(`${API_BASE}/api/card-price?name=${encodeURIComponent(name)}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || 'Search failed')
    data = payload
    setStatus('Live lookup complete.', 'success')
    renderResults()
  } catch (error) {
    setStatus(error.message, 'error')
  } finally {
    form.querySelector('button').disabled = false
  }
})

closeImage.addEventListener('click', () => imageDialog.close())
imageDialog.addEventListener('click', (event) => {
  if (event.target === imageDialog) imageDialog.close()
})
