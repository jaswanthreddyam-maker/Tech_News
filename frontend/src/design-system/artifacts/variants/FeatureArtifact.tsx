import React, { useState } from 'react';
import { ArtifactGeometry } from '../layers/ArtifactGeometry';
import { ArtifactMaterial } from '../layers/ArtifactMaterial';
import { ArtifactLighting } from '../layers/ArtifactLighting';
import { EditorialSurface } from '../layers/EditorialSurface';

interface FeatureArtifactProps {
  article: any;
  onClick?: () => void;
}

/**
 * FeatureArtifact
 * 
 * The large, dominant museum-display scale artifact.
 * Composes the 4 physical layers into a cohesive object.
 */
export function FeatureArtifact({ article, onClick }: FeatureArtifactProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div 
      className="group block w-full h-full cursor-pointer"
      role="button"
      tabIndex={0}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && onClick) {
          e.preventDefault();
          onClick();
        }
      }}
      style={{ transformStyle: 'preserve-3d' }}
    >
      <ArtifactGeometry thickness={28} proudZ={4} isHovered={isHovered}>
        <ArtifactMaterial variant="glass">
          <ArtifactLighting>
            <EditorialSurface article={article} variant="feature" isHovered={isHovered} />
          </ArtifactLighting>
        </ArtifactMaterial>
      </ArtifactGeometry>
    </div>
  );
}
