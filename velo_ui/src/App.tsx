import { NotchProvider } from './context/NotchContext';
import { Notch } from './components';
import { useVelo } from './hooks';
import './index.css';

function App() {
  useVelo();

  return (
    <NotchProvider>
      <div
        className="w-full h-screen bg-transparent overflow-hidden relative"
        style={{ backgroundColor: 'transparent' }}
      >
        <div
          className="absolute top-0 w-full h-8 pointer-events-none z-50"
          style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
        />
        <Notch />
      </div>
    </NotchProvider>
  );
}

export default App;