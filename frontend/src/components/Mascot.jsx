import React from 'react';

/**
 * Mnemo — the bouncy blob mascot.
 * moods: 'idle' | 'thinking' | 'talking' | 'happy'
 */
const Mascot = ({ mood = 'idle', size = 56, className = '' }) => {
  const moodClass = `mascot-${mood}`;

  return (
    <div
      className={`mascot ${moodClass} ${className}`}
      style={{ width: size, height: size }}
    >
      <div className="mascot-blob">
        <div className="mascot-eye mascot-eye-left" />
        <div className="mascot-eye mascot-eye-right" />
        <div className="mascot-mouth" />
      </div>
      {mood === 'thinking' && (
        <>
          <span className="mascot-dot mascot-dot-1" />
          <span className="mascot-dot mascot-dot-2" />
          <span className="mascot-dot mascot-dot-3" />
        </>
      )}
    </div>
  );
};

export default Mascot;
