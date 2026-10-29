"use client";

import {useState} from "react";
import {
 ArrowLeft, ArrowRight, Check, ChevronDown, CircleHelp, Database,
 Dna, FlaskConical, LoaderCircle, Play, Settings2, ShieldCheck,
 SlidersHorizontal, Sparkles, UploadCloud, ChartNoAxesCombined, Activity, ListFilter, TrendingUp, Wallet, Clock3
} from "lucide-react";
import {IndicatorCatalog, type MacroRule} from "./indicator-catalog";
import {CapitalManagement, DEFAULT_CAPITAL, type CapitalSettings} from "./capital-management";
import {ScheduleConfig,DEFAULT_SCHEDULE,type ScheduleSettings} from "./schedule-config";
import {FundingConfig,DEFAULT_FUNDING,type FundingSettings} from "./funding-config";
import {AdvancedConfig,DEFAULT_ADVANCED,type AdvancedSettings} from "./advanced-config";
import {QualityFilters,DEFAULT_QUALITY,type QualitySettings} from "./quality-filters";
import {WalkForwardConfig,DEFAULT_WALK_FORWARD,type WalkForwardSettings} from "./walk-forward-config";
import {MultiverseConfig,DEFAULT_MULTIVERSE,type MultiverseSettings} from "./multiverse-config";
import {CostsConfig,DEFAULT_COSTS,type CostSettings} from "./costs-config";
import type {MT5Symbol} from "./account-center";
import {DatasetDiagnostics,type AssetDiagnostics} from "./dataset-diagnostics";

export type IndicatorRanges = {
 tech_period_min:number;tech_period_step:number;tech_period_max:number;
 ema_fast_min:number;ema_fast_step:number;ema_fast_max:number;
 ema_slow_min:number;ema_slow_step:number;ema_slow_max:number;
 rsi_period_min:number;rsi_period_step:number;rsi_period_max:number;
 rsi_oversold_min:number;rsi_oversold_step:number;rsi_oversold_max:number;
 breakout_lookback_min:number;breakout_lookback_step:number;breakout_lookback_max:number;
 london_high_sweep_buffer_min:number;london_high_sweep_buffer_step:number;london_high_sweep_buffer_max:number;
 london_low_sweep_buffer_min:number;london_low_sweep_buffer_step:number;london_low_sweep_buffer_max:number;
 asia_high_sweep_buffer_min:number;asia_high_sweep_buffer_step:number;asia_high_sweep_buffer_max:number;
 asia_low_sweep_buffer_min:number;asia_low_sweep_buffer_step:number;asia_low_sweep_buffer_max:number;
 previous_day_high_sweep_buffer_min:number;previous_day_high_sweep_buffer_step:number;previous_day_high_sweep_buffer_max:number;
 previous_day_low_sweep_buffer_min:number;previous_day_low_sweep_buffer_step:number;previous_day_low_sweep_buffer_max:number;
};
export const DEFAULT_INDICATOR_RANGES:IndicatorRanges={
 tech_period_min:10,tech_period_step:5,tech_period_max:30,
 ema_fast_min:5,ema_fast_step:1,ema_fast_max:28,
 ema_slow_min:29,ema_slow_step:1,ema_slow_max:90,
 rsi_period_min:7,rsi_period_step:1,rsi_period_max:25,
 rsi_oversold_min:20,rsi_oversold_step:1,rsi_oversold_max:40,
 breakout_lookback_min:12,breakout_lookback_step:1,breakout_lookback_max:75,
 london_high_sweep_buffer_min:0,london_high_sweep_buffer_step:1,london_high_sweep_buffer_max:10,
 london_low_sweep_buffer_min:0,london_low_sweep_buffer_step:1,london_low_sweep_buffer_max:10,
 asia_high_sweep_buffer_min:0,asia_high_sweep_buffer_step:1,asia_high_sweep_buffer_max:10,
 asia_low_sweep_buffer_min:0,asia_low_sweep_buffer_step:1,asia_low_sweep_buffer_max:10,
 previous_day_high_sweep_buffer_min:0,previous_day_high_sweep_buffer_step:1,previous_day_high_sweep_buffer_max:10,
 previous_day_low_sweep_buffer_min:0,previous_day_low_sweep_buffer_step:1,previous_day_low_sweep_buffer_max:10,
};
export type AlgoConfig = {
 name:string;dataset_id:string;symbol:string;timeframe:string;timeframes:string[];
 start_date:string;end_date:string;initial_deposit:number;mode:"random"|"genetic";optimization_objective:OptimizationObjective;
 modeling:"open"|"ohlc"|"m1"|"ticks";sizing:"compound"|"fixed";
 multi_tf:"individual"|"combined"|"both";generations:number;candidates:number;
 families:string[];indicator_ranges:IndicatorRanges;source_timezone:string;macro_indicators:string[];macro_rules:Record<string,MacroRule>;capital:CapitalSettings;schedule:ScheduleSettings;funding:FundingSettings;advanced_modifiers:AdvancedSettings;quality:QualitySettings;walk_forward:WalkForwardSettings;multiverse:MultiverseSettings;costs:CostSettings;direction:"long"|"short"|"both";risk_pct:number;rr:number;
 atr_multiplier:number;cost_bps:number;is_ratio:number;min_trades:number;
 mc_iterations:number;prop_daily_pct:number;prop_max_pct:number;
};

export type OptimizationObjective =
 |"balanced"|"sharpe"|"sortino"|"calmar"|"net_profit"|"min_drawdown"
 |"profit_factor"|"expectancy"|"win_rate"|"recovery_factor"|"funding_pass_rate";
export const OPTIMIZATION_OPTIONS:{id:OptimizationObjective;name:string;description:string}[]=[
 {id:"balanced",name:"Score Balanceado",description:"Combina Sharpe × 2, penaliza drawdown superior al 30% y bonifica Profit Factor mayor de 1.5. El modo histórico de la plataforma."},
 {id:"sharpe",name:"Mayor Sharpe Ratio",description:"Maximiza el retorno ajustado por volatilidad anualizado con la convención de 252 días de trading."},
 {id:"sortino",name:"Mayor Sortino Ratio",description:"Similar al Sharpe, pero penaliza solamente la volatilidad negativa de los retornos."},
 {id:"calmar",name:"Mayor Calmar",description:"Retorno anualizado dividido por el drawdown máximo. Favorece la consistencia y la recuperación."},
 {id:"net_profit",name:"Mayor PnL Absoluto",description:"Maximiza la ganancia total en dólares estadounidenses (USD), útil para estudiar estrategias agresivas."},
 {id:"min_drawdown",name:"Menor Drawdown",description:"Minimiza el peor descenso de la curva de balance realizado. Útil para evaluar estrategias de fondeo."},
 {id:"profit_factor",name:"Mayor Profit Factor",description:"Maximiza la ganancia bruta dividida entre la pérdida bruta. Favorece estrategias con ratios positivos."},
 {id:"expectancy",name:"Mayor Expectancy",description:"Maximiza la ganancia media en USD por operación cerrada."},
 {id:"win_rate",name:"Mayor Win Rate",description:"Maximiza el porcentaje de operaciones ganadoras, independientemente del tamaño de la ganancia."},
 {id:"recovery_factor",name:"Mayor Recovery Factor",description:"Maximiza el PnL neto dividido por el drawdown máximo absoluto de capital."},
 {id:"funding_pass_rate",name:"Mayor Pass Rate de Fondeo",description:"Maximiza la tasa estimada de aprobación de las fases de Fondeo configuradas, favoreciendo también un menor percentil de días hasta aprobar. Aplica los mínimos de aprobación y plazo indicados; es un proxy de balance realizado, no una garantía ni una prueba de equity flotante."}
];

type Dataset={id:string;filename:string;rows:number;start:string;end:string;timeframe:string;uploaded_at:string};
type Props={
 config:AlgoConfig;datasetList:Dataset[];availableSymbols:{name:string;description:string}[];accountLabel:string;costSnapshot:MT5Symbol|null;accountCurrency:string;importingMT5:boolean;onImportMT5:()=>void;loading:boolean;profile:AssetDiagnostics|null;analyzing:boolean;onAnalyze:()=>void;
 onChange:<K extends keyof AlgoConfig>(key:K,value:AlgoConfig[K])=>void;
 onUpload:()=>void;onExecute:()=>void;onBack:()=>void;
};
const TF=[["1m","M1"],["5m","M5"],["15m","M15"],["30m","M30"],["1h","H1"],["4h","H4"],["1d","D1"]] as const;
const DEPOSITS=[1000,2000,5000,10000,25000,50000,100000];
const HELP:Record<string,string>={
 symbol:"Selecciona el instrumento que corresponde al histórico que vas a investigar.",
 timeframe:"Puedes elegir varios intervalos. Individual prueba cada uno; combinado utiliza el menor para las entradas y el mayor para el contexto.",
 period:"El periodo es inclusivo. Las fechas vacías utilizan todo el histórico disponible.",
 deposit:"El depósito inicial determina el capital base del backtest y el sizing; no conecta una cuenta real.",
 type:"Exploración aleatoria: genera candidatos al azar y los clasifica por el objetivo elegido. Evolución genética: realiza mutación, crossover y selección por el objetivo elegido usando únicamente entrenamiento.",
 modeling:"Solo apertura: evalúa a cada apertura, sin conocer extremos intrabar. OHLC: evalúa apertura/máximo/mínimo/cierre y prioriza SL cuando SL/TP coinciden. M1 y ticks reales requieren datos de mayor resolución y están pendientes de integración.",
 direction:"Solo Long busca compras; Solo Short busca ventas; Long + Short explora ambos sentidos, ampliando el espacio de búsqueda.",
 sizing:"Compuesto arriesga un porcentaje del saldo actual; fijo calcula siempre el riesgo a partir del depósito inicial.",
 multi:"Individual prueba cada timeframe por separado. Combinado filtra con el marco mayor y entra con el menor. Ambos combina los dos métodos.",
 combinations:"Número máximo de evaluaciones del motor. En esta versión el límite operativo es 2,000 por ejecución; los trabajos grandes necesitarán una cola asíncrona.",
 dataset:"Selecciona un CSV de precios históricos importado. El motor trabaja con los datos del archivo y no inventa resoluciones más finas.",
};

function Hint({id,active,toggle}:{id:string;active:string|null;toggle:(v:string|null)=>void}){
 return <span className="tq-inline-hint"><button type="button" className="tq-hint-icon" aria-label={"Ayuda de "+id} aria-expanded={active===id} onClick={()=>toggle(active===id?null:id)}><CircleHelp size={15}/></button>{active===id&&<span className="tq-hint-popover" role="note">{HELP[id]}</span>}</span>;
}
function Row({label,id,children,active,toggle}:{label:string;id:string;children:React.ReactNode;active:string|null;toggle:(v:string|null)=>void}){
 return <div className="tq-one-row"><div className="tq-one-label"><label htmlFor={"tq-"+id}>{label}:</label></div><div className="tq-one-value">{children}</div><Hint id={id} active={active} toggle={toggle}/></div>;
}

export function StrategyConfigurator({config:c,datasetList,availableSymbols,accountLabel,costSnapshot,accountCurrency,importingMT5,onImportMT5,loading,profile,analyzing,onAnalyze,onChange,onUpload,onExecute,onBack}:Props){
 const [help,setHelp]=useState<string|null>(null);
 const [activeTab,setActiveTab]=useState<"config"|"indicators"|"capital"|"schedule"|"funding"|"advanced"|"quality"|"walk_forward"|"multiverse"|"costs">("config");
 const [advanced,setAdvanced]=useState(false);
 const [customDeposit,setCustomDeposit]=useState(false);
 const update=<K extends keyof AlgoConfig>(key:K,value:AlgoConfig[K])=>onChange(key,value);
 const tfs=(c.timeframes?.length?c.timeframes:[c.timeframe]).filter(v=>TF.some(([key])=>key===v));
 const ranges={...DEFAULT_INDICATOR_RANGES,...c.indicator_ranges};
 const cap={...DEFAULT_CAPITAL,...c.capital};
 const usedKeys:("sl_atr"|"tp_atr"|"sl_percent"|"tp_multiplier")[] = cap.exit_mode==="atr_classic"?["sl_atr","tp_atr"]:cap.exit_mode==="percent"?["sl_percent","tp_multiplier"]:["sl_atr","tp_multiplier"];
 const funding={...DEFAULT_FUNDING,...c.funding};
 const modifier={...DEFAULT_ADVANCED,...c.advanced_modifiers};
 const quality={...DEFAULT_QUALITY,...c.quality};
 const walkForward={...DEFAULT_WALK_FORWARD,...c.walk_forward};
 const multiverse={...DEFAULT_MULTIVERSE,...c.multiverse};
 const costs={...DEFAULT_COSTS,...c.costs};
 const invalidCosts=costs.use_in_backtest&&!costs.instruments.some(x=>x.symbol.toUpperCase()===c.symbol.toUpperCase());
 const invalidResearch=quality.min_trades<0||walkForward.enabled&&(walkForward.top_n<1||walkForward.rolling_windows<2)||multiverse.enabled&&(multiverse.top_n<1||multiverse.universes<50);
 const invalidAdvanced=modifier.entry_modes.length===0||(modifier.be_enabled&&modifier.be_offset_pips>0&&modifier.pip_size<=0)||(modifier.dca_enabled&&modifier.dca_levels<2)||(modifier.pyramid_enabled&&modifier.pyramid_levels<2);
 const invalidFunding=funding.enabled&&(funding.phases.length<1||funding.phases.length>3||funding.phases.some(ph=>ph.min_days>ph.max_days||ph.target_pct<=0||ph.max_days<=0)||funding.daily_loss_pct<0||funding.total_loss_pct<=0||funding.simulations<32);
 const invalidCapital=usedKeys.some(k=>{const v=cap[k];return !Number.isFinite(v.from)||!Number.isFinite(v.to)||!Number.isFinite(v.step)||v.step<=0||v.from>v.to;})||c.prop_daily_pct>c.prop_max_pct;
 const multiNeedsTwo=c.multi_tf!=="individual"&&tfs.length<2;
 const invalidPeriod=Boolean(c.start_date&&c.end_date&&c.start_date>c.end_date);
 const selectedSituations=c.families.filter(f=>f.endsWith("_sweep"));
 const sweepTimeframeError=selectedSituations.length>0&&tfs.some(tf=>tf==="4h"||tf==="1d");
 const shortOnly=new Set(["london_high_sweep","asia_high_sweep","previous_day_high_sweep"]);
 const longOnly=new Set(["london_low_sweep","asia_low_sweep","previous_day_low_sweep"]);
 const directionMismatch=c.families.length>0&&!c.families.some(f=>
  !f.endsWith("_sweep")||c.direction==="both"||(c.direction==="short"&&shortOnly.has(f))||(c.direction==="long"&&longOnly.has(f))
 );
 const invalidRanges=(
  ["ema_fast","ema_slow","rsi_period","rsi_oversold","breakout_lookback","london_high_sweep_buffer","london_low_sweep_buffer","asia_high_sweep_buffer","asia_low_sweep_buffer","previous_day_high_sweep_buffer","previous_day_low_sweep_buffer"] as const
 ).some(name=>{
  const min=ranges[(name+"_min") as keyof IndicatorRanges];
  const max=ranges[(name+"_max") as keyof IndicatorRanges];
  const step=ranges[(name+"_step") as keyof IndicatorRanges];
  const lower=name.endsWith("_buffer")?0:name==="ema_fast"||name==="rsi_period"?2:name==="ema_slow"?10:name==="rsi_oversold"?5:5;
  const upper=name.endsWith("_buffer")?30:name==="ema_fast"?100:name==="ema_slow"||name==="breakout_lookback"?250:name==="rsi_period"?60:45;
  return !Number.isInteger(min)||!Number.isInteger(max)||!Number.isInteger(step)||step<1||step>30||min<lower||max>upper||min>max;
 })||ranges.ema_fast_min+8>ranges.ema_slow_max;
 const hasPendingMacro=(c.macro_indicators||[]).length>0;
 const cannotRun=loading||!c.dataset_id||!c.symbol||!c.start_date||!c.end_date||invalidPeriod||multiNeedsTwo||!c.families.length||invalidRanges||sweepTimeframeError||directionMismatch||hasPendingMacro||invalidCapital||invalidFunding||invalidAdvanced||invalidCosts||invalidResearch||c.candidates<10;
 const missing=[
  ...(!c.symbol?["símbolo"]:[]),
  ...(!c.start_date||!c.end_date?["fecha de inicio y fin"]:[]),
  ...(!c.dataset_id?["datos históricos"]:[]),
  ...(multiNeedsTwo?["dos intervalos para Multi-TF"]:[]),
  ...(invalidPeriod?["rango de fechas válido"]:[]),
  ...(!c.families.length?["al menos un indicador"]:[]),
  ...(invalidRanges?["rangos de indicadores válidos"]:[]),
  ...(sweepTimeframeError?["usar solo M1–H1 con barridas de sesión"]:[]),
  ...(directionMismatch?["dirección compatible con las situaciones seleccionadas"]:[]),
  ...(hasPendingMacro?["retirar o dejar pendientes las reglas macro sin fuente de datos"]:[]),
  ...(invalidCapital?["rangos o límites de gestión de capital válidos"]:[]),
  ...(invalidFunding?["configuración de fases y filtros de fondeo válida"]:[]),
  ...(invalidAdvanced?["configuración de modificadores avanzada válida"]:[]),
  ...(invalidCosts?["instrumento con especificaciones de costes configuradas"]:[]),
  ...(invalidResearch?["parámetros de validación estadística válidos"]:[])
 ];
 const chooseTF=(value:string)=>{
  const next=tfs.includes(value)?tfs.filter(t=>t!==value):[...tfs,value];
  if(!next.length)return;
  next.sort((a,b)=>TF.findIndex(([v])=>v===a)-TF.findIndex(([v])=>v===b));
  update("timeframes",next);update("timeframe",next[0]);
 };
 const numberField=(key:keyof AlgoConfig,min:number,max:number,step:number,label:string)=><input aria-label={label} type="number" min={min} max={max} step={step} value={Number(c[key])} onChange={e=>update(key,Math.min(max,Math.max(min,Number(e.target.value)||min)) as never)}/>;

 return <div className="tq-single-config">
  <div className="tq-config-topline"><button onClick={onBack}><ArrowLeft size={15}/> Mis sesiones</button><span>/</span><strong>{c.name}</strong></div>
  <div className="tq-config-titlebar">
   <div><div className="eyebrow">LABORATORIO <span className="eyebrow-line"/> CREADOR DE ALGORITMOS</div><h1>Configuración <Settings2 size={24}/></h1><p>Define todos los parámetros de tu sesión en un solo lugar.</p></div>
   <span className="tq-config-saved"><Check size={14}/> Borrador guardado</span>
  </div>
  <div className="tq-config-tabbar" role="tablist" aria-label="Apartados del creador">
   <button type="button" role="tab" aria-selected={activeTab==="config"} className={activeTab==="config"?"active":""} onClick={()=>setActiveTab("config")}><Settings2 size={17}/> Configuración</button>
   <button type="button" role="tab" aria-selected={activeTab==="indicators"} className={activeTab==="indicators"?"active":""} onClick={()=>setActiveTab("indicators")}><ChartNoAxesCombined size={17}/> Indicadores <span className="tq-tab-pill">{c.families.length}</span></button>
   <button type="button" role="tab" aria-selected={activeTab==="capital"} className={activeTab==="capital"?"active":""} onClick={()=>setActiveTab("capital")}><Wallet size={17}/> Gestión de capital</button>
   <button type="button" role="tab" aria-selected={activeTab==="schedule"} className={activeTab==="schedule"?"active":""} onClick={()=>setActiveTab("schedule")}><Clock3 size={17}/> Horarios</button>
   <button type="button" role="tab" aria-selected={activeTab==="funding"} className={activeTab==="funding"?"active":""} onClick={()=>setActiveTab("funding")}><ShieldCheck size={17}/> Fondeo</button>
   <button type="button" role="tab" aria-selected={activeTab==="advanced"} className={activeTab==="advanced"?"active":""} onClick={()=>setActiveTab("advanced")}><SlidersHorizontal size={17}/> Avanzado</button>
   <button type="button" role="tab" aria-selected={activeTab==="quality"} className={activeTab==="quality"?"active":""} onClick={()=>setActiveTab("quality")}><ShieldCheck size={17}/> Filtro</button>
   <button type="button" role="tab" aria-selected={activeTab==="walk_forward"} className={activeTab==="walk_forward"?"active":""} onClick={()=>setActiveTab("walk_forward")}><ChartNoAxesCombined size={17}/> Walk-Forward</button>
   <button type="button" role="tab" aria-selected={activeTab==="multiverse"} className={activeTab==="multiverse"?"active":""} onClick={()=>setActiveTab("multiverse")}><Dna size={17}/> Multiverso</button>
   <button type="button" role="tab" aria-selected={activeTab==="costs"} className={activeTab==="costs"?"active":""} onClick={()=>setActiveTab("costs")}><Wallet size={17}/> Costes</button>
  </div>
  {activeTab==="config"?<div className="tq-one-panel">
   <div className="tq-one-panel-header"><div className="tq-one-header-icon"><SlidersHorizontal size={19}/></div><div><strong>Parámetros de la sesión</strong><span>Mercado, ejecución y descubrimiento de estrategias</span></div><span className="tq-one-header-tag">RESEARCH MODE</span></div>
   <div className="tq-one-form">
    <Row id="symbol" label="Símbolo" active={help} toggle={setHelp}><select id="tq-symbol" value={c.symbol} onChange={e=>update("symbol",e.target.value)}><option value="">Seleccionar instrumentos...</option>{availableSymbols.map(s=><option value={s.name} key={s.name}>{s.name}{s.description?" · "+s.description:""}</option>)}</select></Row>
    <div className="tq-mt5-import-inline"><div><strong>Histórico oficial del terminal MT5</strong><small>{accountLabel} · {availableSymbols.length} símbolos del bróker · período seleccionado arriba (si no se define: últimos 90 días)</small></div><button type="button" className="btn btn-outline btn-small" disabled={!c.symbol||importingMT5} onClick={onImportMT5}>{importingMT5?"Extrayendo MT5…":"Importar velas desde MT5"}</button></div>
    <Row id="timeframe" label="Intervalo" active={help} toggle={setHelp}><div className="tq-one-intervals">{TF.map(([key,name])=><button key={key} aria-pressed={tfs.includes(key)} type="button" className={tfs.includes(key)?"active":""} onClick={()=>chooseTF(key)}>{tfs.includes(key)&&<span className="tq-interval-dot"/>}{name}</button>)}</div></Row>
    <Row id="period" label="Periodo" active={help} toggle={setHelp}><div className="tq-one-date-range"><input aria-label="Desde" id="tq-period" type="date" value={c.start_date||""} max={c.end_date||undefined} onChange={e=>update("start_date",e.target.value)}/><span>→</span><input aria-label="Hasta" type="date" value={c.end_date||""} min={c.start_date||undefined} onChange={e=>update("end_date",e.target.value)}/></div></Row>
    <Row id="deposit" label="Depósito inicial" active={help} toggle={setHelp}><div className="tq-one-deposit"><select id="tq-deposit" aria-label="Depósito inicial" value={!customDeposit&&DEPOSITS.includes(c.initial_deposit)?String(c.initial_deposit):"custom"} onChange={e=>{if(e.target.value==="custom"){setCustomDeposit(true)}else{setCustomDeposit(false);update("initial_deposit",Number(e.target.value))}}}>{DEPOSITS.map(n=><option value={String(n)} key={n}>{new Intl.NumberFormat("en-US").format(n)}</option>)}<option value="custom">Otro importe...</option></select>{(customDeposit||!DEPOSITS.includes(c.initial_deposit))&&<input type="number" aria-label="Importe personalizado" min={100} max={100000000} step={100} value={c.initial_deposit} onChange={e=>update("initial_deposit",Math.max(100,Math.min(100000000,Number(e.target.value)||100)))}/>}<span>USD</span></div></Row>
    <div className="tq-one-hairline"/>
    <Row id="type" label="Tipo" active={help} toggle={setHelp}><select id="tq-type" value={c.mode} onChange={e=>update("mode",e.target.value as AlgoConfig["mode"])}><option value="random">Exploración aleatoria</option><option value="genetic">Evolución genética</option></select></Row>
    <div className="tq-optimization-heading"><strong>Objetivo de optimización</strong><small>El motor genético maximiza esta métrica y las estrategias encontradas se ordenan por ella. Los resultados fuera de muestra quedan reservados para validación.</small></div>
    <div className="tq-one-row tq-optimization-row">
      <div className="tq-one-label"><label htmlFor="tq-optimization-objective">Optimizar por:</label></div>
      <div className="tq-one-value">
       <div className="tq-optimization-select">
        <select id="tq-optimization-objective" value={c.optimization_objective||"balanced"}
         onChange={e=>{update("optimization_objective",e.target.value as OptimizationObjective);setHelp(null)}}>
         {OPTIMIZATION_OPTIONS.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <button type="button" className="tq-hint-icon" aria-label="Información sobre el objetivo de optimización"
         aria-expanded={help==="optimization"} aria-controls="tq-optimization-description"
         title="¿Cómo se calcula?" onClick={()=>setHelp(help==="optimization"?null:"optimization")}><CircleHelp size={16}/></button>
       </div>
       {help==="optimization"&&<div id="tq-optimization-description" className="tq-optimization-explanation" role="note">
        <span>OBJETIVO SELECCIONADO</span>
        <p>{OPTIMIZATION_OPTIONS.find(o=>o.id===(c.optimization_objective||"balanced"))?.description}</p>
        <small>La selección y el orden usan el conjunto de entrenamiento (IS); los resultados fuera de muestra (OOS) no intervienen en el ranking.</small>
       </div>}
      </div>
    </div>
    {c.mode==="genetic"&&<div className="tq-one-subrow"><span>Generaciones</span><input aria-label="Número de generaciones" type="number" min={2} max={30} value={c.generations} onChange={e=>update("generations",Math.max(2,Math.min(30,Number(e.target.value)||2)))}/><small>Población y generaciones dentro del límite de combinaciones.</small></div>}
    <Row id="modeling" label="Modelado" active={help} toggle={setHelp}><select id="tq-modeling" value={c.modeling==="m1"||c.modeling==="ticks"?"ohlc":c.modeling} onChange={e=>update("modeling",e.target.value as AlgoConfig["modeling"])}><option value="open">Solo precios de apertura</option><option value="ohlc">OHLC del timeframe (SL primero)</option><option value="m1" disabled>OHLC en M1 · Próximamente</option><option value="ticks" disabled>Cada tick (datos reales) · Próximamente</option></select></Row>
    <Row id="direction" label="Dirección" active={help} toggle={setHelp}><select id="tq-direction" value={c.direction} onChange={e=>update("direction",e.target.value as AlgoConfig["direction"])}><option value="long">Solo Long</option><option value="short">Solo Short</option><option value="both">Long + Short</option></select></Row>
    <Row id="sizing" label="Sizing" active={help} toggle={setHelp}><select id="tq-sizing" value={c.sizing} onChange={e=>update("sizing",e.target.value as AlgoConfig["sizing"])}><option value="compound">Compuesto (riesgo % del saldo actual)</option><option value="fixed">Riesgo fijo (% del saldo inicial)</option></select></Row>
    <Row id="multi" label="Multi-TF" active={help} toggle={setHelp}><div className="tq-one-multitf"><select id="tq-multi" value={c.multi_tf} onChange={e=>update("multi_tf",e.target.value as AlgoConfig["multi_tf"])}><option value="individual">Individual (cada TF por separado)</option><option value="combined">Combinado (TF alto filtra, TF bajo entra)</option><option value="both">Ambos (Individual + combinado)</option></select>{c.mode==="genetic"&&c.multi_tf!=="individual"&&<small className="tq-one-warning">El modo genético también evoluciona estrategias multi-timeframe. Las generaciones y la población se ajustan al presupuesto de combinaciones.</small>}{multiNeedsTwo&&<small className="tq-one-error">Selecciona al menos dos intervalos distintos para este modo.</small>}</div></Row>
    <div className="tq-one-hairline"/>
    <Row id="combinations" label="Combinaciones" active={help} toggle={setHelp}><div className="tq-one-combinations"><input aria-label="Cantidad de combinaciones" className="tq-one-combo-number" type="number" min={10} max={2000} step={10} value={c.candidates} onChange={e=>update("candidates",Math.max(10,Math.min(2000,Number(e.target.value)||10)))}/><input aria-label="Ajustar combinaciones" type="range" min={10} max={2000} step={10} value={c.candidates} onChange={e=>update("candidates",Number(e.target.value))}/><span>Máx. 2,000</span></div></Row>
    <div className="tq-one-hairline"/>
    <Row id="dataset" label="Datos históricos" active={help} toggle={setHelp}><div className="tq-one-dataset"><select id="tq-dataset" value={c.dataset_id} onChange={e=>update("dataset_id",e.target.value)}><option value="">Seleccionar archivo CSV...</option>{datasetList.map(d=><option value={d.id} key={d.id}>{d.filename} · {d.rows.toLocaleString("en-US")} velas</option>)}</select><button type="button" onClick={onUpload} title="Importar CSV"><UploadCloud size={17}/><span>Importar</span></button></div></Row>
    <div className="tq-one-advanced">
     <button className="tq-one-expand" type="button" aria-expanded={advanced} onClick={()=>setAdvanced(x=>!x)}><SlidersHorizontal size={17}/><span>Parámetros científicos avanzados</span><ChevronDown size={17} className={advanced?"rotated":""}/></button>
     {advanced&&<div className="tq-one-advanced-grid">
      <p className="tq-research-note">Riesgo, DD, SL/TP y trailing se controlan exclusivamente desde Gestión de capital y Avanzado. Coste por trade se configura solo en Costes.</p>
      <label>Entrenamiento IS (%){numberField("is_ratio",50,85,5,"Porcentaje entrenamiento")}</label>
      <label>Trades mínimos OOS{numberField("min_trades",1,100,1,"Trades mínimos")}</label>
      <label>Monte Carlo<select value={c.mc_iterations} onChange={e=>update("mc_iterations",Number(e.target.value))}><option value={100}>100 simulaciones</option><option value={500}>500 simulaciones</option><option value={1000}>1,000 simulaciones</option></select></label>
     </div>}
    </div>
   </div>
   <div className="tq-one-footer">
    <div><div className="tq-one-ready"><ShieldCheck size={16}/><strong>{missing.length?"Configuración pendiente":"Configuración completa"}</strong></div><p>{missing.length?"Falta: "+missing.join(", "):"Revisa los parámetros antes de ejecutar."}</p></div>
    <button className="btn btn-primary" disabled={cannotRun} onClick={onExecute}>{loading?<LoaderCircle className="spin" size={17}/>:<Play size={16}/>} {loading?"Ejecutando...":"Iniciar exploración"} <ArrowRight size={16}/></button>
   </div>
  </div>:activeTab==="indicators"?<div className="tq-one-panel tq-indicator-panel"><div className="tq-one-panel-header"><div className="tq-one-header-icon"><ChartNoAxesCombined size={19}/></div><div><strong>Indicadores y situaciones de mercado</strong><span>Señales técnicas, patrones de liquidez y parámetros Desde / Pasos / Hasta</span></div><span className="tq-one-header-tag">CATÁLOGO</span></div><IndicatorCatalog families={c.families} ranges={ranges} sourceTimezone={c.source_timezone||"UTC"} macroIndicators={c.macro_indicators||[]} macroRules={c.macro_rules||{}} onFamilies={v=>update("families",v)} onRanges={v=>update("indicator_ranges",v)} onTimezone={v=>update("source_timezone",v)} onMacroIndicators={v=>update("macro_indicators",v)} onMacroRules={v=>update("macro_rules",v)}/><footer className="tq-one-footer"><div><div className="tq-one-ready"><Check size={15}/><strong>{c.families.length} elementos seleccionados</strong></div><p>Todos los cambios se guardan en esta sesión.</p></div><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer></div>:activeTab==="capital"?<div className="tq-one-panel tq-capital-panel"><CapitalManagement value={cap} onChange={v=>update("capital",v)} deposit={c.initial_deposit} riskPct={c.risk_pct} sizing={c.sizing} dailyDD={c.prop_daily_pct} totalDD={c.prop_max_pct} onRisk={v=>update("risk_pct",v)} onSizing={v=>update("sizing",v)} onDailyDD={v=>update("prop_daily_pct",v)} onTotalDD={v=>update("prop_max_pct",v)}/><footer className="tq-one-footer"><span><Check size={15}/> Parámetros de riesgo guardados por sesión</span><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer></div>:activeTab==="schedule"?<div className="tq-one-panel tq-hours-panel"><ScheduleConfig value={{...DEFAULT_SCHEDULE,...c.schedule}} onChange={v=>update("schedule",v)} sourceTimezone={c.source_timezone||"UTC"} onTimezone={tz=>update("source_timezone",tz)}/><footer className="tq-one-footer"><span><Check size={15}/> Sesiones y restricciones guardadas</span><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer></div>:activeTab==="funding"?<div className="tq-one-panel tq-fund-panel"><FundingConfig value={funding} onChange={v=>update("funding",v)} optimizationObjective={c.optimization_objective||"balanced"} initialDeposit={c.initial_deposit}/><footer className="tq-one-footer"><span><Check size={15}/> Reglas de fondeo guardadas en la sesión</span><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer></div>:activeTab==="advanced"?<div className="tq-one-panel tq-adv-panel"><AdvancedConfig value={modifier} onChange={x=>update("advanced_modifiers",x)} currentCapitalBE={cap.breakeven_enabled} currentCapitalTrailing={cap.trailing_enabled}/><footer className="tq-one-footer"><span><Check size={15}/> Modificadores avanzados guardados por sesión</span><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer></div>:activeTab==="quality"?<div className="tq-one-panel"><QualityFilters value={quality} onChange={x=>update("quality",x)}/></div>:activeTab==="walk_forward"?<div className="tq-one-panel"><WalkForwardConfig value={walkForward} onChange={x=>update("walk_forward",x)} periodLabel={c.start_date&&c.end_date?c.start_date+" — "+c.end_date:undefined}/></div>:activeTab==="multiverse"?<div className="tq-one-panel"><MultiverseConfig value={multiverse} onChange={x=>update("multiverse",x)}/></div>:<div className="tq-one-panel"><CostsConfig value={costs} onChange={x=>update("costs",x)} onFallbackChange={x=>update("cost_bps",x)} symbol={c.symbol} snapshot={costSnapshot} accountCurrency={accountCurrency} fallbackBps={c.cost_bps}/></div>}

  {activeTab==="config"&&<DatasetDiagnostics value={profile} loading={analyzing} onAnalyze={onAnalyze} datasetLoaded={Boolean(c.dataset_id)} pipSize={costs.instruments.find(x=>x.symbol.toUpperCase()===c.symbol.toUpperCase())?.pip_size}/>}
  <div className="tq-one-footnote"><Sparkles size={14}/> Investigación cuantitativa · Resultados OOS no garantizan rendimiento futuro · Modelado M1/tick pendiente de integración.</div>
 </div>;
}
