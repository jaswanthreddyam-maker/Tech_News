/**
 * Curated Editorial Hero & Thumbnail Fallbacks by Tech Category
 * High-resolution, professional technology, AI, computing, and science photography.
 */
const CATEGORY_IMAGES: Record<string, string[]> = {
  "artificial-intelligence": [
    "https://images.unsplash.com/photo-1677442136019-21780efad99a?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1676299081847-824916de030a?auto=format&fit=crop&w=1200&q=80",
  ],
  cybersecurity: [
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
  ],
  hardware: [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1555680202-c86f0e12f086?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=1200&q=80",
  ],
  robotics: [
    "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1535378917042-10a22c95931a?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1561557944-6e7860d1a7eb?auto=format&fit=crop&w=1200&q=80",
  ],
  science: [
    "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1507413245164-6160d8298b31?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=1200&q=80",
  ],
  "startups-and-business": [
    "https://images.unsplash.com/photo-1559136555-9303baea8ebd?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80",
  ],
  policy: [
    "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
  ],
  technology: [
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504639725590-34d0984388bd?auto=format&fit=crop&w=1200&q=80",
  ],
  general: [
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
  ]
};

export function getCategoryFallbackImage(
  category?: string | { name?: string } | null,
  seed?: string | number | null
): string {
  const catStr = typeof category === "string" 
    ? category 
    : (typeof category === "object" && category?.name ? category.name : "technology");

  const normCat = catStr.toLowerCase().replace(/[^a-z0-9]/g, "-");
  
  let pool = CATEGORY_IMAGES[normCat];
  if (!pool) {
    for (const key of Object.keys(CATEGORY_IMAGES)) {
      if (normCat.includes(key) || key.includes(normCat)) {
        pool = CATEGORY_IMAGES[key];
        break;
      }
    }
  }
  
  if (!pool || pool.length === 0) {
    pool = CATEGORY_IMAGES["technology"];
  }

  if (seed !== undefined && seed !== null) {
    const strSeed = String(seed);
    let hash = 0;
    for (let i = 0; i < strSeed.length; i++) {
      hash = (hash << 5) - hash + strSeed.charCodeAt(i);
      hash |= 0;
    }
    const idx = Math.abs(hash) % pool.length;
    return pool[idx];
  }

  return pool[0];
}
