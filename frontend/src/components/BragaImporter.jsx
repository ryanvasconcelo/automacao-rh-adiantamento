import React, { useState } from 'react';
import { UploadCloud, FileSpreadsheet, AlertCircle, CheckCircle2, Download, Play } from 'lucide-react';
import { PageTransition, Card, Button, SmartButton } from './ui/Shared';

const COMPANY_NAMES = {
    "9274": "Braga Veículos",
    "9275": "Rey Moto"
};

const BragaImporter = () => {
    const [file, setFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [result, setResult] = useState(null);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
            setResult(null);
        }
    };

    const handleProcess = async () => {
        if (!file) return;
        setIsUploading(true);
        setResult(null);

        const formData = new FormData();
        formData.append("file", file);
        formData.append("evento_padrao", "030");

        try {
            const response = await fetch("http://localhost:8001/braga-comissoes/processar", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                // Captura erros padrão do FastAPI (HTTPExceptions)
                setResult({
                    status: 'error',
                    title: 'Erro no Servidor',
                    message: data.detail || 'Falha na requisição ao servidor.'
                });
                return;
            }

            setResult({ ...data, title: 'Erro de Validação (Apelidos Vazio)' });
        } catch (error) {
            setResult({ status: 'error', title: 'Erro de Conexão', message: 'Servidor offline ou fora do ar.' });
        } finally {
            setIsUploading(false);
        }
    };

    const downloadCSV = (empId, content) => {
        const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `importacao_fortes_${empId}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <PageTransition>
            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-slate-800">Importador de Eventos</h2>
                    <p className="text-slate-500 mt-1">Gere arquivos de importação para o Fortes a partir de planilhas Excel.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Panel 1: Upload */}
                    <Card>
                        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                            <UploadCloud className="text-blue-500" /> Upload de Planilha
                        </h3>

                        <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center bg-slate-50 hover:bg-slate-100 transition-colors">
                            <input
                                type="file"
                                id="file-upload"
                                className="hidden"
                                accept=".xlsx"
                                onChange={handleFileChange}
                            />
                            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                                <FileSpreadsheet size={48} className={file ? "text-blue-600 mb-4" : "text-slate-400 mb-4"} />
                                <span className="font-semibold text-slate-700">
                                    {file ? file.name : "Clique para selecionar ou arraste o arquivo"}
                                </span>
                                <span className="text-sm text-slate-500 mt-2">Apenas arquivos .xlsx</span>
                            </label>
                        </div>

                        <div className="mt-6">
                            <SmartButton
                                onClick={handleProcess}
                                isLoading={isUploading}
                                icon={Play}
                                disabled={!file}
                                className={!file ? 'opacity-50 cursor-not-allowed' : ''}
                            >
                                Processar e Validar
                            </SmartButton>
                        </div>
                    </Card>

                    {/* Panel 2: Results */}
                    <Card>
                        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                            <CheckCircle2 className="text-emerald-500" /> Resultados da Conversão
                        </h3>

                        {!result && (
                            <div className="flex flex-col items-center justify-center h-48 text-slate-400">
                                <p>Faça o upload da planilha para ver os resultados.</p>
                            </div>
                        )}

                        {(result && (result.status === 'success' || result.status === 'warning')) && (
                            <div className="space-y-4">
                                {result.status === 'success' ? (
                                    <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl flex items-start gap-3">
                                        <CheckCircle2 className="text-emerald-500 mt-0.5" />
                                        <div>
                                            <p className="font-bold">Conversão concluída!</p>
                                            <p className="text-sm">Todos os vendedores foram identificados com sucesso.</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-xl flex items-start gap-3">
                                        <AlertCircle className="text-amber-500 mt-0.5" />
                                        <div>
                                            <p className="font-bold">Processado com Avisos</p>
                                            <p className="text-sm">{result.message}</p>
                                        </div>
                                    </div>
                                )}

                                <div className="mt-4 space-y-2">
                                    {Object.entries(result.arquivos || {}).map(([empId, content]) => {
                                        const registros = result.arquivos_detalhes?.[empId] || [];

                                        return (
                                            <div key={empId} className="flex items-center justify-between p-3 border border-slate-200 rounded-lg bg-white">
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-slate-800">{COMPANY_NAMES[empId] || 'Empresa Desconhecida'}</span>
                                                    <span className="text-xs text-slate-500">Cód Fortes: {empId} | {registros.length} registros</span>
                                                </div>
                                                <Button variant="secondary" onClick={() => downloadCSV(empId, content)}>
                                                    <Download size={16} className="mr-2" /> Baixar CSV
                                                </Button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {result && result.status === 'error' && (
                            <div className="space-y-4">
                                <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl flex items-start gap-3 flex-shrink-0">
                                    <AlertCircle className="text-rose-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <p className="font-bold">{result.title || "Erro no Processamento"}</p>
                                        <p className="text-sm">{result.message}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </Card>
                </div>

                {/* Full Width De-Para Table */}
                {(result && result.status !== 'error') && (
                    <Card className="mt-6">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                <FileSpreadsheet className="text-blue-500" /> Conferência de associação de apelidos
                            </h3>
                            <div className="flex gap-4 text-xs">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full"></div>
                                    <span className="text-slate-500 font-medium">Matches: {Object.values(result.arquivos_detalhes || {}).flat().length}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2.5 h-2.5 bg-rose-500 rounded-full"></div>
                                    <span className="text-slate-500 font-medium">Falhas: {result.apelidos_nao_encontrados?.length || 0}</span>
                                </div>
                            </div>
                        </div>

                        <div className="overflow-x-auto max-h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200">
                            <table className="w-full text-left text-sm border-collapse">
                                <thead className="sticky top-0 z-10 bg-white">
                                    <tr className="bg-slate-50 text-slate-500 uppercase text-[10px] tracking-widest font-bold border-b border-slate-200">
                                        <th className="px-4 py-3">Apelido (Planilha)</th>
                                        <th className="px-4 py-3">Nome Identificado (Fortes)</th>
                                        <th className="px-4 py-3">Empresa</th>
                                        <th className="px-4 py-3">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {/* Primeiro as Falhas */}
                                    {result.apelidos_nao_encontrados?.map(apelido => (
                                        <tr key={apelido} className="border-b border-slate-100 bg-rose-50/20 hover:bg-rose-50/40 transition-colors">
                                            <td className="px-4 py-3 font-mono text-rose-700 font-bold">{apelido}</td>
                                            <td className="px-4 py-3 text-slate-400 italic">Não localizado no banco de ativos</td>
                                            <td className="px-4 py-3 text-slate-400">-</td>
                                            <td className="px-4 py-3">
                                                <span className="px-2.5 py-1 bg-rose-100 text-rose-700 rounded-lg text-[10px] font-bold">FALHA</span>
                                            </td>
                                        </tr>
                                    ))}
                                    {/* Sucessos */}
                                    {Object.entries(result.arquivos_detalhes || {}).flatMap(([empId, regs]) =>
                                        regs.map((reg, idx) => (
                                            <tr key={`${empId}-${idx}`} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                                                <td className="px-4 py-3 font-mono text-slate-600">{reg.apelido_original}</td>
                                                <td className="px-4 py-3 font-medium text-slate-800">{reg.nome_match}</td>
                                                <td className="px-4 py-3 text-slate-500 font-medium">
                                                    {COMPANY_NAMES[empId]}
                                                    <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-slate-100 rounded text-slate-400">{empId}</span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-[10px] font-bold">MATCH</span>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                )}
            </div>
        </PageTransition>
    );
};

export default BragaImporter;
