import React from 'react';
import { Brain, Rocket } from 'lucide-react';

const ModeBadge = ({ mode }) => {
  if (mode === 'Recall') {
    return (
      <div className="inline-flex items-center gap-1.5 mb-3 w-fit bg-teal text-white px-3.5 py-1.5 rounded-full text-xs font-bold font-display tracking-wide shadow-[3px_3px_0px_rgba(0,153,132,0.5)] border-2 border-white/40">
        <Brain className="w-3.5 h-3.5" />
        <span>From your notes</span>
      </div>
    );
  }
  if (mode === 'Elaboration') {
    return (
      <div className="inline-flex items-center gap-1.5 mb-3 w-fit bg-pink text-white px-3.5 py-1.5 rounded-full text-xs font-bold font-display tracking-wide shadow-[3px_3px_0px_rgba(232,64,138,0.5)] border-2 border-white/40">
        <Rocket className="w-3.5 h-3.5" />
        <span>Beyond your notes</span>
      </div>
    );
  }
  return null;
};

export default ModeBadge;