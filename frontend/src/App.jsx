// frontend/src/App.jsx
import React, { useState } from 'react';
import { MainLayout } from './components/layout/MainLayout';
import FopagAuditDashboard from './components/FopagAuditDashboard';
import AdiantamentoDashboard from './components/AdiantamentoDashboard';
import { Activity, CheckCircle2, TrendingUp } from 'lucide-react';
import { StatCard } from './components/ui/StatCard';

function App() {
  const [currentModule, setCurrentModule] = useState('HOME');

  const renderContent = () => {
    switch (currentModule) {
      case 'FOPAG':
        return <FopagAuditDashboard />;
      case 'ADIANTAMENTO':
        // A prop onBackToMenu não é mais necessária pois temos a Sidebar, 
        // mas mantemos compatibilidade se o componente interno usar.
        return <AdiantamentoDashboard onBackToMenu={() => setCurrentModule('HOME')} />;
      default:
        return <HomeWelcome onNavigate={setCurrentModule} />;
    }
  };

  return (
    <MainLayout activeModule={currentModule} onChangeModule={setCurrentModule}>
      {renderContent()}
    </MainLayout>
  );
}

// Componente da Home (Dashboard Inicial)
const HomeWelcome = ({ onNavigate }) => (
  <div className="space-y-8">
    <div className="flex justify-between items-end">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Bem-vindo ao GFS</h1>
        <p className="text-slate-500 mt-2">Central Unificada de Auditoria e Controle de RH.</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium text-slate-400">{new Date().toLocaleDateString('pt-BR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
    </div>

    {/* Cards de Atalho Rápido */}
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div onClick={() => onNavigate('ADIANTAMENTO')} className="cursor-pointer">
        <StatCard title="Módulo Adiantamento" value="Auditoria Lote" icon={CalendarClock} color="blue" subtext="Dia 15 e 20" />
      </div>
      <div onClick={() => onNavigate('FOPAG')} className="cursor-pointer">
        <StatCard title="Módulo Folha Mensal" value="Auditoria FOPAG" icon={Calculator} color="purple" subtext="Cálculos Complexos" />
      </div>
      <StatCard title="Status do Sistema" value="Operacional" icon={Activity} color="green" subtext="v4.0.0 Stable" />
    </div>

    {/* Área de Novidades ou Avisos (Opcional) */}
    <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm">
      <h3 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
        <TrendingUp size={20} className="text-blue-600" />
        Atualizações Recentes
      </h3>
      <ul className="space-y-4">
        <li className="flex gap-4 items-start">
          <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <CheckCircle2 size={14} className="text-green-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Cálculo de Consignado Ajustado</p>
            <p className="text-sm text-slate-500">Agora o desconto do consignado respeita a proporcionalidade do valor líquido recebido.</p>
          </div>
        </li>
        <li className="flex gap-4 items-start">
          <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <CheckCircle2 size={14} className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Unificação de Plataforma</p>
            <p className="text-sm text-slate-500">FOPAG e Adiantamento agora operam no mesmo motor de processamento.</p>
          </div>
        </li>
      </ul>
    </div>
  </div>
);

// Ícones para o componente Home (importados aqui para brevidade)
import { Calculator, CalendarClock } from 'lucide-react';

export default App;