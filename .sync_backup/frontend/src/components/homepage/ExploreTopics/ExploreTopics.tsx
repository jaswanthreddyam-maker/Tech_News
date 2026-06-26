"use client";

import { Reveal, StaggerContainer, StaggerItem } from "@/components/animations";

const gradients = [
  "from-blue-500/20 to-cyan-500/5",
  "from-purple-500/20 to-pink-500/5",
  "from-emerald-500/20 to-teal-500/5",
  "from-orange-500/20 to-amber-500/5",
  "from-red-500/20 to-rose-500/5",
];

function getHashIndex(str: string, max: number) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % max;
}

export function ExploreTopics() {
  const topics = ["Artificial Intelligence", "Robotics", "Cybersecurity", "Startups", "Quantum Computing", "Space Tech"];

  return (
    <div className="bg-card border border-border p-6 rounded-lg">
      <Reveal>
        <h3 className="font-sans font-bold mb-4">Explore Topics</h3>
      </Reveal>
      <StaggerContainer className="grid grid-cols-2 gap-3">
        {topics.map(topic => {
          const colorIdx = getHashIndex(topic, gradients.length);
          const gradient = gradients[colorIdx];
          
          return (
            <StaggerItem 
              key={topic} 
              className={`relative overflow-hidden group cursor-pointer border border-border/50 rounded-lg p-4 bg-gradient-to-br ${gradient} hover:border-primary/50 transition-colors`}
            >
              {/* SVG Pattern */}
              <div className="absolute inset-0 opacity-[0.03] group-hover:opacity-[0.06] transition-opacity mix-blend-overlay" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '12px 12px' }} />
              <span className="relative z-10 font-serif font-bold text-sm tracking-wide text-foreground group-hover:text-primary transition-colors">
                {topic}
              </span>
            </StaggerItem>
          );
        })}
      </StaggerContainer>
    </div>
  );
}
