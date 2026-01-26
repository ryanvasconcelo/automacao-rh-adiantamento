// frontend/src/components/AdiantamentoDashboard.jsx
import React, { useState, useMemo } from 'react';
import { Search, ChevronLeft, CalendarClock, AlertTriangle, CheckCircle2, XCircle, FileText, ThumbsUp } from 'lucide-react';
import { PageTransition, Card, SmartButton, CustomSelect, MonthYearPicker, Badge, Button, Input, Toggle } from './ui/Shared';
import { StatCard } from './ui/StatCard';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const API_URL = 'http://localhost:8001';

const AdiantamentoDashboard = () => {
    const [view, setView] = useState('SELECTION');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [auditData, setAuditData] = useState([]);
    const [selectedCompanyCode, setSelectedCompanyCode] = useState(null);

    const [approvedCompanies, setApprovedCompanies] = useState(new Set());
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
                if (data.length === 0) setError("Nenhum dado encontrado.");
                else { setAuditData(data); setView('SUMMARY'); }
            } else { setError(data.detail || 'Erro na auditoria.'); }
        } catch (err) { setError('Falha de conexão.'); }
        finally { setLoading(false); }
    };

    const handleToggleApproval = (code) => {
        const newSet = new Set(approvedCompanies);
        if (newSet.has(code)) newSet.delete(code);
        else newSet.add(code);
        setApprovedCompanies(newSet);
    };

    const groupedSummary = useMemo(() => {
        if (!auditData.length) return {};
        return auditData.reduce((acc, row) => {
            const { empresaCode, empresaNome } = row;
            if (!acc[empresaCode]) {
                acc[empresaCode] = {
                    nome: empresaNome, code: empresaCode,
                    total: 0, pending: 0, warning: 0,
                    totalReal: 0, totalAudit: 0, totalDesc: 0,
                    isApproved: approvedCompanies.has(empresaCode)
                };
            }
            const c = acc[empresaCode];
            c.total++;
            c.totalReal += (row.ValorRealFortes || 0);
            c.totalAudit += (row.valorFinal || 0);
            c.totalDesc += (row.desconto || 0);

            if (!c.isApproved) {
                if (row.analise.includes('Divergência')) c.pending++;
                else if (row.analise.includes('Removido') || row.analise.includes('INCONSISTÊNCIA')) c.warning++;
            }
            return acc;
        }, {});
    }, [auditData, approvedCompanies]);

    const companies = Object.values(groupedSummary);
    const nonCompliant = companies.filter(c => (c.pending > 0 || c.warning > 0) && !c.isApproved);
    const compliant = companies.filter(c => (c.pending === 0 && c.warning === 0) || c.isApproved);

    const formatMoney = (val) => val?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const renderCompanyCard = (company) => (
        <Card
            key={company.code}
            className={`group cursor-pointer border-slate-200 transition-all hover:border-blue-400 hover:shadow-md ${company.isApproved ? 'bg-emerald-50/20' : ''}`}
            onClick={() => { setSelectedCompanyCode(company.code); setView('DETAIL'); }}
        >
            <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-slate-800 truncate pr-4 text-sm" title={company.nome}>{company.nome}</h3>
                {company.isApproved ? <Badge type="success">Aprovado Manual</Badge> :
                    company.pending > 0 ? <Badge type="error">{company.pending} Pend.</Badge> :
                        company.warning > 0 ? <Badge type="warning">{company.warning} Att.</Badge> :
                            <Badge type="success">100% OK</Badge>}
            </div>
            <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500 mb-3 bg-slate-50 p-2 rounded-lg">
                <div><p className="font-bold text-slate-700">{formatMoney(company.totalReal)}</p><span>Folha Real</span></div>
                <div className="text-right"><p className="font-bold text-purple-700">{formatMoney(company.totalAudit)}</p><span>Auditado</span></div>
            </div>
            <div className="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
                <div className={`h-full ${company.isApproved ? 'bg-emerald-500' : 'bg-blue-500'}`} style={{ width: company.isApproved ? '100%' : `${(company.total - company.pending - company.warning) / company.total * 100}%` }}></div>
            </div>
        </Card>
    );

    if (view === 'SELECTION') {
        return (
            <PageTransition className="max-w-2xl mx-auto mt-10">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-extrabold text-slate-900">Auditoria de Adiantamento</h2>
                    <p className="text-slate-500 mt-2">Processamento em lote de múltiplas empresas.</p>
                </div>
                <Card className="shadow-xl shadow-blue-900/5 border-blue-100 p-8">
                    <div className="space-y-8">
                        <CustomSelect label="Dia de Pagamento" value={selectedDay} onChange={setSelectedDay} options={[{ value: '15', label: 'Dia 15' }, { value: '20', label: 'Dia 20' }]} />
                        <MonthYearPicker month={selectedMonth} year={selectedYear} onMonthChange={setSelectedMonth} onYearChange={setSelectedYear} />
                        <SmartButton onClick={handleRunAudit} isLoading={loading} icon={CalendarClock}>Iniciar Auditoria</SmartButton>
                    </div>
                    {error && <div className="mt-6 p-4 bg-rose-50 text-rose-700 rounded-xl flex gap-2 border border-rose-100"><AlertTriangle size={20} />{error}</div>}
                </Card>
            </PageTransition>
        );
    }

    if (view === 'SUMMARY') {
        return (
            <PageTransition>
                <div className="flex justify-between items-center mb-8">
                    <Button variant="ghost" onClick={() => setView('SELECTION')} icon={ChevronLeft} className="-ml-2">Nova Seleção</Button>
                    <h2 className="text-2xl font-bold text-slate-900">Resumo Geral</h2>
                </div>
                <div className="space-y-8">
                    {nonCompliant.length > 0 && (
                        <div><h3 className="text-sm font-bold text-rose-600 uppercase tracking-wider mb-4 flex items-center gap-2"><XCircle size={16} /> Com Divergências ({nonCompliant.length})</h3><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{nonCompliant.map(renderCompanyCard)}</div></div>
                    )}
                    {compliant.length > 0 && (
                        <div><h3 className="text-sm font-bold text-emerald-600 uppercase tracking-wider mb-4 flex items-center gap-2"><CheckCircle2 size={16} /> Conformes ({compliant.length})</h3><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 opacity-80 hover:opacity-100 transition-opacity">{compliant.map(renderCompanyCard)}</div></div>
                    )}
                </div>
            </PageTransition>
        );
    }

    if (view === 'DETAIL') {
        const companyInfo = groupedSummary[selectedCompanyCode];
        const companyData = auditData.filter(r => r.empresaCode === selectedCompanyCode);
        return (
            <DetailView
                data={companyData}
                onBack={() => setView('SUMMARY')}
                name={companyInfo?.nome}
                month={selectedMonth}
                year={selectedYear}
                isApproved={companyInfo?.isApproved}
                onToggle={() => handleToggleApproval(selectedCompanyCode)}
            />
        );
    }
};

const DetailView = ({ data, onBack, name, month, year, isApproved, onToggle }) => {
    const [filter, setFilter] = useState('pending'); // Default: Pending
    const [search, setSearch] = useState('');

    const filtered = data.filter(row => {
        const matchSearch = row.nome.toLowerCase().includes(search.toLowerCase()) || row.matricula.includes(search);
        const isPending = row.analise.includes('Divergência');
        const isWarning = row.analise.includes('Removido') || row.analise.includes('INCONSISTÊNCIA');

        if (filter === 'pending') return matchSearch && isPending;
        if (filter === 'warning') return matchSearch && isWarning;
        if (filter === 'ok') return matchSearch && !isPending && !isWarning;
        return matchSearch;
    });

    const formatMoney = (val) => val?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    const metrics = useMemo(() => {
        const totalReal = data.reduce((s, r) => s + (r.ValorRealFortes || 0), 0);
        const totalAudit = data.reduce((s, r) => s + (r.valorFinal || 0), 0);
        const totalDesc = data.reduce((s, r) => s + (r.desconto || 0), 0);
        const pending = data.filter(r => r.analise.includes('Divergência')).length;
        const warning = data.filter(r => r.analise.includes('Removido') || r.analise.includes('INCONSISTÊNCIA')).length;
        return { totalReal, totalAudit, totalDesc, pending, warning, ok: data.length - pending - warning };
    }, [data]);

    const handleExport = () => {
        const doc = new jsPDF();
        doc.text(`Auditoria Adiantamento: ${name}`, 14, 15);
        doc.text(`Período: ${month}/${year}`, 14, 22);

        const rows = data.filter(r => r.analise.includes('Divergência') || r.analise.includes('INCONSISTÊNCIA') || r.analise.includes('Removido')).map(r => [
            r.matricula, r.nome, `R$ ${r.ValorRealFortes}`, `R$ ${r.valorFinal}`, r.analise
        ]);

        autoTable(doc, {
            head: [['Mat.', 'Nome', 'Real', 'Auditado', 'Análise']],
            body: rows,
            startY: 30
        });
        doc.save(`Adiantamento_${name}.pdf`);
    };

    return (
        <PageTransition className="space-y-6">
            <div className="flex items-end justify-between">
                <div>
                    <Button variant="ghost" onClick={onBack} icon={ChevronLeft} className="-ml-2 mb-1">Voltar</Button>
                    <div className="flex items-center gap-6">
                        <h2 className="text-2xl font-bold text-slate-900">{name}</h2>
                        <Toggle enabled={isApproved} onChange={onToggle} label={isApproved ? "Empresa Aprovada" : "Marcar como Conforme"} />
                    </div>
                </div>

                <div className="flex gap-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                        <input type="text" placeholder="Buscar funcionário..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-64" />
                    </div>
                    <Button variant="success" icon={FileText} onClick={handleExport}>Exportar Relatório</Button>
                </div>
            </div>

            {/* KPIs Financeiros */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-l-4 border-l-blue-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Total Folha (Real)</p>
                    <p className="text-2xl font-mono font-bold text-blue-600">{formatMoney(metrics.totalReal)}</p>
                </Card>
                <Card className="border-l-4 border-l-orange-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Total Consignado</p>
                    <p className="text-2xl font-mono font-bold text-orange-500">{formatMoney(metrics.totalDesc)}</p>
                </Card>
                <Card className="border-l-4 border-l-purple-500">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-1">Total Auditado</p>
                    <p className="text-2xl font-mono font-bold text-purple-600">{formatMoney(metrics.totalAudit)}</p>
                </Card>
            </div>

            {/* Filtros */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div onClick={() => setFilter('pending')} className={`cursor-pointer transition-all ${filter === 'pending' ? 'scale-105 ring-2 ring-rose-500' : 'opacity-70'}`}>
                    <StatCard title="Pendências (Divergência)" value={isApproved ? 0 : metrics.pending} icon={XCircle} color={isApproved ? "green" : "red"} subtext="Clique para filtrar" />
                </div>
                <div onClick={() => setFilter('warning')} className={`cursor-pointer transition-all ${filter === 'warning' ? 'scale-105 ring-2 ring-amber-500' : 'opacity-70'}`}>
                    <StatCard title="Atenção (Removidos)" value={metrics.warning} icon={AlertTriangle} color="blue" subtext="Verificar se correto" />
                </div>
                <div onClick={() => setFilter('all')} className={`cursor-pointer transition-all ${filter === 'all' ? 'scale-105 ring-2 ring-slate-400' : 'opacity-70'}`}>
                    <StatCard title="Total Analisado" value={data.length} icon={CheckCircle2} color="gray" subtext="Ver todos" />
                </div>
            </div>

            <Card noPadding>
                <div className="max-h-[600px] overflow-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 text-slate-500 font-bold uppercase text-xs sticky top-0 shadow-sm z-10">
                            <tr>
                                <th className="px-6 py-4">Matrícula</th>
                                <th className="px-6 py-4">Nome</th>
                                <th className="px-6 py-4 text-center">Status</th>
                                <th className="px-6 py-4 text-right text-slate-400">V. Cadastro</th>
                                <th className="px-6 py-4 text-right bg-blue-50/50 text-blue-700 border-l border-blue-100">V. Real</th>
                                <th className="px-6 py-4 text-right text-purple-700">V. Auditado</th>
                                <th className="px-6 py-4 w-1/3">Observações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filtered.map(row => {
                                const isPending = row.analise.includes('Divergência');
                                const isWarning = row.analise.includes('Removido') || row.analise.includes('INCONSISTÊNCIA');
                                return (
                                    <tr key={row.matricula} className={`hover:bg-slate-50 transition-colors ${isPending && !isApproved ? 'bg-rose-50/20' : isWarning && !isApproved ? 'bg-amber-50/20' : ''}`}>
                                        <td className="px-6 py-4 font-mono text-slate-500">{row.matricula}</td>
                                        <td className="px-6 py-4 font-medium text-slate-900">{row.nome}</td>
                                        <td className="px-6 py-4 text-center">
                                            {isPending && !isApproved ? <Badge type="error">Divergência</Badge> :
                                                isWarning && !isApproved ? <Badge type="warning">Atenção</Badge> :
                                                    <Badge type="success">OK</Badge>}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-400">{formatMoney(row.valorBruto)}</td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-blue-700 bg-blue-50/30 border-l border-blue-100">{formatMoney(row.ValorRealFortes)}</td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-purple-700">{formatMoney(row.valorFinal)}</td>
                                        <td className="px-6 py-4 text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{row.observacoes || row.analise}</td>
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