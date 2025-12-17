import React, { useState } from 'react';
import axios from 'axios';
import { Search, AlertTriangle, Users, FileWarning, CheckCircle, XCircle, ChevronDown, ChevronUp, Info, Calculator } from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000';

export default function FopagAuditDashboard() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    // Filtros
    const [company, setCompany] = useState('JR');
    const [month, setMonth] = useState(10);
    const [year, setYear] = useState(2025);
    const [casoPensao, setCasoPensao] = useState(2); // Novo: Caso de Pensão

    const [expandedRows, setExpandedRows] = useState({});
    const [showPensaoInfo, setShowPensaoInfo] = useState(false);

    const handleAudit = async () => {
        setLoading(true);
        setError(null);
        setData(null);
        try {
            const response = await axios.post(`${API_URL}/api/v1/fopag/audit/database`, {
                company_code: company,
                month: parseInt(month),
                year: parseInt(year),
                caso_pensao: parseInt(casoPensao) // Envia o caso selecionado
            });
            setData(response.data);
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || "Erro ao conectar com o servidor.");
        } finally {
            setLoading(false);
        }
    };

    const toggleRow = (matricula) => {
        setExpandedRows(prev => ({ ...prev, [matricula]: !prev[matricula] }));
    };

    const formatMoney = (val) => {
        return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    };

    // Filtra apenas quem tem erro
    const funcionariosComErro = data?.divergencias.filter(f => f.tem_divergencia).length || 0;
    const funcionariosOK = data?.divergencias.filter(f => !f.tem_divergencia).length || 0;

    // Estatísticas extras
    const totalEventosAuditados = data?.divergencias.reduce((acc, f) => acc + f.itens.length, 0) || 0;
    const totalErros = data?.divergencias.reduce((acc, f) => acc + f.itens.filter(i => i.status === "ERRO").length, 0) || 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen font-sans">
            {/* Header */}
            <div className="bg-white p-6 rounded-xl shadow-sm mb-8">
                <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <Calculator className="text-blue-600" />
                    Auditoria FOPAG - Relatório Completo
                </h1>

                {/* Filtros */}
                <div className="flex flex-wrap gap-4 items-end">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
                        <select
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            className="p-2 border rounded-lg w-48 bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="JR">JR (9098)</option>
                            <option value="CMD">CMD (Exemplo)</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
                        <input
                            type="number"
                            value={month}
                            onChange={e => setMonth(e.target.value)}
                            min="1"
                            max="12"
                            className="p-2 border rounded-lg w-20 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
                        <input
                            type="number"
                            value={year}
                            onChange={e => setYear(e.target.value)}
                            className="p-2 border rounded-lg w-24 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>

                    {/* Novo: Seletor de Caso de Pensão */}
                    <div className="relative">
                        <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                            Regra de Pensão
                            <button
                                onClick={() => setShowPensaoInfo(!showPensaoInfo)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <Info size={14} />
                            </button>
                        </label>
                        <select
                            value={casoPensao}
                            onChange={e => setCasoPensao(e.target.value)}
                            className="p-2 border rounded-lg w-48 bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="1">Caso 1 - Proventos Brutos</option>
                            <option value="2">Caso 2 - Líquido (Padrão)</option>
                            <option value="3">Caso 3 - Salário Base</option>
                        </select>

                        {/* Tooltip de Informação */}
                        {showPensaoInfo && (
                            <div className="absolute z-10 mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-lg w-80 text-sm">
                                <p className="font-bold text-gray-800 mb-2">Regras de Cálculo:</p>
                                <ul className="space-y-2 text-gray-600">
                                    <li><span className="font-semibold">Caso 1:</span> Proventos Brutos × %</li>
                                    <li><span className="font-semibold">Caso 2:</span> (Proventos - INSS - IRRF) × %</li>
                                    <li><span className="font-semibold">Caso 3:</span> Salário Base × %</li>
                                </ul>
                                <p className="text-xs text-gray-500 mt-2">
                                    O percentual vem do banco de dados do Fortes.
                                </p>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleAudit}
                        disabled={loading}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
                    >
                        {loading ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                                Auditando...
                            </>
                        ) : (
                            <>
                                <Search size={18} />
                                Executar Auditoria
                            </>
                        )}
                    </button>
                </div>

                {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-start gap-2">
                        <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
                        <span>{error}</span>
                    </div>
                )}
            </div>

            {/* Resultados */}
            {data && (
                <div className="animate-fade-in space-y-6">
                    {/* KPIs Principais */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <CardKPI
                            title="Total Funcionários"
                            value={data.metadata.total_funcionarios}
                            icon={<Users className="text-blue-500" />}
                        />
                        <CardKPI
                            title="Com Divergência"
                            value={funcionariosComErro}
                            icon={<XCircle className="text-red-500" />}
                            color="text-red-600"
                        />
                        <CardKPI
                            title="100% Validados"
                            value={funcionariosOK}
                            icon={<CheckCircle className="text-green-500" />}
                            color="text-green-600"
                        />
                        <CardKPI
                            title="Eventos Auditados"
                            value={totalEventosAuditados}
                            icon={<FileWarning className="text-purple-500" />}
                            color="text-purple-600"
                        />
                    </div>

                    {/* Badge de Regra Aplicada */}
                    <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg flex items-center gap-3">
                        <Info className="text-blue-600" size={20} />
                        <div>
                            <p className="text-sm font-semibold text-blue-900">
                                Regra de Pensão Aplicada: Caso {casoPensao}
                            </p>
                            <p className="text-xs text-blue-700">
                                {casoPensao === "1" && "Cálculo: Proventos Brutos × %"}
                                {casoPensao === "2" && "Cálculo: (Proventos - INSS - IRRF) × %"}
                                {casoPensao === "3" && "Cálculo: Salário Base × %"}
                            </p>
                        </div>
                    </div>

                    {/* Resumo de Erros */}
                    {totalErros > 0 && (
                        <div className="bg-red-50 border border-red-200 p-4 rounded-lg flex items-center gap-3">
                            <AlertTriangle className="text-red-600" size={20} />
                            <div>
                                <p className="text-sm font-semibold text-red-900">
                                    {totalErros} evento(s) com divergência encontrado(s)
                                </p>
                                <p className="text-xs text-red-700">
                                    Revise os eventos marcados em vermelho abaixo.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Lista Detalhada de Funcionários */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                        <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                            <h3 className="font-bold text-gray-800">Detalhamento por Funcionário</h3>
                            <p className="text-xs text-gray-500 mt-1">
                                Clique em um funcionário para ver os eventos auditados
                            </p>
                        </div>

                        <div className="divide-y divide-gray-100">
                            {data.divergencias.map((func) => {
                                const errosCount = func.itens.filter(i => i.status === "ERRO").length;
                                const okCount = func.itens.filter(i => i.status === "OK").length;

                                return (
                                    <div key={func.matricula} className="group">
                                        <div
                                            onClick={() => toggleRow(func.matricula)}
                                            className={`p-4 flex items-center justify-between cursor-pointer hover:bg-blue-50 transition-all ${func.tem_divergencia ? 'bg-red-50/30' : 'hover:bg-green-50/30'
                                                }`}
                                        >
                                            <div className="flex items-center gap-4">
                                                {func.tem_divergencia ? (
                                                    <div className="relative">
                                                        <XCircle className="text-red-500" size={24} />
                                                        <span className="absolute -top-1 -right-1 bg-red-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-bold">
                                                            {errosCount}
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <CheckCircle className="text-green-500" size={24} />
                                                )}
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <p className="font-bold text-gray-800">{func.nome}</p>
                                                        {func.is_aprendiz && (
                                                            <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full font-semibold">
                                                                Aprendiz
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-gray-500">
                                                        Matrícula: {func.matricula} • {func.itens.length} evento(s) auditado(s)
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                {func.tem_divergencia && (
                                                    <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-semibold">
                                                        {errosCount} erro(s)
                                                    </span>
                                                )}
                                                <div className="text-gray-400">
                                                    {expandedRows[func.matricula] ? <ChevronUp /> : <ChevronDown />}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Detalhes dos Eventos */}
                                        {expandedRows[func.matricula] && (
                                            <div className="bg-gray-50 p-6 border-t border-gray-200">
                                                <div className="overflow-x-auto">
                                                    <table className="w-full text-sm">
                                                        <thead className="text-xs text-gray-500 uppercase bg-gray-100">
                                                            <tr>
                                                                <th className="px-4 py-3 text-left">Evento</th>
                                                                <th className="px-4 py-3 text-right">Base</th>
                                                                <th className="px-4 py-3 text-right">Esperado</th>
                                                                <th className="px-4 py-3 text-right">Real (Fortes)</th>
                                                                <th className="px-4 py-3 text-center">Status</th>
                                                                <th className="px-4 py-3 text-right">Diferença</th>
                                                                <th className="px-4 py-3 text-left">Observação</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {func.itens.map((item, idx) => (
                                                                <tr
                                                                    key={idx}
                                                                    className={`border-b transition-colors ${item.status === "ERRO"
                                                                        ? 'bg-red-50 hover:bg-red-100'
                                                                        : 'bg-white hover:bg-gray-50'
                                                                        }`}
                                                                >
                                                                    <td className="px-4 py-3 font-medium text-gray-800">
                                                                        {item.evento}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right text-gray-500 font-mono text-xs">
                                                                        {item.base > 0 ? formatMoney(item.base) : '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right text-blue-600 font-mono font-semibold">
                                                                        {formatMoney(item.esperado)}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right text-gray-700 font-mono font-semibold">
                                                                        {formatMoney(item.real)}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-center">
                                                                        {item.status === "OK" ? (
                                                                            <span className="bg-green-100 text-green-800 text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1">
                                                                                <CheckCircle size={12} /> OK
                                                                            </span>
                                                                        ) : (
                                                                            <span className="bg-red-100 text-red-800 text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1">
                                                                                <XCircle size={12} /> ERRO
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className={`px-4 py-3 text-right font-mono font-bold ${item.status === "ERRO" ? 'text-red-600' : 'text-gray-400'
                                                                        }`}>
                                                                        {item.diferenca !== 0 && (
                                                                            <span>
                                                                                {item.diferenca > 0 ? '+' : ''}
                                                                                {formatMoney(item.diferenca)}
                                                                            </span>
                                                                        )}
                                                                        {item.diferenca === 0 && '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-xs text-gray-600">
                                                                        {item.msg}
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>

                                                {/* Resumo do Funcionário */}
                                                <div className="mt-4 flex items-center gap-4 text-xs text-gray-600 bg-white p-3 rounded-lg border border-gray-200">
                                                    <span className="flex items-center gap-1">
                                                        <CheckCircle size={14} className="text-green-500" />
                                                        <strong>{okCount}</strong> validado(s)
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <XCircle size={14} className="text-red-500" />
                                                        <strong>{errosCount}</strong> divergência(s)
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Rodapé com Informações */}
                    <div className="bg-gray-100 p-4 rounded-lg text-xs text-gray-600">
                        <p className="font-semibold mb-2">Eventos Confiáveis (via Conecta):</p>
                        <p>
                            956 (Reembolso Salarial), 934 (Convênio Compras), 30 (Comissão), 938 (Falta em Caixa), 955 (Reembolso VT)
                        </p>
                        <p className="mt-2">
                            <strong>DSR (49):</strong> Incide sobre variáveis (HE + Adicionais) •
                            <strong> Adic. Noturno 012:</strong> Sobre salário contratual •
                            <strong> Adic. Noturno 050:</strong> Sobre horas trabalhadas
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

function CardKPI({ title, value, icon, color = "text-gray-800" }) {
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4 hover:shadow-md transition-shadow">
            <div className="p-3 bg-gray-50 rounded-full">{icon}</div>
            <div>
                <p className="text-sm text-gray-500 font-medium">{title}</p>
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
            </div>
        </div>
    );
}