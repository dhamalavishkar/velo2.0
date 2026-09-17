import { motion } from 'motion/react';
import type { PermissionRequest } from '../types/notch';
import { AlertTriangle, Check, X, Shield } from 'lucide-react';

interface PermissionPromptProps {
  request: PermissionRequest;
  onAllow: (id: string) => void;
  onDeny: (id: string) => void;
}

const riskColors = {
  low: 'text-[#1DB954] border-[#1DB954]/30 bg-[#1DB954]/10',
  medium: 'text-[#FFAA00] border-[#FFAA00]/30 bg-[#FFAA00]/10',
  high: 'text-[#FF1744] border-[#FF1744]/30 bg-[#FF1744]/10',
};

const riskIcons = {
  low: Shield,
  medium: AlertTriangle,
  high: AlertTriangle,
};

export const PermissionPrompt = ({ request, onAllow, onDeny }: PermissionPromptProps) => {
  const RiskIcon = riskIcons[request.risk];
  const riskClass = riskColors[request.risk];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 5 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -5 }}
      className="flex flex-col h-full"
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${riskClass}`}>
          <RiskIcon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-semibold tracking-wide truncate">
            Permission Required
          </p>
          <p className="text-white/60 text-xs truncate">{request.description}</p>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium uppercase ${riskClass}`}>
          {request.risk}
        </span>
      </div>

      <div className="bg-white/5 rounded-lg p-3 mb-3 border border-white/10 max-h-32 overflow-y-auto">
        <p className="text-white/70 text-xs font-mono whitespace-pre-wrap break-words">
          {JSON.stringify(request.args, null, 2)}
        </p>
      </div>

      <div className="flex items-center justify-end gap-2 mt-auto">
        <button
          onClick={() => onDeny(request.id)}
          className="px-4 py-2 rounded-lg text-white/70 text-sm font-medium hover:bg-white/10 transition-colors border border-white/10"
        >
          <X className="w-3.5 h-3.5 mr-1.5 inline" /> Deny
        </button>
        <button
          onClick={() => onAllow(request.id)}
          className="px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors bg-[#FF1744]/20 border border-[#FF1744]/30 hover:bg-[#FF1744]/30"
        >
          <Check className="w-3.5 h-3.5 mr-1.5 inline" /> Allow
        </button>
      </div>
    </motion.div>
  );
};