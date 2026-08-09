import { getTrendingArticles } from "@/lib/api/articles";
import { mapArticlesToFeatured } from "@/lib/mappers/homepage";
import { getImageProps } from "next/image";

export async function HeroLcpPreloader() {
  try {
    const res = await getTrendingArticles();
    const rawArticles = Array.isArray(res) ? res : (res as any)?.data || [];
    const featured = mapArticlesToFeatured(rawArticles);
    const first = featured[0];
    if (!first) return null;

    const imgUrl =
      first.thumbnail ||
      (first as any).thumbnail_local ||
      (first as any).image_url ||
      (first as any).image ||
      (first as any).thumbnail_url ||
      "";

    if (!imgUrl) return null;

    // Must match HeroMediaCard.tsx <Image> props 1:1 to guarantee exact URL match
    const { props } = getImageProps({
      src: imgUrl,
      alt: first.title || "",
      fill: true,
      sizes: "(max-width: 768px) 290px, 340px",
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
    console.error("HeroLcpPreloader error:", err);
    return null;
  }
}
