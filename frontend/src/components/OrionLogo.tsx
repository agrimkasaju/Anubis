import React from 'react';

interface OrionLogoProps {
  className?: string;
  size?: number;
}

export const OrionLogo: React.FC<OrionLogoProps> = ({ className = '', size = 28 }) => {
  return (
    <div
      className={`relative flex items-center justify-center flex-shrink-0 select-none ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-[0_0_8px_rgba(6,182,212,0.6)]"
      >
        <defs>
          <radialGradient id="nexusGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#06090F" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Ambient Glow */}
        <circle cx="50" cy="50" r="44" fill="url(#nexusGlow)" />

        {/* Constellation Ties */}
        <g stroke="#22D3EE" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.85">
          {/* Hourglass Frame */}
          <line x1="26" y1="22" x2="74" y2="22" />
          <line x1="74" y1="22" x2="58" y2="50" />
          <line x1="58" y1="50" x2="70" y2="78" />
          <line x1="70" y1="78" x2="30" y2="78" />
          <line x1="30" y1="78" x2="42" y2="50" />
          <line x1="42" y1="50" x2="26" y2="22" />
          {/* Diagonal Struts */}
          <line x1="26" y1="22" x2="50" y2="50" strokeOpacity="0.4" strokeDasharray="3 3" />
          <line x1="74" y1="22" x2="50" y2="50" strokeOpacity="0.4" strokeDasharray="3 3" />
          <line x1="30" y1="78" x2="50" y2="50" strokeOpacity="0.4" strokeDasharray="3 3" />
          <line x1="70" y1="78" x2="50" y2="50" strokeOpacity="0.4" strokeDasharray="3 3" />
          {/* Orion's Belt Core */}
          <line x1="42" y1="50" x2="58" y2="50" stroke="#34D399" strokeWidth="2.2" />
        </g>

        {/* Central Quantum Nexus Rings */}
        <circle cx="50" cy="50" r="14" stroke="#06B6D4" strokeWidth="1.5" strokeOpacity="0.6" fill="none" />
        <circle cx="50" cy="50" r="9" stroke="#10B981" strokeWidth="1.2" strokeOpacity="0.8" fill="none" />

        {/* Corner Stars */}
        <circle cx="26" cy="22" r="3.8" fill="#F59E0B" /> {/* Betelgeuse */}
        <circle cx="74" cy="22" r="3.2" fill="#22D3EE" /> {/* Bellatrix */}
        <circle cx="30" cy="78" r="3.0" fill="#22D3EE" /> {/* Saiph */}
        <circle cx="70" cy="78" r="4.0" fill="#38BDF8" /> {/* Rigel */}

        {/* Quantitative Belt Pillars */}
        <circle cx="42" cy="50" r="2.8" fill="#10B981" /> {/* Fundamentals */}
        <circle cx="50" cy="50" r="3.8" fill="#FFFFFF" className="animate-pulse" /> {/* Composite Core */}
        <circle cx="58" cy="50" r="2.8" fill="#06B6D4" /> {/* Microstructure */}
      </svg>
    </div>
  );
};
