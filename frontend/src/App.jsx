import React, { useState, useMemo, useEffect } from 'react';
import { Search, Download, CheckSquare, Square, AlertCircle, CheckCircle, TrendingDown, XCircle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const App = () => {
  // Estados para dados da API e controlo de UI
  const [groupedCompanies, setGroupedCompanies] = useState({ "15": [], "20": [] });
  const [auditData, setAuditData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Estados dos controlos
  const [selectedDay, setSelectedDay] = useState('20');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [filterAnalise, setFilterAnalise] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRows, setSelectedRows] = useState(new Set());

  // Busca a lista de empresas agrupadas da API na inicialização
  useEffect(() => {
    const fetchGroupedCompanies = async () => {
      try {
        const response = await fetch(`${API_URL}/companies/grouped`);
        if (!response.ok) throw new Error('A resposta da rede não foi OK');
        const data = await response.json();
        setGroupedCompanies(data);

        // Define uma empresa padrão (JR do dia 20, se existir)
        if (data['20'] && data['20'].length > 0) {
          const jrCompany = data['20'].find(c => c.code === 'JR');
          setSelectedCompany(jrCompany ? jrCompany.code : data['20'][0].code);
        }
      } catch (err) {
        setError('Falha ao carregar a lista de empresas. O back-end (API) está a correr?');
      }
    };
    fetchGroupedCompanies();
  }, []);

  // Atualiza a empresa selecionada quando o dia de pagamento muda
  useEffect(() => {
    const companiesForSelectedDay = groupedCompanies[selectedDay];
    if (companiesForSelectedDay && companiesForSelectedDay.length > 0) {
      // Para evitar uma seleção inválida, define a primeira empresa da nova lista como padrão
      if (!companiesForSelectedDay.some(c => c.code === selectedCompany)) {
        setSelectedCompany(companiesForSelectedDay[0].code);
      }
    } else {
      setSelectedCompany('');
    }
  }, [selectedDay, groupedCompanies]);

  // Função para carregar os dados da auditoria
  const handleLoadData = async () => {
    if (!selectedCompany) { setError('Por favor, selecione uma empresa.'); return; }
    setIsLoading(true);
    setError('');
    setAuditData([]);
    setSelectedRows(new Set());
    try {
      const response = await fetch(`${API_URL}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          catalog_code: selectedCompany,
          month: parseInt(selectedMonth),
          year: parseInt(selectedYear),
        }),
      });
      const data = await response.json();
      if (response.ok) {
        setAuditData(data);
        setFilterAnalise('all'); // Reseta o filtro ao carregar novos dados
      } else {
        setError(data.detail || 'Ocorreu um erro na API.');
      }
    } catch (err) {
      setError('Falha na comunicação com a API.');
    } finally {
      setIsLoading(false);
    }
  };

  // Cálculo das métricas com base nos dados da API
  const metrics = useMemo(() => {
    if (!auditData || auditData.length === 0) return { totalFunc: 0, totalBruto: 0, totalFinal: 0, totalDesconto: 0, ok: 0, divergencia: 0, removidos: 0, grave: 0 };
    const totalBruto = auditData.reduce((sum, row) => sum + (row.valorBruto || 0), 0);
    const totalFinal = auditData.reduce((sum, row) => sum + (row.valorFinal || 0), 0);
    const totalDesconto = auditData.reduce((sum, row) => sum + (row.desconto || 0), 0);
    const ok = auditData.filter(row => row.analise === 'OK').length;
    const divergencia = auditData.filter(row => row.analise.includes('Divergência de valor')).length;
    const removidos = auditData.filter(row => row.analise.includes('Removido pelas regras')).length;
    const grave = auditData.filter(row => row.analise.includes('INCONSISTÊNCIA GRAVE')).length;
    return { totalFunc: auditData.length, totalBruto, totalFinal, totalDesconto, ok, divergencia, removidos, grave };
  }, [auditData]);

  // Lógica de filtragem com base nos dados da API
  const filteredData = useMemo(() => {
    return (auditData || []).filter(row => {
      const matchesFilter = filterAnalise === 'all' ||
        (filterAnalise === 'ok' && row.analise === 'OK') ||
        (filterAnalise === 'divergencia' && row.analise.includes('Divergência de valor')) ||
        (filterAnalise === 'removido' && row.analise.includes('Removido pelas regras')) ||
        (filterAnalise === 'grave' && row.analise.includes('INCONSISTÊNCIA GRAVE'));
      const matchesSearch = !searchTerm ||
        (row.nome && row.nome.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (row.matricula && row.matricula.includes(searchTerm));
      return matchesFilter && matchesSearch;
    });
  }, [auditData, filterAnalise, searchTerm]);

  const toggleRow = (matricula) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(matricula)) newSelected.delete(matricula);
    else newSelected.add(matricula);
    setSelectedRows(newSelected);
  };

  const getRowColor = (analise) => {
    if (analise.includes('Inconsistência Grave')) return 'bg-red-50 hover:bg-red-100';
    if (analise.includes('Divergência de valor')) return 'bg-amber-50 hover:bg-amber-100';
    if (analise.includes('Removido pelas regras')) return 'bg-slate-50 hover:bg-slate-100';
    return 'bg-white hover:bg-gray-50';
  };

  const getCategoryIcon = (type) => {
    if (type === 'ok') return <CheckCircle className="w-5 h-5 text-emerald-600" />;
    if (type === 'divergencia') return <AlertCircle className="w-5 h-5 text-amber-600" />;
    if (type === 'removido') return <TrendingDown className="w-5 h-5 text-slate-600" />;
    if (type === 'grave') return <XCircle className="w-5 h-5 text-red-600" />;
    return null;
  };

  const formatCurrency = (value) => (value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  // Componente para o botão de aplicar correções, para evitar repetição
  const ActionButton = () => (
    <button disabled={selectedRows.size === 0} className={`px-6 py-2.5 rounded-lg font-semibold transition-colors ${selectedRows.size > 0 ? 'bg-green-600 hover:bg-green-700 text-white shadow-sm' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>
      Aplicar {selectedRows.size > 0 ? `(${selectedRows.size})` : ''} Correções
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4"><div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">RH</div><h1 className="text-xl font-semibold text-gray-900">Robo Auditor RH - Projecont</h1></div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8"><h2 className="text-3xl font-bold text-gray-900 mb-2">Auditor de Adiantamento Salarial</h2><p className="text-gray-600">Valide e corrija as folhas de adiantamento de forma eficiente.</p></div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-12 gap-4 items-end">
            <div className="col-span-12 md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">Dia Pag.</label><select className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" value={selectedDay} onChange={(e) => setSelectedDay(e.target.value)}><option value="15">Dia 15</option><option value="20">Dia 20</option></select></div>
            <div className="col-span-12 md:col-span-3"><label className="block text-sm font-medium text-gray-700 mb-2">Empresa Cliente</label><select className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" value={selectedCompany} onChange={(e) => setSelectedCompany(e.target.value)} disabled={!selectedDay}><option value="">Selecione uma Empresa</option>{(groupedCompanies[selectedDay] || []).map(comp => <option key={comp.code} value={comp.code}>{comp.name}</option>)}</select></div>
            <div className="col-span-6 md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">Mês</label><input type="number" min="1" max="12" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg" value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)} /></div>
            <div className="col-span-6 md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-2">Ano</label><input type="number" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg" value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)} /></div>
            <div className="col-span-12 md:col-span-3"><button onClick={handleLoadData} disabled={isLoading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-lg shadow-sm disabled:bg-gray-400">{isLoading ? 'A Carregar...' : 'Carregar Dados'}</button></div>
          </div>
          {error && <p className="text-red-600 mt-4">{error}</p>}
        </div>

        {(isLoading || auditData.length > 0) &&
          <div>
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumo da Auditoria</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Total Analisados</p><p className="text-3xl font-bold text-gray-900">{metrics.totalFunc}</p></div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Valor Bruto (Fortes)</p><p className="text-3xl font-bold text-gray-900">{formatCurrency(metrics.totalBruto)}</p></div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Valor Final (Regras)</p><p className="text-3xl font-bold text-blue-600">{formatCurrency(metrics.totalFinal)}</p></div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5"><p className="text-sm text-gray-600 font-medium mb-1">Total Descontos</p><p className="text-3xl font-bold text-red-600">{formatCurrency(metrics.totalDesconto)}</p></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <button onClick={() => setFilterAnalise('ok')} className={`text-left p-5 rounded-xl border-2 transition-all ${filterAnalise === 'ok' ? 'bg-emerald-100 border-emerald-500 shadow-md' : 'bg-white border-gray-200 hover:border-emerald-400'}`}><div className="flex items-center justify-between mb-2"><p className="text-sm font-medium text-emerald-900">OK</p>{getCategoryIcon('ok')}</div><p className="text-3xl font-bold text-emerald-700">{metrics.ok}</p></button>
                <button onClick={() => setFilterAnalise('divergencia')} className={`text-left p-5 rounded-xl border-2 transition-all ${filterAnalise === 'divergencia' ? 'bg-amber-100 border-amber-500 shadow-md' : 'bg-white border-gray-200 hover:border-amber-400'}`}><div className="flex items-center justify-between mb-2"><p className="text-sm font-medium text-amber-900">Divergência de Valor</p>{getCategoryIcon('divergencia')}</div><p className="text-3xl font-bold text-amber-700">{metrics.divergencia}</p></button>
                <button onClick={() => setFilterAnalise('removido')} className={`text-left p-5 rounded-xl border-2 transition-all ${filterAnalise === 'removido' ? 'bg-slate-100 border-slate-500 shadow-md' : 'bg-white border-gray-200 hover:border-slate-400'}`}><div className="flex items-center justify-between mb-2"><p className="text-sm font-medium text-slate-900">Removidos por Regras</p>{getCategoryIcon('removido')}</div><p className="text-3xl font-bold text-slate-700">{metrics.removidos}</p></button>
                <button onClick={() => setFilterAnalise('grave')} className={`text-left p-5 rounded-xl border-2 transition-all ${filterAnalise === 'grave' ? 'bg-red-100 border-red-500 shadow-md' : 'bg-white border-gray-200 hover:border-red-400'}`}><div className="flex items-center justify-between mb-2"><p className="text-sm font-medium text-red-900">Inconsistência Grave</p>{getCategoryIcon('grave')}</div><p className="text-3xl font-bold text-red-700">{metrics.grave}</p></button>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-6 border-b border-gray-200 flex flex-col md:flex-row items-center justify-between gap-4">
                <h3 className="text-lg font-semibold text-gray-900">Tabela de Auditoria ({filteredData.length} resultados)</h3>
                <div className="flex w-full md:w-auto items-center gap-4">
                  <div className="relative flex-1"><Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" /><input type="text" placeholder="Buscar..." className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div>
                  <ActionButton />
                </div>
              </div>

              <div className="max-h-[600px] overflow-y-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0"><tr><th className="px-6 py-3 w-12"></th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Matrícula</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Nome</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Análise</th><th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase">Valor Bruto</th><th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase">Valor do RH</th><th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Observações</th></tr></thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredData.map((row) => (
                      <tr key={row.matricula} className={`${getRowColor(row.analise)}`}>
                        <td className="px-6 py-4"><button onClick={() => toggleRow(row.matricula)}>{selectedRows.has(row.matricula) ? <CheckSquare className="w-5 h-5 text-blue-600" /> : <Square className="w-5 h-5 text-gray-400" />}</button></td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.matricula}</td>
                        <td className="px-6 py-4 text-sm text-gray-900 font-medium">{row.nome}</td>
                        <td className="px-6 py-4"><span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${row.analise === 'OK' ? 'bg-emerald-100 text-emerald-800' : row.analise.includes('Divergência') ? 'bg-amber-100 text-amber-800' : row.analise.includes('Removido') ? 'bg-slate-100 text-slate-800' : 'bg-red-100 text-red-800'}`}>{row.analise}</span></td>
                        <td className="px-6 py-4 text-sm text-right font-mono text-gray-900">{formatCurrency(row.valorBruto)}</td>
                        <td className="px-6 py-4 text-sm text-right font-mono font-semibold text-blue-600">{formatCurrency(row.valorFinal)}</td>
                        <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={row.observacoes}>{row.observacoes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
                <p className="text-sm text-gray-600"><span className="font-semibold text-gray-900">{selectedRows.size}</span> funcionário(s) selecionado(s)</p>
                <ActionButton />
              </div>
            </div>
          </div>
        }
      </main>
    </div>
  );
};

export default App;