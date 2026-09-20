import React from 'react';

export const SidebarMotif: React.FC = () => {
  return (
    <div className="w-full select-none pointer-events-none">
      <svg
        viewBox="0 0 240 120"
        className="w-full h-auto overflow-visible"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Background Subtle Rolling Hill Horizon */}
        <path
          d="M0 85 C 40 82, 100 78, 160 84 C 200 88, 225 82, 240 80 L 240 120 L 0 120 Z"
          fill="#EEF0EB"
          opacity="0.6"
        />

        {/* Distant Background Pine Trees (Faint Muted Green/Gray) */}
        <g opacity="0.45" fill="#8B9B90">
          {/* Distant tree 1 */}
          <path d="M125 78 L 129 88 L 121 88 Z" />
          <path d="M125 84 L 131 95 L 119 95 Z" />
          <path d="M125 91 L 133 103 L 117 103 Z" />

          {/* Distant tree 2 */}
          <path d="M136 74 L 141 84 L 131 84 Z" />
          <path d="M136 80 L 143 92 L 129 92 Z" />
          <path d="M136 88 L 146 101 L 126 101 Z" />

          {/* Distant tree 3 (Taller) */}
          <path d="M152 68 L 158 80 L 146 80 Z" />
          <path d="M152 76 L 161 90 L 143 90 Z" />
          <path d="M152 85 L 165 102 L 139 102 Z" />

          {/* Distant tree 4 */}
          <path d="M172 73 L 177 84 L 167 84 Z" />
          <path d="M172 80 L 180 93 L 164 93 Z" />
          <path d="M172 89 L 183 103 L 161 103 Z" />
        </g>

        {/* Foreground Winding Highway Road */}
        {/* Road Bed / Asphalt Base */}
        <path
          d="M 10 120 C 50 112, 90 98, 105 88 C 118 79, 102 75, 85 75 C 70 75, 80 72, 105 70 C 130 68, 155 72, 205 80 L 200 82 C 150 74, 130 71, 105 72 C 85 73, 76 77, 90 78 C 108 79, 128 84, 115 92 C 95 104, 55 118, 0 120 Z"
          fill="#D8DDD8"
          opacity="0.8"
        />

        {/* Main Road Surface Ribbon */}
        <path
          d="M 0 120 C 50 118, 92 104, 108 92 C 120 83, 106 79, 90 78 C 76 77, 85 73, 105 72 C 130 71, 150 74, 200 82"
          stroke="#C5CCC6"
          strokeWidth="14"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 0 120 C 50 118, 92 104, 108 92 C 120 83, 106 79, 90 78 C 76 77, 85 73, 105 72 C 130 71, 150 74, 200 82"
          stroke="#E6EAE6"
          strokeWidth="11"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Highway Road Center Dashed Line */}
        <path
          d="M 0 120 C 50 118, 92 104, 108 92 C 120 83, 106 79, 90 78 C 76 77, 85 73, 105 72 C 130 71, 150 74, 200 82"
          stroke="#FFFFFF"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          strokeLinecap="round"
        />

        {/* Left Foreground Pine Trees (Crisp & Editorial) */}
        <g fill="#7A8D80">
          {/* Foreground Tree 1 (Tall Left) */}
          <path d="M 28 72 L 34 85 L 22 85 Z" />
          <path d="M 28 80 L 37 96 L 19 96 Z" />
          <path d="M 28 90 L 41 110 L 15 110 Z" />
          <rect x="26.5" y="110" width="3" height="6" fill="#6A7A6F" />

          {/* Foreground Tree 2 (Mid Left) */}
          <path d="M 45 78 L 50 89 L 40 89 Z" />
          <path d="M 45 85 L 53 98 L 37 98 Z" />
          <path d="M 45 93 L 56 110 L 34 110 Z" />
          <rect x="43.5" y="110" width="3" height="5" fill="#6A7A6F" />
        </g>
      </svg>
    </div>
  );
};
