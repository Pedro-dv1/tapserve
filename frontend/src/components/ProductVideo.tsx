import { useEffect, useId, useRef, useState } from 'react';
import { Icon } from './Interface';

export default function ProductVideo({ id, name, className = '' }: { id: string; name: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const title = useId();
  useEffect(() => {
    if (!open) return;
    const player = video.current;
    const previous = document.body.style.overflow;
    dialog.current?.showModal(); document.body.style.overflow = 'hidden';
    return () => { player?.pause(); document.body.style.overflow = previous; trigger.current?.focus({ preventScroll: true }); };
  }, [open]);
  return <><button ref={trigger} type="button" className={`product-play ${className}`} aria-label={`Ver vídeo de ${name}`} onClick={event => { event.stopPropagation(); setFailed(false); setOpen(true); }}><Icon name="play" size={22} /></button>{open && <dialog ref={dialog} className="product-video-dialog" aria-labelledby={title} onClick={event => event.stopPropagation()} onCancel={event => { event.preventDefault(); setOpen(false); }}><header><h2 id={title}>{name}</h2><button className="icon-button" aria-label="Fechar vídeo" onClick={() => setOpen(false)}><Icon name="close" /></button></header>{failed ? <p className="error" role="alert">Vídeo indisponível. Feche para continuar no cardápio.</p> : <video ref={video} src={`/api/v1/public/products/${id}/video/`} controls playsInline preload="metadata" onError={() => setFailed(true)} aria-label={`Vídeo de ${name}`} />}<p>Use os controles para reproduzir ou abrir em tela cheia.</p></dialog>}</>;
}
