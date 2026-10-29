import { useState } from 'react';
import { ProductImage } from '../../components/Interface';
import ProductVideo from '../../components/ProductVideo';
import type { ProductDetail } from './menuData';

export default function ProductGallery({ product }: { product: ProductDetail }) {
  const [selected, setSelected] = useState(0);
  const slides = [...(product.has_image ? [{ id: 'cover', alt_text: product.name }] : []), ...product.photos];
  const current = slides[Math.min(selected, slides.length - 1)];
  return <section className="product-gallery" aria-label={`Fotos de ${product.name}`}>
    <div className="product-detail-media">{current && current.id !== 'cover' ? <GalleryImage key={current.id} src={`/api/v1/public/products/${product.id}/photos/${current.id}/`} alt={current.alt_text || product.name} /> : <ProductImage key={`${product.id}:${product.image_version}`} version={product.image_version} id={product.id} name={product.name} hasImage={product.has_image} className="detail-photo" />}{product.has_video && <ProductVideo id={product.id} name={product.name} />}</div>
    {slides.length > 1 && <div className="gallery-navigation" aria-label="Escolher foto">{slides.map((slide, index) => <button type="button" aria-label={`Foto ${index + 1} de ${slides.length}`} aria-pressed={current?.id === slide.id} key={slide.id} onClick={() => setSelected(index)}>{index + 1}</button>)}</div>}
  </section>;
}
function GalleryImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  return <span className="product-image detail-photo">{failed ? <span className="image-fallback" role="img" aria-label={`${alt}: imagem indisponível`}>Imagem indisponível</span> : <img src={src} alt={alt} width={1200} height={900} onError={() => setFailed(true)} />}</span>;
}
