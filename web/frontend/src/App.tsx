import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from '@/components/ui/toaster';
import Layout from '@/components/layout/Layout';
import Dashboard from '@/pages/Dashboard';
import Trading from '@/pages/Trading';
import Charts from '@/pages/Charts';
import MLPanel from '@/pages/MLPanel';
import Strategies from '@/pages/Strategies';
import Indicators from '@/pages/Indicators';
import Positions from '@/pages/Positions';
import Analytics from '@/pages/Analytics';
import Settings from '@/pages/Settings';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchInterval: 5000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="App min-h-screen bg-gray-900 text-white">
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/trading" element={<Trading />} />
              <Route path="/charts" element={<Charts />} />
              <Route path="/ml" element={<MLPanel />} />
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/positions" element={<Positions />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
          <Toaster />
        </div>
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
