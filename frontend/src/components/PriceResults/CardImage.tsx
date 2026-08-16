import { useEffect, useState } from 'react'

export default function CardImage({ src, alt, onPreview }: { src?: string | null; alt: string; onPreview: (preview: { url: string; alt: string }) => void }) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>(src ? 'loading' : 'error')

  useEffect(() => setStatus(src ? 'loading' : 'error'), [src])

  if (!src) return <span className="card-image no-image" role="img" aria-label={alt}>No image</span>

  return <button className="image-button card-image" type="button" onClick={() => onPreview({ url: src, alt })} aria-label={`${alt} (preview)`}>
    {status === 'loading' && <span className="image-loading" aria-hidden="true" />}
    <img key={src} src={src} alt={alt} className={status === 'ready' ? '' : 'is-hidden'} onLoad={() => setStatus('ready')} onError={() => setStatus('error')} />
    {status === 'error' && <span className="no-image" aria-hidden="true">No image</span>}
  </button>
}