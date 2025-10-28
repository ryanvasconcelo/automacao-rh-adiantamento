// src/App.jsx (Versão Completa e Final)

import React, { useState, useMemo, useEffect } from 'react';
import { ChevronLeft, ChevronsRight, FileDown, Loader, Search, CheckSquare, Square, XCircle, CheckCircle, AlertTriangle, UploadCloud } from 'lucide-react';
import logoProjecont from './assets/logoProjecont.jpeg';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Componente para telas de Carregamento
const LoadingScreen = ({ message }) => (
  <div className="flex flex-col items-center justify-center text-center p-8">
    <Loader className="w-12 h-12 text-blue-600 animate-spin mb-4" />
    <p className="text-lg font-semibold text-gray-700">{message}</p>
  </div>
);

// Componente para mensagens de Erro
const ErrorScreen = ({ message, onRetry }) => (
  <div className="text-center p-8 bg-red-50 rounded-lg">
    <XCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
    <p className="text-lg font-semibold text-red-800 mb-4">{message}</p>
    <button onClick={onRetry} className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg">
      Tentar Novamente
    </button>
  </div>
);

const Alert = ({ message, type = 'error', onClose }) => {
  const bgColor = type === 'success' ? 'bg-green-50' : 'bg-red-50';
  const borderColor = type === 'success' ? 'border-green-300' : 'border-red-300';
  const textColor = type === 'success' ? 'text-green-800' : 'text-red-800';
  const Icon = type === 'success' ? CheckCircle : AlertTriangle;

  return (
    <div className={`border-l-4 ${borderColor} ${bgColor} p-4 mb-6 rounded-md shadow-sm flex justify-between items-center`}>
      <div className="flex items-center">
        <Icon className={`h-5 w-5 ${textColor} mr-3`} aria-hidden="true" />
        <p className={`text-sm font-medium ${textColor}`}>{message}</p>
      </div>
      {onClose && ( // Renderiza o botão apenas se onClose for fornecido
        <button onClick={onClose} className={`ml-4 p-1 rounded-md ${bgColor} hover:bg-opacity-80 focus:outline-none focus:ring-2 focus:ring-offset-2 ${type === 'success' ? 'focus:ring-green-600' : 'focus:ring-red-600'}`}>
          <XCircle className={`h-5 w-5 ${textColor}`} aria-hidden="true" />
        </button>
      )}
    </div>
  );
};
const SuccessAlert = ({ message, onClose }) => <Alert message={message} type="success" onClose={onClose} />;
const ErrorAlert = ({ message, onClose }) => <Alert message={message} type="error" onClose={onClose} />;

// --- Componente Principal App ---
const App = () => {
  const [view, setView] = useState('SELECTION');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');
  // --- CORREÇÃO APLICADA AQUI ---
  const [successMessage, setSuccessMessage] = useState(''); // <-- Adicionada declaração
  // -----------------------------
  const [auditData, setAuditData] = useState([]);
  const [selectedCompanyCode, setSelectedCompanyCode] = useState(null);
  const [selectedDay, setSelectedDay] = useState('15');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  useEffect(() => {
    let timer;
    if (successMessage || error) {
      timer = setTimeout(() => {
        setSuccessMessage('');
        setError('');
      }, 5000);
    }
    return () => { if (timer) clearTimeout(timer); };
  }, [successMessage, error]); // Agora as dependências existem

  const resetFlow = () => {
    setView('SELECTION'); setAuditData([]); setSelectedCompanyCode(null);
    setError(''); setIsLoading(false); setSuccessMessage(''); // Inclui reset do successMessage
  };

  const handleRunDayAudit = async () => {
    setIsLoading(true); setLoadingMessage('Auditando todas as empresas...'); setError(''); setSuccessMessage('');
    try {
      const response = await fetch(`${API_URL}/audit/day`, {
        // --- CORREÇÃO APLICADA AQUI ---
        method: 'POST', // <-- Garante que o método é POST
        // -----------------------------
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          day: parseInt(selectedDay),
          month: parseInt(selectedMonth),
          year: parseInt(selectedYear),
        }),
      });
      const data = await response.json();
      if (response.ok) { setAuditData(data); setView('SUMMARY'); }
      else { setError(data.detail || 'Erro na API de auditoria.'); }
    } catch (err) { setError('Falha na comunicação com a API.'); }
    finally { setIsLoading(false); }
  };

  // REMOVIDO handleApplyCorrections pois usamos RPA futuramente

  const handleImportConsignments = async (companyCodes = null) => {
    setIsLoading(true); setLoadingMessage('Iniciando importação de consignados (RPA)...'); setError(''); setSuccessMessage('');
    try {
      const response = await fetch(`${API_URL}/rpa/import-consignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year: parseInt(selectedYear), month: parseInt(selectedMonth), company_codes: companyCodes }),
      });
      const result = await response.json();
      if (response.ok && result.status === 'success') {
        setSuccessMessage(result.message);
        await handleRunDayAudit(); // Reexecuta auditoria para atualizar status
      } else { setError(result.detail || result.message || 'Falha ao importar consignados.'); }
    } catch (err) { setError('Erro de rede ao acionar a importação.'); }
    finally { setIsLoading(false); }
  };

  const handleGenerateReports = async () => {
    setIsLoading(true); setLoadingMessage('Acionando RPA para gerar relatórios...'); setError(''); setSuccessMessage('');
    try {
      const response = await fetch(`${API_URL}/reports/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          month: parseInt(selectedMonth), year: parseInt(selectedYear),
          data: auditData.map(row => ({ matricula: row.matricula, nome: row.nome, empresaCodigo: row.empresaCodigo, empresaNome: row.empresaNome }))
        }),
      });
      const result = await response.json(); // Espera JSON, não blob
      if (response.ok && result.status === 'success') {
        setSuccessMessage(result.message || 'RPA de geração iniciado (simulado).');
        // Não há download nesta fase, apenas confirmação
      } else { setError(result.detail || 'Falha ao acionar RPA de geração.'); }
    } catch (err) { setError('Erro de rede ao acionar geração de relatórios.'); }
    finally { setIsLoading(false); }
  };

  const groupedSummaryData = useMemo(() => {
    if (!auditData || auditData.length === 0) return {};
    return auditData.reduce((acc, row) => {
      const { empresaCode, empresaNome } = row;
      if (!acc[empresaCode]) {
        acc[empresaCode] = { nome: empresaNome, code: empresaCode, total: 0, divergencia: 0, removido: 0, grave: 0, corrigido: 0 };
      }
      acc[empresaCode].total++;
      if (row.analise.includes('Divergência')) acc[empresaCode].divergencia++;
      if (row.analise.includes('Removido')) acc[empresaCode].removido++;
      if (row.analise.includes('INCONSISTÊNCIA GRAVE') || row.analise.includes('Rescisão')) acc[empresaCode].grave++;
      if (row.analise.includes('Corrigido')) acc[empresaCode].corrigido++;
      return acc;
    }, {});
  }, [auditData]);

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50"><div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between"><div className="flex items-center gap-4"><img src={logoProjecont} alt="Logo" className='w-10 h-10 rounded-md' /><h1 className="text-xl font-semibold text-gray-900">Robo Auditor RH - Projecont</h1></div></div></header>
      <main className="max-w-7xl mx-auto px-6 py-8">
        {view !== 'SELECTION' && (<button onClick={resetFlow} className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800 mb-6"><ChevronLeft className="w-4 h-4" />Voltar ao Início</button>)}
        {error && <ErrorScreen message={error} onRetry={resetFlow} />}
        {isLoading && <LoadingScreen message={loadingMessage} />}
        {!isLoading && !error && (
          <>
            {view === 'SELECTION' && (<SelectionView selectedDay={selectedDay} setSelectedDay={setSelectedDay} selectedMonth={selectedMonth} setSelectedMonth={setSelectedMonth} selectedYear={selectedYear} setSelectedYear={setSelectedYear} onAudit={handleRunDayAudit} />)}
            {view === 'SUMMARY' && (<SummaryView summaryData={groupedSummaryData} onSelectCompany={(code) => { setSelectedCompanyCode(code); setView('DETAIL'); }} onGenerateReports={() => setView('GENERATION')} />)}
            {view === 'DETAIL' && (
              <DetailView
                companyData={auditData.filter(row => row.empresaCode === selectedCompanyCode)}
                companyName={groupedSummaryData[selectedCompanyCode]?.nome || ''}
                empresaCodigo={auditData.find(row => row.empresaCode === selectedCompanyCode)?.empresaCodigo}
                onBack={() => setView('SUMMARY')}
              />
            )}
            {view === 'GENERATION' && (<GenerationView onConfirm={handleGenerateReports} onBack={() => setView('SUMMARY')} companies={Object.values(groupedSummaryData)} />)}
          </>
        )}
      </main>
    </div>
  );
};

// --- Componentes de Visão ---

const SelectionView = ({ selectedDay, setSelectedDay, selectedMonth, setSelectedMonth, selectedYear, setSelectedYear, onAudit }) => (
  <div>
    <div className="mb-8"><h2 className="text-3xl font-bold text-gray-900 mb-2">Auditoria de Adiantamento por Lote</h2><p className="text-gray-600">Selecione o dia de pagamento e o período para auditar todas as empresas associadas.</p></div>
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="grid grid-cols-12 gap-4 items-end">
        <div className="col-span-12 md:col-span-3"><label className="block text-sm font-medium text-gray-700 mb-2">Dia de Pagamento</label><select className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" value={selectedDay} onChange={(e) => setSelectedDay(e.target.value)}><option value="15">Dia 15</option><option value="20">Dia 20</option></select></div>
        <div className="col-span-6 md:col-span-3"><label className="block text-sm font-medium text-gray-700 mb-2">Mês</label><input type="number" min="1" max="12" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg" value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)} /></div>
        <div className="col-span-6 md:col-span-3"><label className="block text-sm font-medium text-gray-700 mb-2">Ano</label><input type="number" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg" value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)} /></div>
        <div className="col-span-12 md:col-span-3"><button onClick={onAudit} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-lg shadow-sm">Gerar Auditoria do Dia</button></div>
      </div>
    </div>
  </div>
);
// --- Componente SummaryView (CORRIGIDO) ---
const SummaryView = ({ summaryData, auditData, onSelectCompany, onGenerateReports, onImportConsignments }) => {

  // --- CORREÇÃO APLICADA AQUI ---
  // Adiciona verificação para garantir que auditData é um array antes de usar reduce
  const pendingImports = useMemo(() => {
    if (!Array.isArray(auditData) || auditData.length === 0) return 0; // <-- Verifica se é array e não está vazio
    const importedCodes = new Set();
    return auditData.reduce((count, row) => {
      // Adiciona verificação extra para segurança (row pode ser inválido?)
      if (row && row.empresaCode && !importedCodes.has(row.empresaCode) && !row.consignadoImportado) {
        importedCodes.add(row.empresaCode);
        return count + 1;
      }
      return count;
    }, 0);
  }, [auditData]);

  // --- CORREÇÃO APLICADA AQUI ---
  // Adiciona verificação para garantir que auditData é um array antes de usar find
  const getConsignmentStatus = (companyCode) => {
    if (!Array.isArray(auditData) || auditData.length === 0) return false; // <-- Verifica se é array e não está vazio
    const companyRow = auditData.find(row => row && row.empresaCode === companyCode); // Adiciona verificação extra
    return companyRow ? companyRow.consignadoImportado : false;
  };
  // --- FIM DAS CORREÇÕES ---

  return (
    <div>
      <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
        <h2 className="text-3xl font-bold text-gray-900">Resumo da Auditoria</h2>
        <div className="flex items-center gap-4">
          {/* Botão para Importar Pendentes */}
          <button
            onClick={() => onImportConsignments(null)} // null = todos pendentes
            disabled={pendingImports === 0}
            className={`flex items-center gap-2 font-semibold py-2.5 px-6 rounded-lg shadow-sm transition-colors ${pendingImports > 0
              ? 'bg-orange-500 hover:bg-orange-600 text-white'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
          >
            <UploadCloud className="w-5 h-5" />
            Importar Consignados ({pendingImports} pendentes)
          </button>
          {/* Botão para Gerar Relatórios */}
          <button onClick={onGenerateReports} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-6 rounded-lg shadow-sm">
            Gerar Relatórios <ChevronsRight className="w-5 h-5" />
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Object.values(summaryData).map(company => {
          const isImported = getConsignmentStatus(company.code);
          return (
            <div key={company.code} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col">
              <h3 className="font-bold text-lg text-gray-900 mb-4 truncate">{company.nome}</h3>
              <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                <p><strong>Total:</strong> {company.total}</p>
                <p className={company.grave > 0 ? 'text-red-600' : 'text-gray-600'}><strong>Graves:</strong> {company.grave}</p>
                <p className={company.divergencia > 0 ? 'text-amber-600' : 'text-gray-600'}><strong>Divergências:</strong> {company.divergencia}</p>
                <p><strong>Removidos:</strong> {company.removido}</p>
              </div>
              <div className="flex gap-2 mt-auto">
                {/* Botão de Status/Ação do Consignado */}
                <button
                  onClick={() => !isImported && onImportConsignments([company.code])} // Só permite clicar se não importado
                  className={`flex-1 flex items-center justify-center gap-2 font-semibold py-2 px-4 rounded-lg text-xs transition-colors ${isImported
                    ? 'bg-emerald-100 text-emerald-800 cursor-default'
                    : 'bg-red-100 hover:bg-red-200 text-red-800'
                    }`}
                >
                  {isImported ? <CheckCircle className="w-4 h-4" /> : <UploadCloud className="w-4 h-4" />}
                  {isImported ? 'Consignado OK' : 'Importar Cons.'}
                </button>
                {/* Botão Ver Detalhes */}
                <button onClick={() => onSelectCompany(company.code)} className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-2 px-4 rounded-lg text-xs">
                  Ver Detalhes
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const DetailView = ({ companyData, companyName, empresaCodigo, onApplyCorrections, onBack }) => {
  const [filterAnalise, setFilterAnalise] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRows, setSelectedRows] = useState(new Set());

  useEffect(() => {
    setSelectedRows(new Set());
    setFilterAnalise('all');
    setSearchTerm('');
  }, [companyData]);

  // Formata moeda com arredondamento para 2 casas decimais
  const formatCurrency = (value) => {
    const rounded = Math.round((value || 0) * 100) / 100; // Arredonda para 2 casas decimais
    return rounded.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const metrics = useMemo(() => {
    if (!companyData) return {
      totalFunc: 0,
      totalBruto: 0,
      totalDescontos: 0,
      totalFinal: 0,
      funcionariosElegiveis: 0,
      ok: 0,
      divergencia: 0,
      removidos: 0,
      grave: 0
    };

    // Calcula totais com arredondamento para 2 casas decimais
    const totalBruto = Math.round(companyData.reduce((sum, row) => sum + (row.valorBruto || 0), 0) * 100) / 100;
    const totalDescontos = Math.round(companyData.reduce((sum, row) => sum + (row.desconto || 0), 0) * 100) / 100;
    const totalFinal = Math.round(companyData.reduce((sum, row) => sum + (row.valorFinal || 0), 0) * 100) / 100;

    // Conta funcionários elegíveis (aqueles com status "Elegível" ou análise "OK"/"Corrigido")
    const funcionariosElegiveis = companyData.filter(row =>
      row.status === 'Elegível' ||
      row.analise.includes('OK') ||
      row.analise.includes('Corrigido')
    ).length;

    return {
      totalFunc: companyData.length,
      totalBruto,
      totalDescontos,
      totalFinal,
      funcionariosElegiveis,
      ok: companyData.filter(row => row.analise.includes('OK') || row.analise.includes('Corrigido')).length,
      divergencia: companyData.filter(row => row.analise.includes('Divergência')).length,
      removidos: companyData.filter(row => row.analise.includes('Removido')).length,
      grave: companyData.filter(row => row.analise.includes('INCONSISTÊNCIA GRAVE') || row.analise.includes('Rescisão')).length,
    };
  }, [companyData]);

  const filteredData = useMemo(() => {
    return (companyData || []).filter(row => {
      const analiseLower = row.analise.toLowerCase();
      const matchesFilter = filterAnalise === 'all' ||
        (filterAnalise === 'ok' && (analiseLower.includes('ok') || analiseLower.includes('corrigido'))) ||
        (filterAnalise === 'divergencia' && analiseLower.includes('divergência')) ||
        (filterAnalise === 'removido' && analiseLower.includes('removido')) ||
        (filterAnalise === 'grave' && (analiseLower.includes('inconsistência grave') || analiseLower.includes('rescisão')));
      const matchesSearch = !searchTerm ||
        (row.nome && row.nome.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (row.matricula && row.matricula.includes(searchTerm));
      return matchesFilter && matchesSearch;
    });
  }, [companyData, filterAnalise, searchTerm]);

  const handleSimulateCorrections = () => {
    if (selectedRows.size === 0) {
      alert('Selecione pelo menos um funcionário para aplicar correções.');
      return;
    }

    const confirmMessage = `⚠️ ATENÇÃO: Você está prestes a aplicar correções REAIS no banco de dados Fortes!\n\n` +
      `${selectedRows.size} funcionário(s) selecionado(s)\n` +
      `Empresa: ${companyName}\n\n` +
      `As alterações serão feitas na tabela SEP e a folha será recalculada automaticamente.\n\n` +
      `Deseja continuar?`;

    if (!confirm(confirmMessage)) {
      return;
    }

    // Chama a API real para aplicar correções
    onApplyCorrections(empresaCodigo, Array.from(selectedRows));
  };

  const toggleRow = (matricula) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(matricula)) newSelected.delete(matricula); else newSelected.add(matricula);
    setSelectedRows(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedRows.size === filteredData.length) setSelectedRows(new Set());
    else setSelectedRows(new Set(filteredData.map(row => row.matricula)));
  };

  const getRowColor = (analise) => {
    if (analise.includes('INCONSISTÊNCIA GRAVE') || analise.includes('Rescisão')) return 'bg-red-50 hover:bg-red-100';
    if (analise.includes('Divergência')) return 'bg-amber-50 hover:bg-amber-100';
    if (analise.includes('Removido')) return 'bg-slate-50 hover:bg-slate-100';
    if (analise.includes('Corrigido')) return 'bg-green-50 hover:bg-green-100';
    return 'bg-white hover:bg-gray-50';
  };

  const filterButtons = [
    { key: 'all', label: 'Todos', count: metrics.totalFunc },
    { key: 'ok', label: 'OK', count: metrics.ok },
    { key: 'divergencia', label: 'Divergências', count: metrics.divergencia },
    { key: 'removido', label: 'Removidos', count: metrics.removidos },
    { key: 'grave', label: 'Graves', count: metrics.grave },
  ];

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800 mb-6"><ChevronLeft className="w-4 h-4" />Voltar ao Resumo</button>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">{companyName}</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Valor Bruto (Fortes)</p><p className="text-3xl font-bold text-gray-900">{formatCurrency(metrics.totalBruto)}</p></div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Descontos Consignado</p><p className="text-3xl font-bold text-orange-600">{formatCurrency(metrics.totalDescontos)}</p></div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Valor Líquido (Auditado)</p><p className="text-3xl font-bold text-blue-600">{formatCurrency(metrics.totalFinal)}</p></div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Funcionários Elegíveis</p><p className="text-3xl font-bold text-green-600">{metrics.funcionariosElegiveis}</p></div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {filterButtons.map(btn => (
              <button key={btn.key} onClick={() => setFilterAnalise(btn.key)} className={`px-3 py-1.5 text-sm font-semibold rounded-full ${filterAnalise === btn.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
                {btn.label} <span className={`ml-1 px-2 py-0.5 rounded-full text-xs ${filterAnalise === btn.key ? 'bg-blue-400 text-white' : 'bg-gray-200 text-gray-600'}`}>{btn.count}</span>
              </button>
            ))}
          </div>
          <div className="flex w-full md:w-auto items-center gap-4">
            <div className="relative flex-1"><Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" /><input type="text" placeholder="Buscar por nome ou matrícula..." className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div>
            <button onClick={handleSimulateCorrections} disabled={selectedRows.size === 0} className={`px-6 py-2.5 rounded-lg font-semibold transition-colors ${selectedRows.size > 0 ? 'bg-green-600 hover:bg-green-700 text-white shadow-sm' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>Aplicar {selectedRows.size > 0 ? `(${selectedRows.size})` : ''} Correções</button>
          </div>
        </div>
        <div className="max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10"><tr><th className="px-6 py-3 w-12"><input type="checkbox" className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" onChange={handleSelectAll} checked={filteredData.length > 0 && selectedRows.size === filteredData.length} /></th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Matrícula</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Nome</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Análise</th><th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Valor Fortes</th><th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Valor Auditado</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Observações</th></tr></thead>
            <tbody className="divide-y divide-gray-200">
              {filteredData.map((row) => (
                <tr key={row.matricula} className={`${getRowColor(row.analise)}`}>
                  <td className="px-6 py-4"><button onClick={() => toggleRow(row.matricula)}>{selectedRows.has(row.matricula) ? <CheckSquare className="w-5 h-5 text-blue-600" /> : <Square className="w-5 h-5 text-gray-400" />}</button></td>
                  <td className="px-6 py-4 font-medium text-gray-900">{row.matricula}</td>
                  <td className="px-6 py-4 text-gray-900 font-medium">{row.nome}</td>
                  <td className="px-6 py-4"><span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${row.analise.includes('OK') || row.analise.includes('Corrigido') ? 'bg-emerald-100 text-emerald-800' : row.analise.includes('Divergência') ? 'bg-amber-100 text-amber-800' : row.analise.includes('Removido') ? 'bg-slate-100 text-slate-800' : 'bg-red-100 text-red-800'}`}>{row.analise}</span></td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900">{formatCurrency(row.valorBruto)}</td>
                  <td className="px-6 py-4 text-right font-mono font-semibold text-blue-600">{formatCurrency(row.valorFinal)}</td>
                  <td className="px-6 py-4 text-gray-600 max-w-xs truncate" title={row.observacoes}>{row.observacoes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const GenerationView = ({ onConfirm, onBack, companies }) => (
  <div>
    <button onClick={onBack} className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800 mb-6"><ChevronLeft className="w-4 h-4" /></button>
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
      <FileDown className="w-12 h-12 text-blue-600 mx-auto mb-4" />
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Gerar Relatórios Finais</h2>
      <p className="text-gray-600 mb-6">A ação a seguir irá gerar, compactar e baixar os relatórios para as seguintes empresas:</p>
      <ul className="text-left max-w-md mx-auto bg-gray-50 p-4 rounded-lg border mb-6 list-disc list-inside">
        {companies.map(c => <li key={c.code} className="font-semibold text-gray-800">{c.nome}</li>)}
      </ul>
      <button onClick={onConfirm} className="w-full max-w-xs mx-auto bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg shadow-sm">Confirmar e Iniciar Geração</button>
    </div>
  </div>
);

export default App;