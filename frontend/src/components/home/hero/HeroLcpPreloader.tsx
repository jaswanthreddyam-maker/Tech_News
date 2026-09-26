import { getImageProps } from "next/image";

export function HeroLcpPreloader({ article }: { article?: any }) {
  if (!article) return null;

  try {
    const imgUrl =
      article.thumbnail ||
      (article as any).thumbnail_local ||
      (article as any).image_url ||
      (article as any).image ||
      (article as any).thumbnail_url ||
      "";

    if (!imgUrl) return null;

    const { props } = getImageProps({
      src: imgUrl,
      alt: article.title || "",
      fill: true,
      sizes: "(max-width: 768px) 275px, 304px",
      quality: 90,
      priority: true,
    });

    return (
      <link
        rel="preload"
        as="image"
        href={props.src}
        imageSrcSet={props.srcSet}
        imageSizes={props.sizes}
        fetchPriority="high"
      />
    );
  } catch (err) {
    return null;
  }
}
