// frontend/src/components/AdiantamentoDashboard.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { ChevronLeft, ChevronsRight, FileDown, Loader, Search, CheckSquare, Square, XCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import logoProjecont from '../assets/logoProjecont.jpeg';

// CONFIGURAÇÃO DA API
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// --- Subcomponentes de UI ---
const LoadingScreen = ({ message }) => (
    <div className="flex flex-col items-center justify-center text-center p-8">
        <Loader className="w-12 h-12 text-blue-600 animate-spin mb-4" />
        <p className="text-lg font-semibold text-gray-700">{message}</p>
    </div>
);

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
            {onClose && (
                <button onClick={onClose} className={`ml-4 p-1 rounded-md ${bgColor} hover:bg-opacity-80 focus:outline-none focus:ring-2 focus:ring-offset-2 ${type === 'success' ? 'focus:ring-green-600' : 'focus:ring-red-600'}`}>
                    <XCircle className={`h-5 w-5 ${textColor}`} aria-hidden="true" />
                </button>
            )}
        </div>
    );
};

const SuccessAlert = ({ message, onClose }) => <Alert message={message} type="success" onClose={onClose} />;
const ErrorAlert = ({ message, onClose }) => <Alert message={message} type="error" onClose={onClose} />;

// --- Subcomponentes Funcionais ---

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

const SummaryView = ({ summaryData, onSelectCompany, onGenerateReports }) => (
    <div>
        <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
            <h2 className="text-3xl font-bold text-gray-900">Resumo da Auditoria</h2>
            <div className="flex items-center gap-4">
                <button onClick={onGenerateReports} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-6 rounded-lg shadow-sm">
                    Gerar Relatórios <ChevronsRight className="w-5 h-5" />
                </button>
            </div>
        </div>
        <div className="grid grid-cols-1 md:col-cols-2 lg:grid-cols-3 gap-6">
            {Object.values(summaryData).map(company => (
                <div key={company.code} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col">
                    <h3 className="font-bold text-lg text-gray-900 mb-4 truncate">{company.nome}</h3>
                    <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                        <p><strong>Total:</strong> {company.total}</p>
                        <p className={company.grave > 0 ? 'text-red-600' : 'text-gray-600'}><strong>Graves:</strong> {company.grave}</p>
                        <p className={company.divergencia > 0 ? 'text-amber-600' : 'text-gray-600'}><strong>Divergências:</strong> {company.divergencia}</p>
                        <p><strong>Removidos:</strong> {company.removido}</p>
                    </div>
                    <div className="flex gap-2 mt-auto">
                        <button onClick={() => onSelectCompany(company.code)} className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-2 px-4 rounded-lg text-xs">
                            Ver Detalhes
                        </button>
                    </div>
                </div>
            ))}
        </div>
    </div>
);

// --- COMPONENTE DETALHES (TABELA) ---
const DetailView = ({ companyData, companyName, empresaCodigo, onBack }) => {
    const [filterAnalise, setFilterAnalise] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedRows, setSelectedRows] = useState(new Set());

    useEffect(() => { setSelectedRows(new Set()); setFilterAnalise('all'); setSearchTerm(''); }, [companyData]);

    const formatCurrency = (value) => {
        const rounded = Math.round((value || 0) * 100) / 100;
        return rounded.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    // --- CÁLCULO DE TOTAIS COM A NOVA COLUNA ---
    const metrics = useMemo(() => {
        if (!companyData) return { totalFunc: 0, totalBruto: 0, totalReal: 0, totalFinal: 0, funcionariosElegiveis: 0, ok: 0, divergencia: 0, removidos: 0, grave: 0 };

        // valorBruto = Cadastro (Teórico) | ValorRealFortes = Folha (Eventos) | valorFinal = Auditado (Nosso)
        const totalBruto = Math.round(companyData.reduce((sum, row) => sum + (row.valorBruto || 0), 0) * 100) / 100;
        const totalReal = Math.round(companyData.reduce((sum, row) => sum + (row.ValorRealFortes || 0), 0) * 100) / 100;
        const totalFinal = Math.round(companyData.reduce((sum, row) => sum + (row.valorFinal || 0), 0) * 100) / 100;

        return {
            totalFunc: companyData.length,
            totalBruto,
            totalReal,
            totalFinal,
            funcionariosElegiveis: companyData.filter(row => row.status === 'Elegível' || row.analise.includes('OK')).length,
            ok: companyData.filter(row => row.analise.includes('OK')).length,
            divergencia: companyData.filter(row => row.analise.includes('Divergência')).length,
            removidos: companyData.filter(row => row.analise.includes('Removido')).length,
            grave: companyData.filter(row => row.analise.includes('INCONSISTÊNCIA') || row.analise.includes('Rescisão')).length,
        };
    }, [companyData]);

    const filteredData = useMemo(() => {
        return (companyData || []).filter(row => {
            const analiseLower = row.analise.toLowerCase();
            const matchesFilter = filterAnalise === 'all' ||
                (filterAnalise === 'ok' && analiseLower.includes('ok')) ||
                (filterAnalise === 'divergencia' && analiseLower.includes('divergência')) ||
                (filterAnalise === 'removido' && analiseLower.includes('removido')) ||
                (filterAnalise === 'grave' && (analiseLower.includes('inconsistência') || analiseLower.includes('rescisão')));
            const matchesSearch = !searchTerm || (row.nome && row.nome.toLowerCase().includes(searchTerm.toLowerCase())) || (row.matricula && row.matricula.includes(searchTerm));
            return matchesFilter && matchesSearch;
        });
    }, [companyData, filterAnalise, searchTerm]);

    const toggleRow = (matricula) => { const newSelected = new Set(selectedRows); if (newSelected.has(matricula)) newSelected.delete(matricula); else newSelected.add(matricula); setSelectedRows(newSelected); };
    const handleSelectAll = () => { if (selectedRows.size === filteredData.length) setSelectedRows(new Set()); else setSelectedRows(new Set(filteredData.map(row => row.matricula))); };

    const getRowColor = (analise) => {
        if (analise.includes('INCONSISTÊNCIA') || analise.includes('Rescisão')) return 'bg-red-50 hover:bg-red-100';
        if (analise.includes('Divergência')) return 'bg-amber-50 hover:bg-amber-100';
        if (analise.includes('Removido')) return 'bg-slate-50 hover:bg-slate-100';
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

            {/* CARDS DE TOTALIZADORES ATUALIZADOS */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <p className="text-xs text-gray-500 font-semibold uppercase mb-1">Total Cadastro (Teórico)</p>
                    <p className="text-2xl font-bold text-gray-400">{formatCurrency(metrics.totalBruto)}</p>
                </div>

                {/* NOVO CARD: VALOR REAL FOLHA */}
                <div className="bg-blue-50 rounded-xl shadow-sm border border-blue-200 p-5">
                    <p className="text-xs text-blue-600 font-semibold uppercase mb-1">Total Folha (Eventos)</p>
                    <p className="text-3xl font-bold text-blue-700">{formatCurrency(metrics.totalReal)}</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <p className="text-xs text-gray-500 font-semibold uppercase mb-1">Total Auditado (Regras)</p>
                    <p className="text-2xl font-bold text-purple-600">{formatCurrency(metrics.totalFinal)}</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <p className="text-xs text-gray-500 font-semibold uppercase mb-1">Elegíveis</p>
                    <p className="text-3xl font-bold text-green-600">{metrics.funcionariosElegiveis}</p>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {/* BARRA DE FILTROS */}
                <div className="p-6 border-b border-gray-200 flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex flex-wrap gap-2">
                        {filterButtons.map(btn => (
                            <button key={btn.key} onClick={() => setFilterAnalise(btn.key)} className={`px-3 py-1.5 text-sm font-semibold rounded-full transition-colors ${filterAnalise === btn.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
                                {btn.label} <span className={`ml-1 px-2 py-0.5 rounded-full text-xs bg-white/20`}>{btn.count}</span>
                            </button>
                        ))}
                    </div>
                    <div className="relative w-full md:w-auto"><Search className="absolute left-3 top-2.5 text-gray-400 w-4 h-4" /><input type="text" placeholder="Buscar funcionário..." className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} /></div>
                </div>

                {/* TABELA ATUALIZADA COM COLUNA EXTRA */}
                <div className="max-h-[600px] overflow-y-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 sticky top-0 z-10 text-xs text-gray-500 uppercase tracking-wider">
                            <tr>
                                <th className="px-6 py-3 w-12"><input type="checkbox" onChange={handleSelectAll} checked={filteredData.length > 0 && selectedRows.size === filteredData.length} /></th>
                                <th className="px-6 py-3 text-left">Matrícula</th>
                                <th className="px-6 py-3 text-left">Nome</th>
                                <th className="px-6 py-3 text-center">Análise</th>

                                {/* COLUNAS FINANCEIRAS */}
                                <th className="px-6 py-3 text-right text-gray-400">V. Cadastro</th>
                                <th className="px-6 py-3 text-right bg-blue-50 text-blue-700 font-bold border-l border-r border-blue-100">V. Folha (Real)</th>
                                <th className="px-6 py-3 text-right text-purple-700 font-bold">V. Auditado</th>

                                <th className="px-6 py-3 text-left">Observações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {filteredData.map((row) => (
                                <tr key={row.matricula} className={`${getRowColor(row.analise)} transition-colors`}>
                                    <td className="px-6 py-4"><input type="checkbox" checked={selectedRows.has(row.matricula)} onChange={() => toggleRow(row.matricula)} /></td>
                                    <td className="px-6 py-4 font-mono text-xs text-gray-500">{row.matricula}</td>
                                    <td className="px-6 py-4 font-medium text-gray-900">{row.nome}</td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={`px-2 py-1 rounded-full text-xs font-bold border ${row.analise.includes('OK') ? 'bg-green-100 text-green-700 border-green-200' : row.analise.includes('Divergência') ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-red-100 text-red-700 border-red-200'}`}>
                                            {row.analise.includes('OK') ? 'OK' : 'ATENÇÃO'}
                                        </span>
                                    </td>

                                    {/* VALORES */}
                                    <td className="px-6 py-4 text-right font-mono text-gray-400">{formatCurrency(row.valorBruto)}</td>

                                    {/* COLUNA NOVA DESTACADA */}
                                    <td className="px-6 py-4 text-right font-mono font-bold text-blue-700 bg-blue-50/50 border-l border-r border-blue-100">
                                        {formatCurrency(row.ValorRealFortes)}
                                    </td>

                                    <td className="px-6 py-4 text-right font-mono font-bold text-purple-700">{formatCurrency(row.valorFinal)}</td>

                                    <td className="px-6 py-4 text-xs text-gray-500 max-w-xs truncate" title={row.observacoes || row.analise}>
                                        {row.observacoes || row.analise}
                                    </td>
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
            <p className="text-gray-600 mb-6">Empresas selecionadas:</p>
            <ul className="text-left max-w-md mx-auto bg-gray-50 p-4 rounded-lg border mb-6 list-disc list-inside">{companies.map(c => <li key={c.code} className="font-semibold text-gray-800">{c.nome}</li>)}</ul>
            <button onClick={onConfirm} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg">Confirmar Geração</button>
        </div>
    </div>
);

// --- Componente Principal ---
const AdiantamentoDashboard = ({ onBackToMenu }) => {
    const [view, setView] = useState('SELECTION');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('');
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [auditData, setAuditData] = useState([]);

    const [selectedCompanyCode, setSelectedCompanyCode] = useState(null);
    const [selectedDay, setSelectedDay] = useState('15');
    const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

    useEffect(() => {
        let timer;
        if (successMessage) timer = setTimeout(() => setSuccessMessage(''), 5000);
        return () => { if (timer) clearTimeout(timer); };
    }, [successMessage]);

    const handleRunDayAudit = async () => {
        setIsLoading(true); setLoadingMessage('Auditando todas as empresas...'); setError(''); setSuccessMessage('');
        try {
            const response = await fetch(`${API_URL}/audit/adiantamento/day`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    day: parseInt(selectedDay),
                    month: parseInt(selectedMonth),
                    year: parseInt(selectedYear),
                }),
            });
            const data = await response.json();
            if (response.ok) {
                setAuditData(data);
                setView('SUMMARY');
            } else {
                setError(data.detail || 'Erro na API de auditoria.');
            }
        } catch (err) { setError('Falha na comunicação com a API (Porta 8001).'); }
        finally { setIsLoading(false); }
    };

    const handleGenerateReports = async () => {
        setIsLoading(true); setLoadingMessage('Gerando relatórios...'); setError(''); setSuccessMessage('');
        try {
            const response = await fetch(`${API_URL}/audit/adiantamento/reports/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    month: parseInt(selectedMonth), year: parseInt(selectedYear),
                    data: auditData.map(row => ({ matricula: row.matricula, nome: row.nome, empresaCodigo: row.empresaCodigo, empresaNome: row.empresaNome }))
                }),
            });
            const result = await response.json();
            if (response.ok && result.status === 'success') {
                setSuccessMessage(result.message || 'Relatórios gerados com sucesso!');
            } else { setError(result.detail || 'Falha ao gerar relatórios.'); }
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
            if (row.analise.includes('INCONSISTÊNCIA') || row.analise.includes('Rescisão')) acc[empresaCode].grave++;
            if (row.analise.includes('Corrigido')) acc[empresaCode].corrigido++;
            return acc;
        }, {});
    }, [auditData]);

    return (
        <div className="min-h-screen bg-gray-50 font-sans">
            <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                    <img src={logoProjecont} alt="Logo" className='w-8 h-8 rounded-md' />
                    <h1 className="text-xl font-semibold text-gray-900">Módulo Adiantamento</h1>
                </div>
                <button onClick={onBackToMenu} className="text-sm text-gray-500 hover:text-blue-600 font-medium">
                    Voltar ao Menu Principal
                </button>
            </div>

            <main className="max-w-7xl mx-auto px-6 py-2">
                {view !== 'SELECTION' && (<button onClick={() => setView('SELECTION')} className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800 mb-6"><ChevronLeft className="w-4 h-4" />Nova Seleção</button>)}
                {successMessage && <SuccessAlert message={successMessage} onClose={() => setSuccessMessage('')} />}
                {error && <ErrorAlert message={error} onClose={() => setError('')} />}
                {isLoading && <LoadingScreen message={loadingMessage} />}

                {!isLoading && !error && (
                    <>
                        {view === 'SELECTION' && (<SelectionView selectedDay={selectedDay} setSelectedDay={setSelectedDay} selectedMonth={selectedMonth} setSelectedMonth={setSelectedMonth} selectedYear={selectedYear} setSelectedYear={setSelectedYear} onAudit={handleRunDayAudit} />)}

                        {view === 'SUMMARY' && (
                            <SummaryView
                                summaryData={groupedSummaryData}
                                onSelectCompany={(code) => { setSelectedCompanyCode(code); setView('DETAIL'); }}
                                onGenerateReports={() => setView('GENERATION')}
                            />
                        )}

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

export default AdiantamentoDashboard;