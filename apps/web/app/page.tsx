"use client";

import { useEffect, useRef, useState } from "react";
import {
 Activity, ArrowRight, ArrowUpRight, BarChart3, BookOpen, Check, CheckCircle2,
 ChevronLeft, ChevronRight, CircleHelp, Clock3, CloudUpload, Database,
 FlaskConical, FolderOpen, GitBranch, LayoutDashboard, Layers3, Menu,
 Microscope, Play, Plus, SearchCheck, Settings2, Shield, ShieldCheck, Info,
 SlidersHorizontal, Sparkles, Target, TerminalSquare, TrendingUp, UploadCloud,
 WandSparkles, X, Zap, AlertTriangle, LoaderCircle, ExternalLink, FileSpreadsheet
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SessionOverview, type AlgoSession } from "./session-overview";
import { StrategyConfigurator, DEFAULT_INDICATOR_RANGES, type AlgoConfig } from "./strategy-configurator";
import {DEFAULT_CAPITAL} from "./capital-management";
import {DEFAULT_SCHEDULE} from "./schedule-config";
import {DEFAULT_FUNDING} from "./funding-config";
import {DEFAULT_ADVANCED} from "./advanced-config";
import {DEFAULT_QUALITY} from "./quality-filters";
import {DEFAULT_WALK_FORWARD} from "./walk-forward-config";
import {DEFAULT_MULTIVERSE} from "./multiverse-config";
import {DEFAULT_COSTS} from "./costs-config";
import {ResearchResults,StrategyDetail} from "./research-results";
import type {AssetDiagnostics} from "./dataset-diagnostics";
import {readExperiments,writeExperiments} from "./browser-store";

type View = "home" | "sessions" | "builder" | "datasets" | "results" | "validation" | "running" | "detail";
type Dataset = { id:string; filename:string; rows:number; start:string; end:string; timeframe:string; uploaded_at:string };
type FundingAnalysis={
 pass_rate_pct:number;p20_days:number|null;p50_days:number|null;p80_days:number|null;
 selected_percentile_days:number|null;pass_within_day_cap_pct:number;
 phase_pass_rate_pct:number[];eligible:boolean;successful_paths:number;simulations:number;
 fail_reasons:Record<string,number>;
};
type Candidate = {
 quality_is?:{sharpe:number;dsr:number;trades_per_day:number;dsr_trials:number};
 quality_oos?:{sharpe:number;dsr:number;trades_per_day:number};
 walk_forward?:{pass_rate_pct?:number;median_wfe?:number;tested_windows?:number;mode?:string;eligible?:boolean;error?:string}|null;
 multiverse?:{score?:number;survival_pct?:number;p95_drawdown_pct?:number;universes?:number;eligible?:boolean;error?:string}|null;
 estimated_cost_bps?:number;
 entry_mode?:"market"|"stop"|"limit";advanced_modifiers?:Record<string,unknown>;
 funding_evaluation_is?:FundingAnalysis|null;funding_evaluation_oos?:FundingAnalysis|null;
 id:string; family:string; params:Record<string,number>; in_sample:Metrics; out_of_sample:Metrics;
 monte_carlo:{p95_drawdown_pct:number|null; probability_10pct_drawdown:number|null; iterations:number; trade_count:number};
 accepted:boolean; reasons:string[];
};
type Metrics = { trades:number; win_rate:number; profit_factor:number|null; expectancy_r:number; max_drawdown_pct:number; net_return_pct:number; daily_breached:boolean; total_breached:boolean };
type RunResult = { id:string; created_at:string; dataset_id:string; tested:number; accepted:number; candidates:Candidate[]; warnings:string[]; config:Config };
type Config = AlgoConfig;
const DEFAULT_API="http://127.0.0.1:8000"; // Only local scientific engine
const DEFAULT:Config={ name:"Nueva exploración cuantitativa",dataset_id:"",symbol:"XAUUSD",timeframe:"5m",timeframes:["5m"],start_date:"",end_date:"",initial_deposit:5000,mode:"random",optimization_objective:"balanced",modeling:"ohlc",sizing:"compound",multi_tf:"individual",generations:8,candidates:100,families:["ema_cross","rsi_reversion","breakout"],indicator_ranges:DEFAULT_INDICATOR_RANGES,source_timezone:"UTC",macro_indicators:[],macro_rules:{},capital:DEFAULT_CAPITAL,schedule:DEFAULT_SCHEDULE,funding:DEFAULT_FUNDING,advanced_modifiers:DEFAULT_ADVANCED,quality:DEFAULT_QUALITY,walk_forward:DEFAULT_WALK_FORWARD,multiverse:DEFAULT_MULTIVERSE,costs:DEFAULT_COSTS,direction:"both",risk_pct:0.5,rr:1.0,atr_multiplier:1.5,cost_bps:2,is_ratio:70,min_trades:12,mc_iterations:500,prop_daily_pct:3,prop_max_pct:10 };
const STEPS=[{title:"Mercado y datos",sub:"Fuente y búsqueda"},{title:"Señales",sub:"Hipótesis y reglas"},{title:"Ejecución",sub:"Riesgo y costes"},{title:"Validación",sub:"Pruebas y filtros"}];
const formatDate=(value:string)=>{const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleDateString("es-DO",{day:"2-digit",month:"short",year:"numeric"})};
const n2=(x:number|null|undefined,d=2)=>x===null||x===undefined?"—":Number(x).toFixed(d);
const pct=(x:number|null|undefined)=>x===null||x===undefined?"—":n2(x)+"%";
const fCurrency=(n:number)=>new Intl.NumberFormat("es-DO").format(n);
const NAV: {section:string;items:{id:View|null;label:string;icon:LucideIcon;sub?:string}[]}[]=[
 {section:"WORKSPACE",items:[{id:"home",label:"Visión general",icon:LayoutDashboard}]},
 {section:"LABORATORIO",items:[{id:"sessions",label:"Creador de algoritmos",icon:WandSparkles},{id:null,label:"Portafolios",icon:Layers3,sub:"Próximamente"}]},
 {section:"INFRAESTRUCTURA",items:[{id:"datasets",label:"Datos históricos",icon:Database},{id:null,label:"IDE de estrategias",icon:TerminalSquare,sub:"Próximamente"}]}
];
function Brand(){return <div className="brand-mark"><div className="brand-symbol"><Activity size={19} strokeWidth={2.6}/></div><div className="brand-copy">TRADING<span>QUANT</span><small>QUANT RESEARCH PLATFORM</small></div></div>}
function Badge({children,kind="neutral"}:{children:React.ReactNode;kind?:"neutral"|"accent"|"good"|"warning"}){return <span className={`badge badge-${kind}`}>{children}</span>}
function SectionHeading({eyebrow,title,description,right}:{eyebrow?:string;title:string;description?:string;right?:React.ReactNode}){return <div className="section-heading"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2>{description&&<p>{description}</p>}</div>{right}</div>}
function Illustration(){
 return <div className="illustration"><div className="illustration-head"><span className="mini-dot"/><span>RESEARCH PIPELINE</span><span className="mono dim">SYSTEM / 01</span></div>
 <div className="pipeline"><div className="pipe-node"><Database size={16}/><span>Market data</span></div><div className="pipe-link"/><div className="pipe-node active"><GitBranch size={16}/><span>Discovery</span></div><div className="pipe-link"/><div className="pipe-node"><ShieldCheck size={16}/><span>Validation</span></div></div>
 <div className="chart-grid"><div className="chart-top"><span>ESTRUCTURA DEL MOTOR</span><span className="mono">01—03</span></div><svg viewBox="0 0 520 154" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#76f4c1" stopOpacity=".25"/><stop offset="100%" stopColor="#76f4c1" stopOpacity="0"/></linearGradient></defs><path d="M0 123 L31 121 L53 105 L73 114 L103 101 L126 109 L152 86 L178 94 L203 82 L228 88 L251 63 L276 75 L294 57 L320 68 L343 42 L364 49 L392 31 L419 49 L442 28 L467 43 L496 20 L520 23 V154 H0 Z" fill="url(#lineFill)"/><path d="M0 123 L31 121 L53 105 L73 114 L103 101 L126 109 L152 86 L178 94 L203 82 L228 88 L251 63 L276 75 L294 57 L320 68 L343 42 L364 49 L392 31 L419 49 L442 28 L467 43 L496 20 L520 23" fill="none" stroke="#7af0c1" strokeWidth="2.5" vectorEffect="non-scaling-stroke"/><path d="M0 127 H520 M0 90 H520 M0 53 H520 M0 16 H520" stroke="#ffffff" opacity=".07" fill="none" strokeDasharray="3 5"/><circle cx="496" cy="20" r="5" fill="#7af0c1" stroke="#0c2530" strokeWidth="4"/></svg><div className="chart-footer"><span>ALGORITMOS</span><span>PRUEBAS OOS</span><span>MONTE CARLO</span></div></div><div className="illustration-caption"><Sparkles size={13}/> Diagrama conceptual; no representa rentabilidad ni resultados reales.</div></div>
}
function Field({title,hint,children}:{title:string;hint?:string;children:React.ReactNode}){return <label className="field"><span className="field-title">{title}</span>{children}{hint&&<small>{hint}</small>}</label>}
function InfoCard({icon:Icon,title,desc}:{icon:LucideIcon;title:string;desc:string}){return <div className="info-card"><div className="info-icon"><Icon size={20}/></div><h3>{title}</h3><p>{desc}</p></div>}
function MetricBlock({label,value,foot,icon:Icon}:{label:string;value:string;foot:string;icon:LucideIcon}){return <div className="metric-card"><div className="metric-head"><span>{label}</span><Icon size={18}/></div><strong>{value}</strong><span className="metric-foot">{foot}</span></div>}
function Empty({title,description,action,icon:Icon=FlaskConical}:{title:string;description:string;action?:React.ReactNode;icon?:LucideIcon}){return <div className="empty-state"><div className="empty-icon"><Icon size={25}/></div><h3>{title}</h3><p>{description}</p>{action}</div>}
function StepNumber({num,active,done}:{num:number;active:boolean;done:boolean}){return <span className={`step-number ${active?"selected":""} ${done?"done":""}`}>{done?<Check size={14}/>:num}</span>}
function MiniMetric({label,value}:{label:string;value:string}){return <div className="mini-metric"><span>{label}</span><strong>{value}</strong></div>}
export default function Page(){
 const [view,setView]=useState<View>("home");
 const [mobile,setMobile]=useState(false);
 const [step,setStep]=useState(0);
 const [cfg,setCfg]=useState<Config>(DEFAULT);
 const [datasets,setDatasets]=useState<Dataset[]>([]);
 const [runs,setRuns]=useState<RunResult[]>([]);
 const [runsHydrated,setRunsHydrated]=useState(false);
 const [sessions,setSessions]=useState<AlgoSession<Config>[]>([]);
 const [activeSessionId,setActiveSessionId]=useState<string|null>(null);
 const [sessionsHydrated,setSessionsHydrated]=useState(false);
 const [selected,setSelected]=useState<string|null>(null);
 const [loading,setLoading]=useState(false);
 const [uploading,setUploading]=useState(false);
 const [uploadProgress,setUploadProgress]=useState<{percent:number;phase:string;uploaded:number;total:number}|null>(null);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");

 const [apiStatus,setApiStatus]=useState<"unknown"|"checking"|"online"|"offline">("unknown");
 const API=DEFAULT_API;
 const authHeaders:Record<string,string>={};
 const [selectedCandidate,setSelectedCandidate]=useState<string|null>(null);
 const [jobStatus,setJobStatus]=useState<{id:string;status:string;phase:string;percent:number;checked:number;total:number;elapsed_seconds:number;error?:string|null}|null>(null);
 const [profile,setProfile]=useState<AssetDiagnostics|null>(null);
 const [analyzing,setAnalyzing]=useState(false);
 const fileRef=useRef<HTMLInputElement>(null);
 const currentRun=runs.find(r=>r.id===selected)||runs[0];
 const validated=runs.flatMap(r=>r.candidates).filter(c=>c.accepted);
 const count=runs.reduce((acc,r)=>acc+r.tested,0);
 useEffect(()=>{try{localStorage.removeItem("tq_api_url");sessionStorage.removeItem("tq_api_token");const d=localStorage.getItem("tq_datasets");const r=localStorage.getItem("tq_runs");const c=localStorage.getItem("tq_cfg");const s=localStorage.getItem("tq_sessions_v1");if(d)setDatasets(JSON.parse(d));const previousRuns:RunResult[]=r?JSON.parse(r):[];if(r)setRuns(previousRuns);if(c)setCfg({...DEFAULT,...JSON.parse(c)});if(s){setSessions(JSON.parse(s))}else if(previousRuns.length){setSessions(previousRuns.map(run=>({id:"migrated-"+run.id,name:run.config.name,symbol:run.config.symbol,config:run.config,createdAt:run.created_at,updatedAt:run.created_at,status:"results" as const,runId:run.id,found:run.candidates.length})))}}catch{/* ignore corrupt local draft */}finally{setSessionsHydrated(true)}},[]);
 useEffect(()=>{localStorage.setItem("tq_datasets",JSON.stringify(datasets))},[datasets]);
 useEffect(()=>{readExperiments<RunResult>().then(saved=>{
   if(saved.length)setRuns(saved.sort((a,b)=>b.created_at.localeCompare(a.created_at)));
 }).catch(()=>{/* localStorage fallback still works */}).finally(()=>setRunsHydrated(true))},[]);
 useEffect(()=>{if(!runsHydrated)return;writeExperiments(runs).catch(()=>setError("No se pudieron persistir los resultados en IndexedDB. Exporta tu investigación antes de cerrar el navegador."));},[runs,runsHydrated]);
 useEffect(()=>{localStorage.setItem("tq_cfg",JSON.stringify(cfg))},[cfg]);
 useEffect(()=>{if(sessionsHydrated)localStorage.setItem("tq_sessions_v1",JSON.stringify(sessions))},[sessions,sessionsHydrated]);
 useEffect(()=>{if(activeSessionId)setSessions(prev=>prev.map(s=>s.id===activeSessionId?{...s,name:cfg.name,symbol:cfg.symbol,config:cfg,updatedAt:new Date().toISOString()}:s))},[cfg,activeSessionId]);
 function change<K extends keyof Config>(key:K,value:Config[K]){setCfg(p=>({...p,[key]:value}));setError("");if(["dataset_id","symbol","timeframe","timeframes","start_date","end_date","families","capital"].includes(String(key)))setProfile(null)}
 function open(v:View){setView(v);setMobile(false);setError("");setNotice("")}
 function start(){open("sessions")}
 function createSession(name:string){
   const symbol=DEFAULT.symbol;
   const next:AlgoSession<Config>={id:crypto.randomUUID(),name,symbol,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),status:"draft",config:{...DEFAULT,name,symbol}};
   setSessions(prev=>[next,...prev]);
 }
 function editSession(id:string){
   const target=sessions.find(s=>s.id===id);
   if(!target)return;
   setActiveSessionId(target.id);setCfg({...DEFAULT,...target.config,timeframes:target.config.timeframes?.length?target.config.timeframes:[target.config.timeframe||"5m"],indicator_ranges:{...DEFAULT_INDICATOR_RANGES,...target.config.indicator_ranges},macro_indicators:target.config.macro_indicators||[],macro_rules:target.config.macro_rules||{},capital:{...DEFAULT_CAPITAL,...target.config.capital},schedule:{...DEFAULT_SCHEDULE,...target.config.schedule},funding:{...DEFAULT_FUNDING,...target.config.funding},advanced_modifiers:{...DEFAULT_ADVANCED,...target.config.advanced_modifiers},quality:{...DEFAULT_QUALITY,...target.config.quality},walk_forward:{...DEFAULT_WALK_FORWARD,...target.config.walk_forward},multiverse:{...DEFAULT_MULTIVERSE,...target.config.multiverse},costs:{...DEFAULT_COSTS,...target.config.costs}});setStep(0);open("builder");
 }
 function deleteSession(id:string){
   const target=sessions.find(s=>s.id===id);
   setSessions(prev=>prev.filter(s=>s.id!==id));
   if(target?.runId)setRuns(prev=>prev.filter(r=>r.id!==target.runId));
   if(activeSessionId===id)setActiveSessionId(null);
 }
 async function upload(file:File){
  setUploading(true);setError("");setNotice("");
  setUploadProgress({percent:0,phase:"Comprobando conexión",uploaded:0,total:file.size});
  try{
   if(!API)throw Error("No se ha configurado un servidor FastAPI.");
   if(!/\.csv$/i.test(file.name))throw Error("Selecciona un archivo .csv original de MetaTrader 5.");
   if(!file.size)throw Error("El archivo CSV está vacío.");
   const maxFileMiB=1024;
   if(file.size>maxFileMiB*1024*1024)throw Error("Este motor admite un máximo de "+maxFileMiB+" MiB por archivo CSV.");
   const firstLine=(await file.slice(0,4096).text()).replace(/^\uFEFF/,"").split(/\r?\n/,1)[0];
   const mt5=/<DATE>\s+<TIME>\s+<OPEN>\s+<HIGH>\s+<LOW>\s+<CLOSE>/i.test(firstLine);
   const explain=async(resp:Response)=>{
    const raw=await resp.text();
    let data:Record<string,unknown>={};
    try{data=JSON.parse(raw)}catch{}
    if(!resp.ok){
      const detail=typeof data.detail==="string"?data.detail:"";
      if(resp.status===401)throw Error("El motor local rechazó el acceso (401). Reinicia el iniciador de TradingQuant.");
      if(resp.status===404)throw Error("Subida no encontrada (404). Vuelve a importarla si el proceso local se reinició.");
      if(resp.status===409)throw Error(detail||"Se interrumpió el orden de los bloques de subida.");
      if(resp.status===413)throw Error("Archivo o bloque demasiado grande para el motor local (HTTP 413).");
      if(resp.status===422)throw Error("CSV no válido: "+(detail||"Revisa el archivo MT5."));
      if(resp.status>=500)throw Error("El motor local respondió HTTP "+resp.status+". Revisa su consumo de memoria y sus registros.");
      throw Error(detail||"Error HTTP "+resp.status+" durante la importación.");
    }
    return data;
   };
   const send=async(url:string,opts:RequestInit)=>{
    let response:Response;
    try{response=await fetch(url,{...opts,cache:"no-store"})}
    catch{throw Error("La conexión con FastAPI local se interrumpió. Comprueba que esté abierta la ventana «Motor Científico».");}
    return explain(response);
   };
   const auth=await send(API+"/api/auth/check",{headers:authHeaders});
   if(auth.authorized!==true)throw Error("El servidor no confirmó el acceso autenticado.");
   const initiated=await send(API+"/api/datasets/uploads",{
     method:"POST",headers:{"Content-Type":"application/json",...authHeaders},
     body:JSON.stringify({filename:file.name,size_bytes:file.size})
   });
   const uploadId=String(initiated.id||"");
   const chunkBytes=Number(initiated.chunk_bytes);
   if(!/^[0-9a-f-]{36}$/i.test(uploadId)||chunkBytes!==2*1024*1024)
      throw Error("La API local devolvió un identificador o tamaño de bloque inválido.");
   let transferred=0;
   for(let offset=0,index=0;offset<file.size;offset+=chunkBytes,index++){
      const buffer=await file.slice(offset,Math.min(file.size,offset+chunkBytes)).arrayBuffer();
      const hash=new Uint8Array(await crypto.subtle.digest("SHA-256",buffer));
      const sha=Array.from(hash,b=>b.toString(16).padStart(2,"0")).join("");
      let sent=false;
      for(let attempt=0;attempt<3&&!sent;attempt++){
        try{
          const progress=await send(API+"/api/datasets/uploads/"+uploadId+"/chunks/"+index,{
            method:"PUT",headers:{"Content-Type":"application/octet-stream","X-Chunk-SHA256":sha,...authHeaders},
            body:buffer
          });
          transferred=Number(progress.received_bytes);
          if(transferred<offset+buffer.byteLength)throw Error("El motor local no confirmó todos los bytes del bloque.");
          sent=true;
        }catch(e){
          if(attempt===2)throw Error("La subida se interrumpió en el bloque "+(index+1)+" de "+Math.ceil(file.size/chunkBytes)+". "+(e instanceof Error?e.message:"Error de red"));
          await new Promise(resolve=>setTimeout(resolve,1000*(attempt+1)));
        }
      }
      setUploadProgress({percent:Math.min(90,Math.round(90*transferred/file.size)),phase:"Enviando bloques MT5 · "+(index+1)+"/"+Math.ceil(file.size/chunkBytes),uploaded:transferred,total:file.size});
   }
   setUploadProgress({percent:94,phase:"Validando columnas y velas en el servidor",uploaded:file.size,total:file.size});
   await send(API+"/api/datasets/uploads/"+uploadId+"/complete",{method:"POST",headers:authHeaders});
   let result:Record<string,unknown>|null=null;
   for(let attempt=0;attempt<900;attempt++){
     await new Promise(resolve=>setTimeout(resolve,1200));
     const status=await send(API+"/api/datasets/uploads/"+uploadId,{headers:authHeaders});
     if(status.status==="failed")throw Error("Validación del CSV falló: "+String(status.error||"Error desconocido."));
     if(status.status==="ready"){
       result=status.dataset as Record<string,unknown>;
       break;
     }
     setUploadProgress({percent:95+Math.min(4,Math.floor(attempt/30)),phase:"Validando histórico sin cargarlo entero en memoria",uploaded:file.size,total:file.size});
   }
   if(!result||typeof result.id!=="string"||typeof result.rows!=="number")
      throw Error("La validación local excedió el tiempo permitido. Comprueba la ventana «Motor Científico».");
   setDatasets(p=>[result as Dataset,...p.filter(x=>x.id!==result!.id)]);
   change("dataset_id",result.id);
   setUploadProgress({percent:100,phase:"Importación terminada",uploaded:file.size,total:file.size});
   setNotice("CSV importado: "+String(result.filename)+" · "+fCurrency(result.rows)+" velas válidas"+(mt5?" · MetaTrader 5":"")+".");
  }catch(e){setError(e instanceof Error?e.message:"No se pudo importar el CSV.");}
  finally{setUploading(false);if(fileRef.current)fileRef.current.value="";}
 }
 async function checkBackend(){
  if(!API){setError("No hay dirección configurada para el motor.");return}
  setApiStatus("checking");
  try{
   const abort=new AbortController();
   const timeout=setTimeout(()=>abort.abort(),10000);
   try{
    const response=await fetch(API+"/health",{cache:"no-store",signal:abort.signal});
    if(!response.ok)throw Error("HTTP "+response.status);
    const body=await response.json();
    if(body.status!=="ok")throw Error("Respuesta no válida del backend.");
    const authorized=await fetch(API+"/api/auth/check",{cache:"no-store",signal:abort.signal,headers:authHeaders});
    if(!authorized.ok)throw Error(authorized.status===401?"La API local rechazó el acceso. Reinicia el iniciador de TradingQuant.":"La API rechazó la autenticación (HTTP "+authorized.status+").");
    setApiStatus("online");setNotice("Motor FastAPI local conectado. No requiere token ni conexión a la nube.");
   }finally{clearTimeout(timeout)}
  }catch(e){setApiStatus("offline");setError("El motor no responde desde este navegador: "+(e instanceof Error?e.message:"error de conexión o CORS"))}
 }
 async function analyzeHistorical(){
   if(!cfg.dataset_id){setError("Selecciona un CSV histórico para analizar los límites del instrumento.");return}
   if(!API){setError("El proceso FastAPI local no está disponible en 127.0.0.1:8000.");return}
   setAnalyzing(true);setError("");
   try{
    const resp=await fetch(API+"/api/explorations/preflight",{method:"POST",headers:{"Content-Type":"application/json",...authHeaders},body:JSON.stringify(cfg)});
    const data=await resp.json();
    if(!resp.ok)throw Error(typeof data.detail==="string"?data.detail:"No se pudo analizar el CSV.");
    setProfile(data as AssetDiagnostics);
   }catch(e){setError(e instanceof Error?e.message:"Error al analizar el dataset.");}
   finally{setAnalyzing(false)}
 }
 async function explore(){
  if(!API){setError("El motor local FastAPI no está disponible en 127.0.0.1:8000. Abre el iniciador de TradingQuant.");return}
  if(!cfg.dataset_id){setError("Debes importar datos OHLC para investigar.");return}
  if(cfg.macro_indicators?.length){setError("Hay reglas macro sin fuente verificable; retíralas antes de ejecutar.");return}
  if(!cfg.timeframes?.length||!cfg.families.length){setError("Selecciona temporalidades e indicadores válidos.");return}
  setLoading(true);setError("");setNotice("");
  if(activeSessionId)setSessions(prev=>prev.map(t=>t.id===activeSessionId?{...t,status:"running"}:t));
  try{
   const resp=await fetch(API+"/api/explorations/start",{method:"POST",headers:{"Content-Type":"application/json",...authHeaders},body:JSON.stringify(cfg)});
   const body=await resp.json();
   if(!resp.ok)throw Error(typeof body.detail==="string"?body.detail:"No se pudo iniciar la exploración.");
   setJobStatus(body);open("running");
   const jobId=String(body.id);
   localStorage.setItem("tq_active_job",JSON.stringify({jobId,sessionId:activeSessionId}));
   while(true){
     await new Promise(resolve=>setTimeout(resolve,1200));
     const stateResponse=await fetch(API+"/api/explorations/jobs/"+encodeURIComponent(jobId),{cache:"no-store",headers:authHeaders});
     if(!stateResponse.ok)throw Error("El trabajo perdió conexión con el motor. Verifica que FastAPI permanezca activo.");
     const state=await stateResponse.json();
     setJobStatus(state);
     if(state.status==="failed")throw Error(state.error||"El motor canceló la exploración.");
     if(state.status==="completed"){
       const resultResponse=await fetch(API+"/api/explorations/jobs/"+encodeURIComponent(jobId)+"/result",{cache:"no-store",headers:authHeaders});
       const result=await resultResponse.json();
       if(!resultResponse.ok)throw Error(result.detail||"No se pudo recuperar el resultado de la exploración.");
       setRuns(prev=>[result,...prev.filter(t=>t.id!==result.id)]);
       if(activeSessionId)setSessions(prev=>prev.map(t=>t.id===activeSessionId?{...t,status:"results",runId:result.id,found:result.candidates.length}:t));
       localStorage.removeItem("tq_active_job");
       setSelected(result.id);setSelectedCandidate(null);open("results");
       setNotice("Exploración real finalizada: "+result.tested+" probadas, "+result.accepted+" candidatas aprobadas.");
       break;
     }
   }
  }catch(e){
   localStorage.removeItem("tq_active_job");
   if(activeSessionId)setSessions(prev=>prev.map(t=>t.id===activeSessionId?{...t,status:t.runId?"results":"draft"}:t));
   setError(e instanceof Error?e.message:"Motor de backtesting no disponible.");
  }finally{setLoading(false)}
 }
 useEffect(()=>{
   if(!API)return;
   let alive=true;
   const saved=localStorage.getItem("tq_active_job");
   if(!saved)return;
   let id="",sessionId:string|null=null;
   try{const job=JSON.parse(saved);id=String(job.jobId);sessionId=job.sessionId??null}catch{localStorage.removeItem("tq_active_job");return}
   if(!id)return;
   const restore=async()=>{
    setView("running");setLoading(true);
    while(alive){
     try{
      const response=await fetch(API+"/api/explorations/jobs/"+encodeURIComponent(id),{cache:"no-store",headers:authHeaders});
      if(!response.ok)throw Error("No se encontró el trabajo en el motor. Es posible que la API se haya reiniciado.");
      const status=await response.json();
      if(!alive)return;
      setJobStatus(status);
      if(status.status==="failed")throw Error(status.error||"La exploración no pudo continuar.");
      if(status.status==="completed"){
       const resultResponse=await fetch(API+"/api/explorations/jobs/"+encodeURIComponent(id)+"/result",{cache:"no-store",headers:authHeaders});
       if(!resultResponse.ok)throw Error("No se pudo recuperar la exploración terminada.");
       const result=await resultResponse.json();
       if(!alive)return;
       setRuns(old=>[result,...old.filter(t=>t.id!==result.id)]);
       if(sessionId)setSessions(old=>old.map(t=>t.id===sessionId?{...t,status:"results",runId:result.id,found:result.candidates.length}:t));
       setSelected(result.id);setView("results");setLoading(false);
       localStorage.removeItem("tq_active_job");
       return;
      }
      await new Promise(resolve=>setTimeout(resolve,1200));
     }catch(e){
      if(!alive)return;
      setError(e instanceof Error?e.message:"No se puede reanudar la exploración.");
      setLoading(false);setView("sessions");
      localStorage.removeItem("tq_active_job");
      return;
     }
    }
   };
   void restore();
   return ()=>{alive=false};
 },[API]);
 const stepsComplete=Boolean(cfg.dataset_id&&cfg.name.trim()&&cfg.families.length);
 return <div className="shell">
 <aside className={`sidebar ${mobile?"sidebar-open":""}`}>
 <div className="sidebar-brand"><Brand/><button className="icon-only mobile-close" onClick={()=>setMobile(false)} aria-label="Cerrar menú"><X size={19}/></button></div>
 <div className="workspace-selector"><div className="workspace-avatar">TQ</div><span><strong>Quant Research</strong><small>Entorno personal</small></span><span className="workspace-arrow">⌄</span></div>
 <div className="nav-scroller">{NAV.map(group=><div className="nav-section" key={group.section}><div className="nav-title">{group.section}</div>{group.items.map(item=><button key={item.label} disabled={!item.id} onClick={()=>item.id&&open(item.id)} className={`nav-item ${(view===item.id||(item.id==="sessions"&&view==="builder"))?"nav-active":""}`}><item.icon size={17}/><span>{item.label}</span>{item.sub?<span className="soon">PRONTO</span>:(view===item.id||(item.id==="sessions"&&view==="builder"))?<span className="active-bar"/>:null}</button>)}</div>)}</div>
 <div className="sidebar-footer"><div className="sidebar-help"><div className="help-icon"><CircleHelp size={17}/></div><div><strong>Centro de investigación</strong><p>Documentación y arquitectura</p></div><a href="https://github.com/AnthonyHenriquezLuciano/TradingQuant" target="_blank" rel="noreferrer" aria-label="Abrir repositorio"><ArrowUpRight size={16}/></a></div><div className="profile"><div className="profile-avatar">TQ</div><div><strong>TradingQuant</strong><span>Workspace · V0.1</span></div><Settings2 size={16}/></div></div>
 </aside>
 {mobile&&<button className="mobile-overlay" aria-label="Cerrar menú" onClick={()=>setMobile(false)}/>}
 <div className="main-shell">
 <header className="topbar"><div className="topbar-left"><button className="icon-only mobile-menu" onClick={()=>setMobile(true)} aria-label="Abrir menú"><Menu size={21}/></button><span className="breadcrumb-root">TradingQuant</span><ChevronRight size={14}/><span className="breadcrumb-mid">Laboratorio</span><ChevronRight size={14}/><strong>{view==="home"?"Visión general":view==="builder"?"Configuración de sesión":view==="sessions"?"Creador de algoritmos":view==="datasets"?"Datos históricos":view==="validation"?"Validación científica":"Exploraciones"}</strong></div><div className="topbar-right"><span className="environment"><span/> RESEARCH MODE</span><a className="topbar-docs" target="_blank" rel="noreferrer" href="https://github.com/AnthonyHenriquezLuciano/TradingQuant"><BookOpen size={16}/><span>Documentación</span></a><div className="topbar-profile">TQ</div></div></header>
 <main className="content">
 {error&&<div className="alert alert-error" role="alert"><AlertTriangle size={18}/><span>{error}</span><button onClick={()=>setError("")} aria-label="Cerrar aviso"><X size={16}/></button></div>}
 {notice&&<div className="alert alert-success" role="status"><CheckCircle2 size={18}/><span>{notice}</span><button onClick={()=>setNotice("")} aria-label="Cerrar aviso"><X size={16}/></button></div>}
 {view==="home"&&<><div className="page-intro"><div><div className="eyebrow">TRADINGQUANT / LAB 01 <span className="eyebrow-line"/></div><h1>Construye evidencia.<br/><span>Encuentra tu ventaja.</span></h1><p>Un laboratorio de investigación cuantitativa para descubrir, probar y validar estrategias antes de arriesgar capital.</p><div className="intro-actions"><button className="btn btn-primary" onClick={start}><Plus size={17}/> Nueva exploración <ArrowRight size={16}/></button><button className="btn btn-ghost" onClick={()=>open("datasets")}><Database size={16}/> Importar datos</button></div></div><Badge kind="accent"><span className="pulse-dot"/> FASE 01 · BETA</Badge></div>
 <div className="metric-grid"><MetricBlock icon={FlaskConical} label="EXPLORACIONES" value={fCurrency(runs.length)} foot="Sesiones ejecutadas"/><MetricBlock icon={GitBranch} label="CANDIDATOS PROBADOS" value={fCurrency(count)} foot="Con datos históricos"/><MetricBlock icon={ShieldCheck} label="FILTRO PRELIMINAR" value={fCurrency(validated.length)} foot="No equivale a aprobación final"/><MetricBlock icon={Database} label="DATASETS" value={String(datasets.length).padStart(2,"0")} foot="Archivos cargados"/></div>
 <div className="hero-panel"><div className="hero-left"><div className="feature-label"><span className="feature-ping"/><span>RESEARCH ENGINE / V0.1</span></div><h2>De una hipótesis<br/>a una <em>estrategia medible.</em></h2><p>Explora combinaciones de señales, mide su desempeño fuera de muestra y somete los resultados a escenarios de riesgo. Menos intuición. Más proceso.</p><div className="hero-list"><span><CheckCircle2 size={15}/> Descubrimiento parametrizado</span><span><CheckCircle2 size={15}/> Split IS / OOS cronológico</span><span><CheckCircle2 size={15}/> Bootstrap Monte Carlo</span></div><button className="link-button" onClick={start}>Abrir creador de algoritmos <ArrowRight size={17}/></button></div><Illustration/></div>
 <div className="section-space"><SectionHeading eyebrow="TU ACTIVIDAD" title="Exploraciones recientes" description="Cada búsqueda conserva su configuración y resultados en este navegador." right={<button className="btn btn-outline btn-small" onClick={()=>open("results")}>Ver todas <ArrowRight size={15}/></button>}/>{runs.length===0?<Empty title="Tu primera exploración empieza aquí" description="Todavía no has ejecutado búsquedas. Importa un CSV OHLC y configura la primera hipótesis desde el creador." action={<button className="btn btn-primary btn-small" onClick={start}><Plus size={16}/> Crear exploración</button>}/>:<div className="run-list">{runs.slice(0,3).map(r=><button className="run-row" key={r.id} onClick={()=>{setSelected(r.id);open("results")}}><div className="run-glyph"><FlaskConical size={19}/></div><div className="run-detail"><strong>{r.config.name}</strong><small>{r.config.symbol} · {r.config.timeframe} · {formatDate(r.created_at)}</small></div><div className="run-count"><strong>{r.tested}</strong><span>evaluados</span></div><Badge kind={r.accepted>0?"good":"neutral"}>{r.accepted} filtrados</Badge><ChevronRight size={17}/></button>)}</div>}</div>
 <div className="section-space"><SectionHeading eyebrow="METODOLOGÍA" title="Un proceso que puedes auditar" description="La calidad de la estrategia depende del método de validación, no de una curva atractiva."/><div className="info-grid"><InfoCard icon={SlidersHorizontal} title="01. Genera" desc="Busca reglas interpretables y rangos de parámetros sobre un dataset seleccionado."/><InfoCard icon={Microscope} title="02. Contrasta" desc="Separa entrenamiento y prueba temporal para reducir el sesgo de selección."/><InfoCard icon={Shield} title="03. Protege" desc="Evalúa límites de pérdida y remuestreo antes de promover candidatos."/></div></div></>}
 {view==="sessions"&&<SessionOverview sessions={sessions} onCreate={createSession} onOpen={editSession} onDelete={deleteSession} onResults={id=>{const sess=sessions.find(t=>t.id===id);if(sess?.runId&&runs.some(t=>t.id===sess.runId)){setSelected(sess.runId);setSelectedCandidate(null);open("results")}else setError("Esta sesión todavía no tiene un resultado disponible en el navegador actual.")}}/>}
 {view==="builder"&&<StrategyConfigurator config={cfg} datasetList={datasets} loading={loading} onChange={change} onUpload={()=>open("datasets")} profile={profile} analyzing={analyzing} onAnalyze={analyzeHistorical} onExecute={explore} onBack={()=>open("sessions")}/>}
 {view==="datasets"&&<><div className="page-heading"><div><div className="eyebrow">INFRAESTRUCTURA / HISTORICAL DATA</div><h1>Datos históricos</h1><p>El fundamento del laboratorio es un conjunto de datos verificable y consistente.</p></div><button className="btn btn-primary" onClick={()=>fileRef.current?.click()} disabled={uploading}><Plus size={17}/> Subir CSV</button></div><div className="tq-api-settings"><div><strong><Database size={16}/> Motor científico local</strong><p>FastAPI, Polars, Numba, Monte Carlo y backtesting en tu PC. Sin Render ni servicios de terceros.</p></div><div className="tq-api-controls"><code>http://127.0.0.1:8000</code><button type="button" className="btn btn-outline btn-small" onClick={checkBackend} disabled={apiStatus==="checking"}>{apiStatus==="checking"?"Verificando…":"Verificar motor local"}</button><span className={"tq-api-pill "+apiStatus}>{apiStatus==="online"?"Conectado":apiStatus==="offline"?"Desconectado":apiStatus==="checking"?"Comprobando":"Sin verificar"}</span></div><small>La API escucha solo en 127.0.0.1. Los CSV y resultados se conservan en tu PC.</small></div><input ref={fileRef} type="file" accept=".csv,text/csv" style={{display:"none"}} onChange={e=>e.target.files?.[0]&&upload(e.target.files[0])}/><div className="upload-drop" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!uploading&&e.dataTransfer.files?.[0])upload(e.dataTransfer.files[0])}} onClick={()=>!uploading&&fileRef.current?.click()} role="button" tabIndex={0} onKeyDown={e=>(e.key==="Enter"||e.key===" ")&&fileRef.current?.click()}><div className="upload-drop-icon">{uploading?<LoaderCircle size={29} className="spin"/>:<UploadCloud size={29}/>}</div><h3>{uploading?(uploadProgress?.phase||"Importando CSV…"):"Arrastra tu investigación al laboratorio"}</h3><p>Haz clic para seleccionar un archivo CSV con velas OHLC.</p><button className="btn btn-outline" disabled={uploading} onClick={e=>{e.stopPropagation();fileRef.current?.click()}}><FileSpreadsheet size={16}/> Seleccionar archivo</button>{uploadProgress&&<div className="tq-upload-progress" role="progressbar" aria-valuenow={uploadProgress.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Progreso de importación CSV"><div><span>{uploadProgress.phase}</span><strong>{uploadProgress.percent}%</strong></div><div className="tq-r-track"><span style={{width:uploadProgress.percent+"%"}}/></div><small>{(uploadProgress.uploaded/(1024*1024)).toFixed(1)} / {(uploadProgress.total/(1024*1024)).toFixed(1)} MiB transferidos</small></div>}<small>CSV · hasta 150 MB · timestamp u columnas date + time · zona horaria conservada</small></div><div className="section-space"><SectionHeading eyebrow="LIBRERÍA" title="Mis datasets" description="Metadatos en navegador; archivos conservados en el almacenamiento local de la API." right={<Badge>{datasets.length} ARCHIVOS</Badge>}/>{datasets.length===0?<Empty icon={Database} title="No hay datasets importados" description="Sube datos OHLC de MetaTrader 5 para ejecutar tus primeras exploraciones."/>:<div className="dataset-list">{datasets.map(d=><div className="dataset-row" key={d.id}><span className="dataset-icon"><Database size={18}/></span><div><strong>{d.filename}</strong><small>{d.start} → {d.end}</small></div><span className="dataset-rows">{fCurrency(d.rows)} velas</span><Badge kind={cfg.dataset_id===d.id?"good":"neutral"}>{cfg.dataset_id===d.id?"SELECCIONADO":"CSV"}</Badge><button className="btn btn-outline btn-small" onClick={()=>{change("dataset_id",d.id);open("builder")}}>Usar <ArrowRight size={14}/></button></div>)}</div>}</div><div className="aside-note wide"><AlertTriangle size={17}/><p>Fuente horaria: se respeta la hora original del CSV; revisa horario del bróker y cambios DST. Los datos no se envían a un bróker ni se usan para ejecución real.</p></div></>}
 {view==="running"&&<div className="tq-running"><div className="tq-r-eyebrow">MOTOR CIENTÍFICO / EJECUCIÓN REAL</div><h1>Exploración en progreso</h1><p>{cfg.name} · {cfg.symbol} · {cfg.timeframes.join(", ")}</p><div className="tq-running-progress"><div><strong>{jobStatus?.percent??0}%</strong><span>{jobStatus?.phase||"Preparando"}</span></div><div className="tq-r-track"><span style={{width:String(jobStatus?.percent??0)+"%"}}/></div></div><div className="tq-r-metrics"><div className="tq-r-metric"><span>Candidatos evaluados</span><strong>{jobStatus?.checked??0}</strong></div><div className="tq-r-metric"><span>Presupuesto del tramo</span><strong>{jobStatus?.total??cfg.candidates}</strong></div><div className="tq-r-metric"><span>Tiempo transcurrido</span><strong>{jobStatus?.elapsed_seconds??0}s</strong></div><div className="tq-r-metric"><span>Estado</span><strong>{jobStatus?.status||"En cola"}</strong></div></div><div className="tq-r-note"><Info size={16}/> El progreso proviene del worker Python. Las fases de Monte Carlo y validación se calculan después de explorar. Mantén este motor activo hasta terminar.</div></div>}
 {view==="results"&&currentRun&&<ResearchResults run={currentRun} onSelect={id=>{setSelectedCandidate(id);open("detail")}} onEdit={()=>{const s=sessions.find(t=>t.runId===currentRun.id);if(s)editSession(s.id);else open("builder")}}/>}
 {view==="detail"&&currentRun&&selectedCandidate&&(()=>{const cand=currentRun.candidates.find(t=>t.id===selectedCandidate);return cand?<StrategyDetail run={currentRun} candidate={cand} onBack={()=>open("results")}/>:null})()}
 {(view==="validation")&&<><div className="page-heading"><div><div className="eyebrow">LABORATORIO / {view==="validation"?"ROBUSTNESS CHECK":"DISCOVERY SESSIONS"}</div><h1>{view==="validation"?"Validación científica":"Exploraciones"}</h1><p>{view==="validation"?"Compara entrenamiento, prueba fuera de muestra y sensibilidad al drawdown.":"Una visión transparente de tus pruebas y de los candidatos generados."}</p></div><button className="btn btn-primary" onClick={start}><Plus size={17}/> Nueva exploración</button></div>{runs.length===0?<Empty icon={view==="validation"?ShieldCheck:FlaskConical} title="Sin experimentos para analizar" description="Los resultados aparecerán aquí después de ejecutar una exploración con datos históricos." action={<button className="btn btn-primary btn-small" onClick={start}>Crear exploración <ArrowRight size={15}/></button>}/>:<><div className="result-selector"><span><FolderOpen size={16}/> Experimento</span><select value={currentRun?.id} onChange={e=>setSelected(e.target.value)}>{runs.map(r=><option key={r.id} value={r.id}>{r.config.name} · {formatDate(r.created_at)}</option>)}</select><Badge kind="neutral">{currentRun?.config.symbol} / {currentRun?.config.timeframe.toUpperCase()}</Badge></div>{currentRun&&<><div className="metric-grid results-metrics"><MetricBlock icon={GitBranch} label="EVALUADOS" value={String(currentRun.tested)} foot="Combinaciones ejecutadas"/><MetricBlock icon={ShieldCheck} label="FILTRO PRELIMINAR" value={String(currentRun.accepted)} foot="Con criterios OOS"/><MetricBlock icon={BarChart3} label="FUERA DE MUESTRA" value={String(100-currentRun.config.is_ratio)+"%"} foot="Tramo final reservado"/><MetricBlock icon={Microscope} label="MONTE CARLO" value={fCurrency(currentRun.config.mc_iterations)} foot="Remuestreos por candidato"/></div>{currentRun.warnings.length>0&&<div className="subtle-box warning" style={{marginBottom:20}}><AlertTriangle size={18}/>{currentRun.warnings.join(" ")}</div>}<div className="table-panel"><div className="panel-table-header"><div><div className="eyebrow">{view==="validation"?"AUDITORÍA OOS":"CANDIDATOS DESCUBIERTOS"}</div><h2>Ranking de estrategias</h2><p>Ordenadas por métricas de entrenamiento (IS); el tramo OOS sirve para contrastar.</p></div><Badge>{currentRun.candidates.length} RESULTADOS</Badge></div><div className="table-scroll"><table className="result-table"><thead><tr><th>ALGORITMO</th><th>TRADES OOS</th><th>WIN RATE</th><th>PROFIT FACTOR</th><th>EXPECTATIVA</th><th>DD MÁX.</th>{currentRun.config.quality&&<><th>SHARPE OOS</th><th>DSR OOS</th></>}{currentRun.config.walk_forward?.enabled&&<th>WF PASS</th>}{currentRun.config.multiverse?.enabled&&<th>MULTIVERSO</th>}{currentRun.config.funding?.enabled&&<><th>PASS RATE OOS*</th><th>P20 DÍAS*</th><th>APRUEBAN A TIEMPO*</th></>}<th>ESTADO</th></tr></thead><tbody>{currentRun.candidates.map(c=><tr key={c.id}><td><strong>{c.family.replaceAll("_"," ")}</strong><small>{c.entry_mode?`Entrada: ${{market:"Mercado",stop:"Stop",limit:"Limit"}[c.entry_mode]} · `:""}{Object.entries(c.params).map(([k,v])=>`${k}=${v}`).join(" · ")}</small></td><td>{c.out_of_sample.trades}</td><td>{pct(c.out_of_sample.win_rate)}</td><td>{c.out_of_sample.profit_factor===null?"—":n2(c.out_of_sample.profit_factor)}</td><td className={c.out_of_sample.expectancy_r>=0?"positive":"negative"}>{n2(c.out_of_sample.expectancy_r,3)} R</td><td>{pct(c.out_of_sample.max_drawdown_pct)}</td>{currentRun.config.quality&&<><td>{n2(c.quality_oos?.sharpe)}</td><td>{n2(c.quality_oos?.dsr,3)}</td></>}{currentRun.config.walk_forward?.enabled&&<td>{pct(c.walk_forward?.pass_rate_pct)}</td>}{currentRun.config.multiverse?.enabled&&<td>{n2(c.multiverse?.score)} / 100</td>}{currentRun.config.funding?.enabled&&<><td>{pct(c.funding_evaluation_oos?.pass_rate_pct)}</td><td>{c.funding_evaluation_oos?.p20_days==null?"—":n2(c.funding_evaluation_oos.p20_days,1)+" días"}</td><td>{pct(c.funding_evaluation_oos?.pass_within_day_cap_pct)}</td></>}<td><Badge kind={c.accepted?"good":"warning"}>{c.accepted?"PASA FILTRO":"DESCARTADA"}</Badge></td></tr>)}</tbody></table></div></div><div className="validation-panel"><div className="validation-icon"><Microscope size={22}/></div><div><h3>Cómo interpretar estos resultados</h3><p>El motor selecciona reglas sobre IS y calcula su comportamiento OOS. Monte Carlo remuestrea trades OOS, lo que no equivale a una validación completa de regímenes, spreads dinámicos ni forward testing. *Las tasas y tiempos de fondeo son estimaciones por balance realizado, no replican drawdown flotante ni ejecución real.</p></div></div>{view==="validation"&&<div className="mc-grid">{currentRun.candidates.slice(0,4).map(c=><div className="mc-card" key={c.id}><div className="mc-title"><strong>{c.family.replaceAll("_"," ")}</strong><Badge kind={c.accepted?"good":"neutral"}>{c.accepted?"APTO*":"RECHAZADO"}</Badge></div>{currentRun.config.quality&&<><div className="mc-stat"><span>Sharpe IS / OOS (realizado)</span><strong>{n2(c.quality_is?.sharpe)} / {n2(c.quality_oos?.sharpe)}</strong></div><div className="mc-stat"><span>DSR IS / OOS · N intentos</span><strong>{n2(c.quality_is?.dsr,3)} / {n2(c.quality_oos?.dsr,3)} · {c.quality_is?.dsr_trials??"—"}</strong></div></>}
 {currentRun.config.walk_forward?.enabled&&<><div className="mc-stat"><span>Walk-Forward ventanas que aprueban</span><strong>{pct(c.walk_forward?.pass_rate_pct)} · {c.walk_forward?.tested_windows??0} ventanas</strong></div><div className="mc-stat"><span>WFE mediana</span><strong>{n2(c.walk_forward?.median_wfe,3)}</strong></div></>}
 {currentRun.config.multiverse?.enabled&&<><div className="mc-stat"><span>Multiverso score / universos</span><strong>{n2(c.multiverse?.score)} / 100 · {c.multiverse?.universes??"—"}</strong></div><div className="mc-stat"><span>Supervivencia sintética</span><strong>{pct(c.multiverse?.survival_pct)}</strong></div></>}
 <div className="mc-stat"><span>Coste ida/vuelta estimado</span><strong>{n2(c.estimated_cost_bps,3)} bps</strong></div>
 <div className="mc-stat"><span>DD P95 bootstrap</span><strong>{pct(c.monte_carlo.p95_drawdown_pct)}</strong></div><div className="mc-stat"><span>{"P(DD ≥ " + currentRun.config.prop_max_pct + "%)"}</span><strong>{pct(c.monte_carlo.probability_10pct_drawdown)}</strong></div>{currentRun.config.funding?.enabled&&<><div className="mc-stat"><span>Pass Rate IS estimado*</span><strong>{pct(c.funding_evaluation_is?.pass_rate_pct)}</strong></div><div className="mc-stat"><span>P20 / P50 / P80 OOS (días)*</span><strong>{[c.funding_evaluation_oos?.p20_days,c.funding_evaluation_oos?.p50_days,c.funding_evaluation_oos?.p80_days].map(x=>x==null?"—":n2(x,0)).join(" / ")}</strong></div><div className="mc-stat"><span>Aprobación dentro del plazo OOS*</span><strong>{pct(c.funding_evaluation_oos?.pass_within_day_cap_pct)}</strong></div></>}<p>{c.reasons.length?c.reasons.join(" · "):"Pasa controles mínimos de esta fase."}</p></div>)}</div>}</>}</>}</>}
 <div className="bottom-stamp"><span><span className="bottom-dot"/> TRADINGQUANT ENGINE · BUILD 0.1</span><span>Diseñado para investigación · No es asesoramiento financiero</span></div>
 </main></div></div>;
}
