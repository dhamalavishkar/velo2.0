import { useWebSocket } from './useWebSocket';
import { useNotchController } from './useNotchController';

export const useVelo = () => {
  useWebSocket();
  useNotchController();
};