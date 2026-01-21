// frontend/src/components/AdiantamentoDashboard.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { ChevronLeft, ChevronsRight, Search, FileDown, Play, Filter, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { PageTransition, Card, Button, Label, Select, Input, Badge } from './ui/Shared';
import { StatCard } from './ui/StatCard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const AdiantamentoDashboard = () => {
    const [view, setView] = useState('SELECTION');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [auditData, setAuditData] = useState([]);
    const [selectedCompanyCode, setSelectedCompanyCode] = useState(null);

    // Estados do Filtro
    const [selectedDay, setSelectedDay] = useState('15');
    const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

    const handleRunAudit = async () => {
        setLoading(true); setError('');
        try {
            const response = await fetch(`${API_URL}/audit/adiantamento/day`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ day: parseInt(selectedDay), month: parseInt(selectedMonth), year: parseInt(selectedYear) }),
            });
            const data = await response.json();
            if (response.ok) {
                setAuditData(data);
                setView('SUMMARY');
            } else {
                setError(data.detail || 'Erro na auditoria.');
            }
        } catch (err) { setError('Falha de conexão com o servidor.'); }
        finally { setLoading(false); }
    };

    const groupedSummary = useMemo(() => {
        if (!auditData.length) return {};
        return auditData.reduce((acc, row) => {
            const { empresaCode, empresaNome } = row;
            if (!acc[empresaCode]) acc[empresaCode] = { nome: empresaNome, code: empresaCode, total: 0, divergencias: 0, removidos: 0, graves: 0 };
            acc[empresaCode].total++;
            if (row.analise.includes('Divergência')) acc[empresaCode].divergencias++;
            if (row.analise.includes('Removido')) acc[empresaCode].removidos++;
            if (row.analise.includes('INCONSISTÊNCIA')) acc[empresaCode].graves++;
            return acc;
        }, {});
    }, [auditData]);

    // Views
    if (view === 'SELECTION') {
        return (
            <PageTransition className="max-w-2xl mx-auto mt-10">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-extrabold text-slate-900">Auditoria de Adiantamento</h2>
                    <p className="text-slate-500 mt-2">Selecione o período para processar o lote de empresas.</p>
                </div>

                <Card className="shadow-xl shadow-blue-900/5 border-blue-100">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <Label>Dia de Pagamento</Label>
                            <Select value={selectedDay} onChange={e => setSelectedDay(e.target.value)} options={[{ value: '15', label: 'Dia 15' }, { value: '20', label: 'Dia 20' }]} />
                        </div>
                        <div>
                            <Label>Mês de Referência</Label>
                            <Input type="number" value={selectedMonth} onChange={e => setSelectedMonth(e.target.value)} />
                        </div>
                        <div>
                            <Label>Ano</Label>
                            <Input type="number" value={selectedYear} onChange={e => setSelectedYear(e.target.value)} />
                        </div>
                    </div>

                    <div className="mt-8">
                        <Button onClick={handleRunAudit} isLoading={loading} className="w-full py-4 text-lg shadow-xl shadow-blue-500/20" icon={Play}>
                            {loading ? 'Processando Lote...' : 'Iniciar Auditoria'}
                        </Button>
                    </div>

                    {error && (
                        <div className="mt-6 p-4 bg-rose-50 text-rose-700 rounded-xl border border-rose-100 flex gap-3 items-center">
                            <AlertTriangle size={20} /> {error}
                        </div>
                    )}
                </Card>
            </PageTransition>
        );
    }

    if (view === 'SUMMARY') {
        return (
            <PageTransition>
                <div className="flex justify-between items-end mb-8">
                    <div>
                        <Button variant="ghost" onClick={() => setView('SELECTION')} icon={ChevronLeft} className="mb-2 -ml-2">Nova Seleção</Button>
                        <h2 className="text-3xl font-bold text-slate-900">Resumo da Execução</h2>
                    </div>
                    <Button variant="success" icon={FileDown}>Exportar Relatórios</Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Object.values(groupedSummary).map((company) => (
                        <Card key={company.code} className="hover:border-blue-300 group cursor-pointer" onClick={() => { setSelectedCompanyCode(company.code); setView('DETAIL'); }}>
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="font-bold text-slate-800 truncate pr-4" title={company.nome}>{company.nome}</h3>
                                <Badge type={company.divergencias > 0 ? "warning" : "success"}>
                                    {company.divergencias > 0 ? `${company.divergencias} Alertas` : "100% OK"}
                                </Badge>
                            </div>

                            <div className="grid grid-cols-3 gap-2 text-center py-4 bg-slate-50 rounded-xl mb-4">
                                <div><p className="text-xl font-bold text-slate-700">{company.total}</p><p className="text-[10px] uppercase font-bold text-slate-400">Total</p></div>
                                <div><p className="text-xl font-bold text-amber-600">{company.divergencias}</p><p className="text-[10px] uppercase font-bold text-amber-600/70">Div.</p></div>
                                <div><p className="text-xl font-bold text-slate-500">{company.removidos}</p><p className="text-[10px] uppercase font-bold text-slate-400">Rem.</p></div>
                            </div>

                            <Button variant="secondary" className="w-full text-xs" onClick={(e) => { e.stopPropagation(); setSelectedCompanyCode(company.code); setView('DETAIL'); }}>
                                Ver Detalhes
                            </Button>
                        </Card>
                    ))}
                </div>
            </PageTransition>
        );
    }

    if (view === 'DETAIL') {
        const companyData = auditData.filter(r => r.empresaCode === selectedCompanyCode);
        return <DetailView data={companyData} onBack={() => setView('SUMMARY')} name={groupedSummary[selectedCompanyCode]?.nome} />;
    }

    return null;
};

// --- COMPONENTE DE DETALHES (TABELA REFORMULADA) ---
const DetailView = ({ data, onBack, name }) => {
    const [filter, setFilter] = useState('all');
    const [search, setSearch] = useState('');

    const filtered = data.filter(row => {
        const matchSearch = row.nome.toLowerCase().includes(search.toLowerCase()) || row.matricula.includes(search);
        if (filter === 'all') return matchSearch;
        if (filter === 'error') return matchSearch && (row.analise.includes('Divergência') || row.analise.includes('INCONSISTÊNCIA'));
        if (filter === 'ok') return matchSearch && row.analise.includes('OK');
        return matchSearch;
    });

    const formatMoney = (val) => val?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    return (
        <PageTransition>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <Button variant="ghost" onClick={onBack} icon={ChevronLeft} className="mb-1 -ml-2">Voltar</Button>
                    <h2 className="text-2xl font-bold text-slate-900">{name}</h2>
                </div>
                <div className="flex gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Buscar..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none w-64"
                        />
                    </div>
                    <div className="flex bg-white rounded-xl border border-slate-200 p-1">
                        <button onClick={() => setFilter('all')} className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === 'all' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>Todos</button>
                        <button onClick={() => setFilter('error')} className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === 'error' ? 'bg-rose-50 text-rose-700' : 'text-slate-500 hover:text-slate-700'}`}>Divergências</button>
                    </div>
                </div>
            </div>

            <Card noPadding className="overflow-hidden">
                <div className="overflow-x-auto max-h-[700px]">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 text-slate-500 font-bold uppercase text-xs sticky top-0 shadow-sm z-10">
                            <tr>
                                <th className="px-6 py-4">Matrícula</th>
                                <th className="px-6 py-4">Nome</th>
                                <th className="px-6 py-4 text-center">Status</th>
                                <th className="px-6 py-4 text-right">V. Cadastro</th>
                                <th className="px-6 py-4 text-right bg-blue-50/50 text-blue-700 border-l border-blue-100">V. Folha (Real)</th>
                                <th className="px-6 py-4 text-right text-purple-700">V. Auditado</th>
                                <th className="px-6 py-4">Observações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filtered.map((row) => {
                                const isError = row.analise.includes('Divergência') || row.analise.includes('INCONSISTÊNCIA');
                                return (
                                    <tr key={row.matricula} className={`hover:bg-slate-50/80 transition-colors ${isError ? 'bg-rose-50/30' : ''}`}>
                                        <td className="px-6 py-4 font-mono text-slate-500">{row.matricula}</td>
                                        <td className="px-6 py-4 font-medium text-slate-900">{row.nome}</td>
                                        <td className="px-6 py-4 text-center">
                                            <Badge type={isError ? "error" : "success"}>
                                                {isError ? "Atenção" : "OK"}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-400">{formatMoney(row.valorBruto)}</td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-blue-700 bg-blue-50/30 border-l border-blue-100">
                                            {formatMoney(row.ValorRealFortes)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-purple-700">
                                            {formatMoney(row.valorFinal)}
                                        </td>
                                        <td className="px-6 py-4 text-xs text-slate-500 max-w-xs truncate" title={row.observacoes}>
                                            {row.observacoes || "-"}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </Card>
        </PageTransition>
    );
};

export default AdiantamentoDashboard;