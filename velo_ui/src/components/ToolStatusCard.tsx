import { motion } from 'motion/react';
import type { ToolStatus } from '../types/notch';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export const ToolStatusCard = ({ status }: { status: ToolStatus }) => {
  const icons = {
    pending: Loader2,
    executing: Loader2,
    success: CheckCircle,
    error: XCircle,
  };
  const Icon = icons[status.status];

  const colors = {
    pending: 'text-white/60',
    executing: 'text-[#2979FF]',
    success: 'text-[#1DB954]',
    error: 'text-[#FF1744]',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, height: 0 }}
      animate={{ opacity: 1, y: 0, height: 'auto' }}
      exit={{ opacity: 0, y: -10, height: 0 }}
      className="mt-3 p-3 rounded-xl bg-white/5 border border-white/10 overflow-hidden"
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${colors[status.status]} animate-${status.status === 'executing' || status.status === 'pending' ? 'spin' : 'none'}`} />
        <span className="text-white text-xs font-medium uppercase tracking-wider">
          {status.tool}
        </span>
        <span className={`text-xs ${colors[status.status]}`}>
          {status.status === 'executing' ? 'Running...' : status.status === 'pending' ? 'Pending...' : status.status}
        </span>
      </div>
      {(status.output || status.error) && (
        <pre className="text-white/70 text-xs font-mono whitespace-pre-wrap break-words max-h-24 overflow-y-auto">
          {status.output || status.error}
        </pre>
      )}
    </motion.div>
  );
};