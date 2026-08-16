import { useEffect, useRef } from 'react'
import './ImageDialog.scss'

export default function ImageDialog({ preview, onClose }: { preview: { url: string; alt: string } | null; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { if (preview && !dialog.current?.open) dialog.current?.showModal(); if (!preview && dialog.current?.open) dialog.current.close() }, [preview])
  return <dialog ref={dialog} className="image-dialog" onClick={(event) => { if (event.target === dialog.current) onClose() }}><button className="dialog-close" type="button" onClick={onClose} aria-label="Close image preview">×</button>{preview && <><img src={preview.url} alt={preview.alt} /><p>{preview.alt}</p></>}</dialog>
}
