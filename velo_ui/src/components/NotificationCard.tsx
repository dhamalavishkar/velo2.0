import { motion } from 'motion/react';
import type { NotificationItem, NotificationSentiment } from '../types/notch';
import { Bell, AlertTriangle, Music } from 'lucide-react';

interface NotificationCardProps {
  notification: NotificationItem;
}

const sentimentConfig: Record<NotificationSentiment, { icon: typeof Bell; color: string; bg: string; border: string }> = {
  ambient: { icon: Bell, color: 'text-[#2979FF]', bg: 'bg-[#2979FF]/20', border: 'border-[#2979FF]/30' },
  urgent: { icon: AlertTriangle, color: 'text-[#FF1744]', bg: 'bg-[#FF1744]/20', border: 'border-[#FF1744]/30' },
  media: { icon: Music, color: 'text-[#1DB954]', bg: 'bg-[#1DB954]/20', border: 'border-[#1DB954]/30' },
};

export const NotificationCard = ({ notification }: NotificationCardProps) => {
  const config = sentimentConfig[notification.sentiment];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 5 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -5 }}
      className="flex items-center gap-4 w-full"
    >
      <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${config.bg} ${config.color} ${config.border}`}>
        <Icon className="w-5 h-5" />
      </div>
      <span className="text-white text-sm font-semibold tracking-wide flex-1 leading-snug text-left">
        {notification.summary}
      </span>
    </motion.div>
  );
};