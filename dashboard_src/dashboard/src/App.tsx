import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CalendarView from './pages/CalendarView';
import AppointmentDetail from './pages/AppointmentDetail';
import Clients from './pages/Clients';
import ClientProfile from './pages/ClientProfile';
import Analytics from './pages/Analytics';
import Live from './pages/Live';

const WestpacBankerDashboard = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/appointment" element={<Dashboard />} />
          <Route path="/calendar" element={<CalendarView />} />
          <Route path="/appointment/:id" element={<AppointmentDetail />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/clients/:id" element={<ClientProfile />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/live" element={<Live />} />
          <Route path="*" element={<Navigate to="/appointment" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

export default WestpacBankerDashboard;
