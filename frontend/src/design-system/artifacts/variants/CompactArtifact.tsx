import React, { useState } from 'react';
import { ArtifactGeometry } from '../layers/ArtifactGeometry';
import { ArtifactMaterial } from '../layers/ArtifactMaterial';
import { ArtifactLighting } from '../layers/ArtifactLighting';
import { EditorialSurface } from '../layers/EditorialSurface';

interface CompactArtifactProps {
  article: any;
  thickness?: number;
  proudZ?: number;
  cardIndex?: number;
  onClick?: () => void;
}

/**
 * CompactArtifact
 * 
 * The elegant, dense network scale artifact.
 * Composes the 4 physical layers with thinner geometry.
 */
export function CompactArtifact({ article, thickness = 14, proudZ = 2, cardIndex = 1, onClick }: CompactArtifactProps) {
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
      <ArtifactGeometry thickness={thickness} proudZ={proudZ} isHovered={isHovered}>
        <ArtifactMaterial variant="metal">
          <ArtifactLighting cardIndex={cardIndex}>
            <EditorialSurface article={article} variant="compact" isHovered={isHovered} />
          </ArtifactLighting>
        </ArtifactMaterial>
      </ArtifactGeometry>
    </div>
  );
}
