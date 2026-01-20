// src/App.jsx
import React, { useState } from 'react';
import FopagAuditDashboard from './components/FopagAuditDashboard';
import AdiantamentoDashboard from './components/AdiantamentoDashboard';
import logoProjecont from './assets/logoProjecont.jpeg'; // Garanta que a logo esteja aqui
import { Calculator, CalendarClock, ChevronRight } from 'lucide-react';

function App() {
  // Estado para controlar qual módulo está ativo: 'HOME', 'FOPAG', 'ADIANTAMENTO'
  const [currentModule, setCurrentModule] = useState('HOME');

  // Renderização Condicional
  if (currentModule === 'FOPAG') {
    return (
      <div>
        {/* Botão flutuante ou Header para voltar */}
        <div className="bg-slate-900 text-white px-4 py-2 flex justify-between items-center text-sm">
          <span>Módulo: <b>Auditoria FOPAG</b></span>
          <button onClick={() => setCurrentModule('HOME')} className="hover:text-blue-300 underline">
            Voltar ao Menu
          </button>
        </div>
        <FopagAuditDashboard />
      </div>
    );
  }

  if (currentModule === 'ADIANTAMENTO') {
    // Passamos a função de voltar como prop para o dashboard usar se quiser
    return <AdiantamentoDashboard onBackToMenu={() => setCurrentModule('HOME')} />;
  }

  // TELA INICIAL (MENU)
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center font-sans p-6">

      <div className="text-center mb-12 animate-fade-in-up">
        <img src={logoProjecont} alt="Projecont" className="w-24 h-24 rounded-xl mx-auto mb-6 shadow-lg" />
        <h1 className="text-4xl font-extrabold text-slate-900 mb-3">
          GLF <span className="text-blue-600">Auditor Unificado</span>
        </h1>
        <p className="text-lg text-slate-600 max-w-md mx-auto">
          Plataforma centralizada de auditoria e automação de Departamento Pessoal.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-4xl">

        {/* CARD ADIANTAMENTO */}
        <button
          onClick={() => setCurrentModule('ADIANTAMENTO')}
          className="group relative bg-white p-8 rounded-2xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-200 transition-all duration-300 text-left"
        >
          <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
            <CalendarClock size={100} className="text-blue-600" />
          </div>
          <div className="bg-blue-50 w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <CalendarClock size={32} className="text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2 group-hover:text-blue-700 transition-colors">
            Auditoria de Adiantamento
          </h2>
          <p className="text-slate-500 mb-6 leading-relaxed">
            Geração em lote, cálculo de elegibilidade, conferência de flags e integração com RPA de consignados.
          </p>
          <div className="flex items-center font-bold text-blue-600 group-hover:translate-x-2 transition-transform">
            Acessar Módulo <ChevronRight size={20} className="ml-1" />
          </div>
        </button>

        {/* CARD FOPAG */}
        <button
          onClick={() => setCurrentModule('FOPAG')}
          className="group relative bg-white p-8 rounded-2xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-purple-200 transition-all duration-300 text-left"
        >
          <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
            <Calculator size={100} className="text-purple-600" />
          </div>
          <div className="bg-purple-50 w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <Calculator size={32} className="text-purple-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2 group-hover:text-purple-700 transition-colors">
            Auditoria Mensal (FOPAG)
          </h2>
          <p className="text-slate-500 mb-6 leading-relaxed">
            Análise detalhada da folha mensal, cálculo de impostos (INSS/IRRF), benefícios e regras complexas.
          </p>
          <div className="flex items-center font-bold text-purple-600 group-hover:translate-x-2 transition-transform">
            Acessar Módulo <ChevronRight size={20} className="ml-1" />
          </div>
        </button>

      </div>

      <div className="mt-16 text-slate-400 text-sm">
        &copy; 2025 Projecont RH Tools • Versão 4.0 Unified
      </div>
    </div>
  );
}

export default App;