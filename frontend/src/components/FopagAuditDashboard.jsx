// frontend/src/components/FopagAuditDashboard.jsx
import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, AlertTriangle, CheckCircle2, XCircle, FileText, Calculator, Hash, HelpCircle, ThumbsUp, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { PageTransition, Card, SmartButton, CustomSelect, MonthYearPicker, Badge, Button, SmartLoading, Toggle, Input, CalculationModal } from './ui/Shared';
import { StatCard } from './ui/StatCard';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const API_URL = 'http://localhost:8001';

export default function FopagAuditDashboard() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [view, setView] = useState('SELECTION');

    const [company, setCompany] = useState('');
    const [month, setMonth] = useState(new Date().getMonth() + 1);
    const [year, setYear] = useState(new Date().getFullYear());
    const [companiesList, setCompaniesList] = useState([]);

    const [filterMode, setFilterMode] = useState('pending');
    const [expandedRows, setExpandedRows] = useState({});
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedMemory, setSelectedMemory] = useState(null);
    const [isApproved, setIsApproved] = useState(false);

    useEffect(() => {
        axios.get(`${API_URL}/audit/fopag/companies`)
            .then(res => setCompaniesList(res.data))
            .catch(() => setCompaniesList([{ id: 'JR', name: 'JR (Fallback)' }]));
    }, []);

    const handleAudit = async () => {
        if (!company) return;
        setLoading(true); setError(null); setIsApproved(false);
        try {
            const res = await axios.post(`${API_URL}/audit/fopag/audit/database`, {
                empresa_id: company, month: parseInt(month), year: parseInt(year), pension_rule: '2'
            });
            if (res.data.divergencias.length === 0 && res.data.metadata.total_funcionarios === 0) {
                setError("Nenhum dado encontrado para o período.");
            } else {
                setData(res.data);
                setView('RESULTS');
                if (res.data.divergencias.some(d => d.tem_divergencia)) setFilterMode('pending');
            }
        } catch (err) {
            setError(err.response?.data?.detail || "Erro ao conectar com o servidor.");
        } finally { setLoading(false); }
    };

    const handleExportPDF = () => {
        const doc = new jsPDF();
        doc.text(`Auditoria FOPAG - ${month}/${year}`, 14, 15);
        const rows = [];
        data.divergencias.filter(d => d.tem_divergencia).forEach(d => {
            d.itens.filter(i => i.status === 'ERRO').forEach(item => {
                rows.push([d.matricula, d.nome, `${item.tipo_evento === 'D' ? '(-)' : '(+)'} ${item.evento}`, `Dif: R$ ${item.diferenca}`]);
            });
        });
        autoTable(doc, { head: [['Mat.', 'Nome', 'Evento', 'Diferença']], body: rows, startY: 25 });
        doc.save(`FOPAG_${company}.pdf`);
    };

    const toggleRow = (id) => setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
    const formatMoney = (val) => val?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const filteredList = data?.divergencias.filter(f => {
        const matchesSearch = f.nome.toLowerCase().includes(searchTerm.toLowerCase()) || f.matricula.includes(searchTerm);
        if (!matchesSearch) return false;
        if (filterMode === 'pending') return f.tem_divergencia;
        if (filterMode === 'ok') return !f.tem_divergencia;
        return true;
    });

    const financeMetrics = useMemo(() => {
        if (!data) return { proventos: 0, descontos: 0, fgts: 0, liquido: 0 };
        let proventos = 0, descontos = 0, fgts = 0;
        data.divergencias.forEach(func => {
            func.itens.forEach(item => {
                if (item.evento === 'FGTS') fgts += item.real;
                else if (item.tipo_evento === 'D') descontos += item.real;
                else if (item.tipo_evento === 'P') proventos += item.real;
            });
        });
        return { proventos, descontos, fgts, liquido: proventos - descontos };
    }, [data]);

    if (view === 'SELECTION') {
        return (
            <PageTransition className="max-w-2xl mx-auto mt-10">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-extrabold text-slate-900">Auditoria de Folha Mensal</h2>
                    <p className="text-slate-500 mt-2">Cálculo de impostos, benefícios e regras complexas.</p>
                </div>
                <Card className="shadow-xl shadow-purple-900/5 border-purple-100 p-8">
                    <div className="space-y-6">
                        <CustomSelect label="Empresa" value={company} onChange={setCompany} options={companiesList.map(c => ({ value: c.id, label: c.name }))} placeholder="Selecione a empresa..." searchable={true} />
                        <MonthYearPicker month={month} year={year} onMonthChange={setMonth} onYearChange={setYear} />
                        <SmartButton onClick={handleAudit} isLoading={loading} icon={Calculator} variant="green">Iniciar Auditoria Completa</SmartButton>
                    </div>
                    {loading && <div className="mt-6"><SmartLoading /></div>}
                    {error && <div className="mt-6 p-4 bg-rose-50 text-rose-700 rounded-xl border border-rose-100 flex gap-2"><AlertTriangle size={20} /> {error}</div>}
                </Card>
            </PageTransition>
        );
    }

    return (
        <PageTransition className="space-y-6">
            <div className="flex justify-between items-end">
                <div>
                    <Button variant="ghost" onClick={() => setView('SELECTION')} icon={AlertTriangle} className="mb-2 -ml-2 text-purple-600">Nova Seleção</Button>
                    <div className="flex items-center gap-6">
                        <h2 className="text-3xl font-bold text-slate-900">Resultado da Análise</h2>
                        <Toggle enabled={isApproved} onChange={setIsApproved} label={isApproved ? "Empresa Aprovada" : "Marcar como Conforme"} />
                    </div>
                </div>
                <div className="flex gap-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                        <input type="text" placeholder="Buscar funcionário..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none w-64" />
                    </div>
                    <Button variant="success" icon={FileText} onClick={handleExportPDF}>Exportar PDF</Button>
                </div>
            </div>

            {/* KPIs Financeiros */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="border-l-4 border-l-blue-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Proventos Totais</p>
                    <p className="text-xl font-mono font-bold text-blue-600">{formatMoney(financeMetrics.proventos)}</p>
                </Card>
                <Card className="border-l-4 border-l-orange-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Descontos Totais</p>
                    <p className="text-xl font-mono font-bold text-orange-500">{formatMoney(financeMetrics.descontos)}</p>
                </Card>
                <Card className="border-l-4 border-l-emerald-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Total FGTS</p>
                    <p className="text-xl font-mono font-bold text-emerald-600">{formatMoney(financeMetrics.fgts)}</p>
                </Card>
                <Card className="border-l-4 border-l-purple-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Líquido a Pagar</p>
                    <p className="text-2xl font-mono font-bold text-purple-600">{formatMoney(financeMetrics.liquido)}</p>
                </Card>
            </div>

            {/* Filtros */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div onClick={() => setFilterMode('pending')} className={`cursor-pointer transition-all ${filterMode === 'pending' ? 'scale-105 ring-2 ring-rose-500' : 'opacity-70'}`}>
                    <StatCard title="Pendências" value={isApproved ? 0 : data.metadata.total_divergencias} icon={XCircle} color={isApproved ? "green" : "red"} subtext="Clique para filtrar" />
                </div>
                <div onClick={() => setFilterMode('ok')} className={`cursor-pointer transition-all ${filterMode === 'ok' ? 'scale-105 ring-2 ring-emerald-500' : 'opacity-70'}`}>
                    <StatCard title="Conformes" value={isApproved ? data.metadata.total_funcionarios : data.metadata.total_funcionarios - data.metadata.total_divergencias} icon={CheckCircle2} color="green" />
                </div>
                <div onClick={() => setFilterMode('all')} className={`cursor-pointer transition-all ${filterMode === 'all' ? 'scale-105 ring-2 ring-slate-400' : 'opacity-70'}`}>
                    <StatCard title="Total Funcionários" value={data.metadata.total_funcionarios} icon={AlertTriangle} color="gray" />
                </div>
            </div>

            <CalculationModal isOpen={!!selectedMemory} onClose={() => setSelectedMemory(null)} data={selectedMemory} />

            <Card noPadding>
                <div className="max-h-[600px] overflow-auto">
                    {filteredList.map(func => (
                        <div key={func.matricula} className="border-b border-slate-100 last:border-0">
                            <div onClick={() => toggleRow(func.matricula)} className={`p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-all ${func.tem_divergencia && !isApproved ? 'bg-rose-50/10 border-l-4 border-l-rose-500' : 'border-l-4 border-l-transparent'}`}>
                                <div className="flex items-center gap-4">
                                    <div className={`p-2.5 rounded-xl ${func.tem_divergencia && !isApproved ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'}`}>
                                        {func.tem_divergencia && !isApproved ? <XCircle size={20} /> : <CheckCircle2 size={20} />}
                                    </div>
                                    <div><p className="font-bold text-slate-800">{func.nome}</p><p className="text-xs text-slate-400 font-mono mt-0.5">MAT: {func.matricula}</p></div>
                                </div>
                                <div className="flex items-center gap-4">
                                    {func.tem_divergencia && !isApproved && <span className="text-xs font-bold text-rose-600 bg-rose-50 px-3 py-1 rounded-full border border-rose-100">{func.itens.filter(i => i.status === 'ERRO').length} Erros</span>}
                                </div>
                            </div>
                            {expandedRows[func.matricula] && (
                                <div className="bg-slate-50/50 p-6 border-t border-slate-100 shadow-inner">
                                    <table className="w-full text-xs">
                                        <thead className="bg-slate-50 text-slate-500 uppercase font-bold">
                                            <tr>
                                                <th className="px-4 py-3 text-left">Evento</th>
                                                <th className="px-4 py-3 text-right">Base</th>
                                                <th className="px-4 py-3 text-right text-blue-600">Esperado</th>
                                                <th className="px-4 py-3 text-right text-slate-600">Real</th>
                                                <th className="px-4 py-3 text-right">Diferença</th>
                                                <th className="px-4 py-3 text-center">Memória</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {func.itens.map((item, idx) => (
                                                <tr key={idx} className={item.status === "ERRO" ? "bg-rose-50/50" : ""}>
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-2 font-medium text-slate-700">
                                                            {/* ÍCONE DE PROVENTO OU DESCONTO */}
                                                            {item.tipo_evento === 'D' ? <ArrowDownCircle size={14} className="text-rose-500" /> : <ArrowUpCircle size={14} className="text-emerald-500" />}
                                                            {/* NOME DO EVENTO CLICÁVEL SE TIVER MEMÓRIA */}
                                                            {item.memoria ? (
                                                                <button onClick={(e) => { e.stopPropagation(); setSelectedMemory(item.memoria); }} className="hover:text-blue-600 hover:underline flex items-center gap-1 transition-colors">
                                                                    {item.evento} <HelpCircle size={12} className="opacity-50" />
                                                                </button>
                                                            ) : item.evento}
                                                        </div>
                                                        <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5 ml-6"><Hash size={10} /> {item.codigo}</div>
                                                    </td>
                                                    <td className="px-4 py-3 text-right font-mono text-slate-400">{item.base > 0 ? formatMoney(item.base) : '-'}</td>
                                                    <td className="px-4 py-3 text-right font-mono font-bold text-blue-600">{formatMoney(item.esperado)}</td>
                                                    <td className="px-4 py-3 text-right font-mono text-slate-700">{formatMoney(item.real)}</td>
                                                    <td className={`px-4 py-3 text-right font-mono font-bold ${item.status === 'ERRO' ? 'text-rose-600' : 'text-slate-300'}`}>{item.diferenca !== 0 ? formatMoney(item.diferenca) : '-'}</td>
                                                    <td className="px-4 py-3 text-center"><span className="text-[10px] text-slate-400">{item.formula || '-'}</span></td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </Card>
        </PageTransition>
    );
}

// Icones locais para garantir renderização
const UsersIcon = (props) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
const CheckIcon = (props) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>