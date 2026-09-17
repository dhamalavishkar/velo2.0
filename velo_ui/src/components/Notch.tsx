import { motion, AnimatePresence } from 'motion/react';
import { useNotch } from '../context/NotchContext';
import { AuroraGlow } from './AuroraGlow';
import { Waveform } from './Waveform';
import { TranscriptionFeed } from './TranscriptionFeed';
import { ToolStatusCard } from './ToolStatusCard';
import { PermissionPrompt } from './PermissionPrompt';
import { NotificationCard } from './NotificationCard';
import { ActivationPop } from './ActivationPop';
import { Mic, X, Sparkles } from 'lucide-react';

const springPhysics = {
  type: 'spring' as const,
  stiffness: 100,
  damping: 18,
  mass: 1,
};

// Gemini-like logo component
const GeminiLogo = () => (
  <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
    <path
      d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"
      fill="currentColor"
    />
    <path
      d="M7 7c0-1.1.9-2 2-2h6c1.1 0 2 .9 2 2v6c0 1.1-.9 2-2 2H9c-1.1 0-2-.9-2-2V7zm2 2v2h4V9H9zm0 4v2h4v-2H9z"
      fill="currentColor"
      opacity="0.6"
    />
  </svg>
);

export const Notch = () => {
  const { 
    state, 
    transcription, 
    permissionQueue, 
    toolStatus,
    notification,
    activationPhrase
  } = useNotch();

  const isExpanded = state !== 'idle';
  let width = 140;
  let height = 35;

  if (isExpanded) {
    width = 420;
    if (state === 'permission') height = 160;
    else if (state === 'notification') height = 100;
    else if (state === 'activation') height = 80;
    else height = 140;
  }

  let shadow = '0px 0px 0px 0px rgba(0,0,0,0)';
  if (isExpanded) {
    if (state === 'listening') {
      shadow = '0px 10px 40px -10px rgba(41,121,255,0.7), 0px 0px 20px rgba(41,121,255,0.4)';
    } else if (state === 'permission') {
      shadow = '0px 10px 40px -10px rgba(255,23,68,0.8), 0px 0px 20px rgba(255,23,68,0.5)';
    } else if (state === 'notification') {
      const sentiment = notification?.sentiment || 'ambient';
      if (sentiment === 'ambient') {
        shadow = '0px 10px 40px -10px rgba(41,121,255,0.7), 0px 0px 20px rgba(41,121,255,0.4)';
      } else if (sentiment === 'urgent') {
        shadow = '0px 10px 40px -10px rgba(255,23,68,0.8), 0px 0px 20px rgba(255,23,68,0.5)';
      } else if (sentiment === 'media') {
        shadow = '0px 10px 30px -10px rgba(29,185,84,0.4)';
      }
    } else if (state === 'activation') {
      shadow = '0px 10px 40px -10px rgba(255,0,128,0.8), 0px 0px 20px rgba(255,0,128,0.5)';
    } else {
      shadow = '0px 10px 30px -10px rgba(29,185,84,0.4)';
    }
  }

  return (
    <div className="flex w-full justify-center pt-6 select-none relative z-50">
      <motion.div
        initial={false}
        animate={{
          width,
          height,
          boxShadow: shadow,
        }}
        transition={{
          ...springPhysics,
          boxShadow: { duration: 0.5, ease: 'easeOut' },
        }}
        className="relative bg-black/60 rounded-[40px] border border-white/10 overflow-hidden flex items-center justify-center shadow-2xl"
        style={{
          backdropFilter: 'blur(40px)',
          willChange: 'width, height, transform, box-shadow',
        }}
        onMouseEnter={() => (window as any).electronAPI?.setClickThrough(false)}
        onMouseLeave={() => (window as any).electronAPI?.setClickThrough(true)}
      >
        {/* Notch camera simulation (idle only) */}
        <AnimatePresence>
          {!isExpanded && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.2 }}
              className="absolute right-4 w-3 h-3 rounded-full bg-white/5 border border-white/10 shadow-inner"
            />
          )}
        </AnimatePresence>

        {/* Aurora Glow for expanded states */}
        <AnimatePresence>
          {isExpanded && state === 'listening' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <AuroraGlow color="bg-[#2979FF]" />
            </motion.div>
          )}
          {isExpanded && state === 'permission' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <AuroraGlow color="bg-[#FF1744]" />
            </motion.div>
          )}
          {isExpanded && state === 'expanded' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <AuroraGlow color="bg-[#1DB954]" />
            </motion.div>
          )}
          {isExpanded && state === 'notification' && notification && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <AuroraGlow color={
                notification.sentiment === 'ambient' ? 'bg-[#2979FF]' :
                notification.sentiment === 'urgent' ? 'bg-[#FF1744]' :
                'bg-[#1DB954]'
              } />
            </motion.div>
          )}
          {isExpanded && state === 'activation' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0">
              <AuroraGlow color="bg-[#FF0080]" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Content */}
        <AnimatePresence mode="wait">
          {/* Idle state - capsule with Gemini logo */}
          {!isExpanded && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ ...springPhysics, delay: 0.1 }}
              className="flex items-center gap-3 px-6"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#EC4899] flex items-center justify-center shadow-lg shadow-[#8B5CF6]/30">
                <GeminiLogo />
              </div>
              <span className="text-white text-sm font-medium tracking-wide hidden sm:block">VELO</span>
            </motion.div>
          )}

          {/* Activation state - pink pop-out for "Hi Velo" */}
          {state === 'activation' && activationPhrase && (
            <motion.div
              key="activation"
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: -10 }}
              transition={{ ...springPhysics, delay: 0.05 }}
              className="absolute inset-0 flex items-center justify-between px-6 z-10 w-full"
            >
              <ActivationPop phrase={activationPhrase} />
            </motion.div>
          )}

          {/* Listening state - waveform */}
          {state === 'listening' && (
            <motion.div
              key="listening"
              initial={{ opacity: 0, scale: 0.95, y: 5 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -5 }}
              transition={{ ...springPhysics, delay: 0.05 }}
              className="absolute inset-0 flex items-center justify-between px-6 z-10 w-full"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#2979FF]/20 flex items-center justify-center border border-[#2979FF]/30 animate-pulse">
                  <Mic className="w-4 h-4 text-[#2979FF]" />
                </div>
                <span className="text-white text-sm font-semibold tracking-wide">Listening...</span>
              </div>
              <Waveform />
            </motion.div>
          )}

          {/* Notification state - iOS 27 style cards */}
          {state === 'notification' && notification && (
            <motion.div
              key={`notification-${notification.id}`}
              initial={{ opacity: 0, scale: 0.95, y: 5 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -5 }}
              transition={{ ...springPhysics, delay: 0.05 }}
              className="absolute inset-0 flex items-center justify-between px-6 z-10 w-full"
            >
              <NotificationCard notification={notification} />
            </motion.div>
          )}

          {/* Expanded state - transcription feed */}
          {state === 'expanded' && (
            <motion.div
              key="expanded"
              initial={{ opacity: 0, scale: 0.95, y: 5 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -5 }}
              transition={{ ...springPhysics, delay: 0.05 }}
              className="absolute inset-0 flex flex-col px-6 py-4 z-10 w-full"
            >
              <div className="flex items-center justify-between w-full mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#1DB954]/20 flex items-center justify-center border border-[#1DB954]/30">
                    <Sparkles className="w-4 h-4 text-[#1DB954]" />
                  </div>
                  <span className="text-white text-sm font-semibold tracking-wide">VELO</span>
                </div>
                <button
                  onClick={() => (window as any).electronAPI?.setClickThrough(true)}
                  className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-4 h-4 text-white/60" />
                </button>
              </div>
              <TranscriptionFeed text={transcription} />
              {toolStatus && <ToolStatusCard status={toolStatus} />}
            </motion.div>
          )}

          {/* Permission state - prompt */}
          {state === 'permission' && permissionQueue.length > 0 && (
            <motion.div
              key={`permission-${permissionQueue[0].id}`}
              initial={{ opacity: 0, scale: 0.95, y: 5 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -5 }}
              transition={{ ...springPhysics, delay: 0.05 }}
              className="absolute inset-0 flex flex-col px-6 py-4 z-10 w-full"
            >
              <PermissionPrompt
                request={permissionQueue[0]}
                onAllow={(id) => window.dispatchEvent(new CustomEvent('permission-response', { detail: { id, allowed: true } }))}
                onDeny={(id) => window.dispatchEvent(new CustomEvent('permission-response', { detail: { id, allowed: false } }))}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};