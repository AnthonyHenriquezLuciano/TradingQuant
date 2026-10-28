"use client";

import {useState} from "react";
import {
 ArrowLeft, ArrowRight, Check, ChevronDown, CircleHelp, Database,
 Dna, FlaskConical, LoaderCircle, Play, Settings2, ShieldCheck,
 SlidersHorizontal, Sparkles, UploadCloud, ChartNoAxesCombined, Activity, ListFilter, TrendingUp
} from "lucide-react";

export type IndicatorRanges = {
 ema_fast_min:number;ema_fast_max:number;ema_slow_min:number;ema_slow_max:number;
 rsi_period_min:number;rsi_period_max:number;rsi_oversold_min:number;rsi_oversold_max:number;
 breakout_lookback_min:number;breakout_lookback_max:number;
};
export const DEFAULT_INDICATOR_RANGES:IndicatorRanges={
 ema_fast_min:5,ema_fast_max:28,ema_slow_min:29,ema_slow_max:90,
 rsi_period_min:7,rsi_period_max:25,rsi_oversold_min:20,rsi_oversold_max:40,
 breakout_lookback_min:12,breakout_lookback_max:75,
};
export type AlgoConfig = {
 name:string;dataset_id:string;symbol:string;timeframe:string;timeframes:string[];
 start_date:string;end_date:string;initial_deposit:number;mode:"random"|"genetic";
 modeling:"open"|"ohlc"|"m1"|"ticks";sizing:"compound"|"fixed";
 multi_tf:"individual"|"combined"|"both";generations:number;candidates:number;
 families:string[];indicator_ranges:IndicatorRanges;direction:"long"|"short"|"both";risk_pct:number;rr:number;
 atr_multiplier:number;cost_bps:number;is_ratio:number;min_trades:number;
 mc_iterations:number;prop_daily_pct:number;prop_max_pct:number;
};
type Dataset={id:string;filename:string;rows:number;start:string;end:string;timeframe:string;uploaded_at:string};
type Props={
 config:AlgoConfig;datasetList:Dataset[];loading:boolean;
 onChange:<K extends keyof AlgoConfig>(key:K,value:AlgoConfig[K])=>void;
 onUpload:()=>void;onExecute:()=>void;onBack:()=>void;
};
const TF=[["1m","M1"],["5m","M5"],["15m","M15"],["30m","M30"],["1h","H1"],["4h","H4"],["1d","D1"]] as const;
const SYMBOLS=["XAUUSD","NAS100","US30","SPX500","EURUSD","GBPUSD","USDJPY","USDCAD","AUDUSD","NZDUSD","BTCUSD","ETHUSD","OTRO"];
const DEPOSITS=[1000,2000,5000,10000,25000,50000,100000];
const HELP:Record<string,string>={
 symbol:"Selecciona el instrumento que corresponde al histórico que vas a investigar.",
 timeframe:"Puedes elegir varios intervalos. Individual prueba cada uno; combinado utiliza el menor para las entradas y el mayor para el contexto.",
 period:"El periodo es inclusivo. Las fechas vacías utilizan todo el histórico disponible.",
 deposit:"El depósito inicial determina el capital base del backtest y el sizing; no conecta una cuenta real.",
 type:"Exploración aleatoria: muestrea indicadores y parámetros al azar, realiza backtesting y filtra los resultados sobre entrenamiento. Evolución genética: evoluciona una población con crossover, mutación y selección mediante Sharpe de entrenamiento.",
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

export function StrategyConfigurator({config:c,datasetList,loading,onChange,onUpload,onExecute,onBack}:Props){
 const [help,setHelp]=useState<string|null>(null);
 const [activeTab,setActiveTab]=useState<"config"|"indicators">("config");
 const [advanced,setAdvanced]=useState(false);
 const [customDeposit,setCustomDeposit]=useState(false);
 const update=<K extends keyof AlgoConfig>(key:K,value:AlgoConfig[K])=>onChange(key,value);
 const tfs=(c.timeframes?.length?c.timeframes:[c.timeframe]).filter(v=>TF.some(([key])=>key===v));
 const ranges={...DEFAULT_INDICATOR_RANGES,...c.indicator_ranges};
 const multiNeedsTwo=c.multi_tf!=="individual"&&tfs.length<2;
 const invalidPeriod=Boolean(c.start_date&&c.end_date&&c.start_date>c.end_date);
 const invalidRanges=Object.keys(DEFAULT_INDICATOR_RANGES).some(k=>!Number.isInteger(ranges[k as keyof IndicatorRanges])) ||
    ranges.ema_fast_min>ranges.ema_fast_max ||
    ranges.ema_slow_min>ranges.ema_slow_max ||
    ranges.rsi_period_min>ranges.rsi_period_max ||
    ranges.rsi_oversold_min>ranges.rsi_oversold_max ||
    ranges.breakout_lookback_min>ranges.breakout_lookback_max ||
    ranges.ema_slow_max<ranges.ema_fast_min+8;
 const cannotRun=loading||!c.dataset_id||!c.symbol||!c.start_date||!c.end_date||invalidPeriod||multiNeedsTwo||!c.families.length||invalidRanges||c.candidates<10;
 const missing=[
  ...(!c.symbol?["símbolo"]:[]),
  ...(!c.start_date||!c.end_date?["fecha de inicio y fin"]:[]),
  ...(!c.dataset_id?["datos históricos"]:[]),
  ...(multiNeedsTwo?["dos intervalos para Multi-TF"]:[]),
  ...(invalidPeriod?["rango de fechas válido"]:[]),
  ...(!c.families.length?["al menos un indicador"]:[]),
  ...(invalidRanges?["rangos de indicadores válidos"]:[])
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
  </div>
  {activeTab==="config"?<div className="tq-one-panel">
   <div className="tq-one-panel-header"><div className="tq-one-header-icon"><SlidersHorizontal size={19}/></div><div><strong>Parámetros de la sesión</strong><span>Mercado, ejecución y descubrimiento de estrategias</span></div><span className="tq-one-header-tag">RESEARCH MODE</span></div>
   <div className="tq-one-form">
    <Row id="symbol" label="Símbolo" active={help} toggle={setHelp}><select id="tq-symbol" value={c.symbol} onChange={e=>update("symbol",e.target.value)}><option value="">Seleccionar instrumentos...</option>{SYMBOLS.map(s=><option value={s} key={s}>{s}</option>)}</select></Row>
    <Row id="timeframe" label="Intervalo" active={help} toggle={setHelp}><div className="tq-one-intervals">{TF.map(([key,name])=><button key={key} aria-pressed={tfs.includes(key)} type="button" className={tfs.includes(key)?"active":""} onClick={()=>chooseTF(key)}>{tfs.includes(key)&&<span className="tq-interval-dot"/>}{name}</button>)}</div></Row>
    <Row id="period" label="Periodo" active={help} toggle={setHelp}><div className="tq-one-date-range"><input aria-label="Desde" id="tq-period" type="date" value={c.start_date||""} max={c.end_date||undefined} onChange={e=>update("start_date",e.target.value)}/><span>→</span><input aria-label="Hasta" type="date" value={c.end_date||""} min={c.start_date||undefined} onChange={e=>update("end_date",e.target.value)}/></div></Row>
    <Row id="deposit" label="Depósito inicial" active={help} toggle={setHelp}><div className="tq-one-deposit"><select id="tq-deposit" aria-label="Depósito inicial" value={!customDeposit&&DEPOSITS.includes(c.initial_deposit)?String(c.initial_deposit):"custom"} onChange={e=>{if(e.target.value==="custom"){setCustomDeposit(true)}else{setCustomDeposit(false);update("initial_deposit",Number(e.target.value))}}}>{DEPOSITS.map(n=><option value={String(n)} key={n}>{new Intl.NumberFormat("en-US").format(n)}</option>)}<option value="custom">Otro importe...</option></select>{(customDeposit||!DEPOSITS.includes(c.initial_deposit))&&<input type="number" aria-label="Importe personalizado" min={100} max={100000000} step={100} value={c.initial_deposit} onChange={e=>update("initial_deposit",Math.max(100,Math.min(100000000,Number(e.target.value)||100)))}/>}<span>USD</span></div></Row>
    <div className="tq-one-hairline"/>
    <Row id="type" label="Tipo" active={help} toggle={setHelp}><select id="tq-type" value={c.mode} onChange={e=>update("mode",e.target.value as AlgoConfig["mode"])}><option value="random">Exploración aleatoria</option><option value="genetic">Evolución genética</option></select></Row>
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
      <label>Riesgo por trade (%){numberField("risk_pct",.05,2,.05,"Riesgo por trade")}</label>
      <label>Ratio TP / SL{numberField("rr",.2,5,.1,"Ratio TP/SL")}</label>
      <label>Stop ATR (×){numberField("atr_multiplier",.5,6,.1,"Stop ATR")}</label>
      <label>Coste round-trip (bps){numberField("cost_bps",0,100,.5,"Coste round trip")}</label>
      <label>Entrenamiento IS (%){numberField("is_ratio",50,85,5,"Porcentaje entrenamiento")}</label>
      <label>Trades mínimos OOS{numberField("min_trades",1,100,1,"Trades mínimos")}</label>
      <label>Monte Carlo<select value={c.mc_iterations} onChange={e=>update("mc_iterations",Number(e.target.value))}><option value={100}>100 simulaciones</option><option value={500}>500 simulaciones</option><option value={1000}>1,000 simulaciones</option></select></label>
      <label>Drawdown diario (%) {numberField("prop_daily_pct",.5,10,.5,"Drawdown diario")}</label>
      <label>Drawdown total (%) {numberField("prop_max_pct",1,20,.5,"Drawdown total")}</label>
     </div>}
    </div>
   </div>
   <div className="tq-one-footer">
    <div><div className="tq-one-ready"><ShieldCheck size={16}/><strong>{missing.length?"Configuración pendiente":"Configuración completa"}</strong></div><p>{missing.length?"Falta: "+missing.join(", "):"Revisa los parámetros antes de ejecutar."}</p></div>
    <button className="btn btn-primary" disabled={cannotRun} onClick={onExecute}>{loading?<LoaderCircle className="spin" size={17}/>:<Play size={16}/>} {loading?"Ejecutando...":"Iniciar exploración"} <ArrowRight size={16}/></button>
   </div>
  </div>:<div className="tq-one-panel tq-indicator-panel">
    <div className="tq-one-panel-header"><div className="tq-one-header-icon"><ChartNoAxesCombined size={19}/></div><div><strong>Indicadores y parámetros</strong><span>Define qué familias se exploran y sus rangos de búsqueda</span></div><span className="tq-one-header-tag">RANGOS DEL MOTOR</span></div>
    <div className="tq-indicator-body">
      <div className="tq-indicator-intro"><ListFilter size={18}/><span>Selecciona uno o varios grupos. El motor probará parámetros dentro de los mínimos y máximos indicados, sin utilizar el tramo fuera de muestra para elegirlos.</span></div>
      {([
       {id:"ema_cross",title:"Medias móviles exponenciales (EMA)",desc:"Cruces entre EMA rápida y lenta para detectar cambios de tendencia.",icon:TrendingUp,inputs:[["ema_fast_min","EMA rápida · desde",2,100],["ema_fast_max","EMA rápida · hasta",2,100],["ema_slow_min","EMA lenta · desde",10,250],["ema_slow_max","EMA lenta · hasta",10,250]]},
       {id:"rsi_reversion",title:"Índice de Fuerza Relativa (RSI)",desc:"Reversión tras recuperar o perder umbrales de sobrecompra y sobreventa.",icon:Activity,inputs:[["rsi_period_min","Periodo RSI · desde",2,60],["rsi_period_max","Periodo RSI · hasta",2,60],["rsi_oversold_min","Sobreventa · desde",5,45],["rsi_oversold_max","Sobreventa · hasta",5,45]]},
       {id:"breakout",title:"Ruptura de canal (Breakout)",desc:"Entradas cuando el cierre supera los extremos de las velas anteriores.",icon:ChartNoAxesCombined,inputs:[["breakout_lookback_min","Velas de canal · desde",5,250],["breakout_lookback_max","Velas de canal · hasta",5,250]]}
      ] as {id:string;title:string;desc:string;icon:typeof Activity;inputs:(string|number)[][]}[]).map(group=>{
        const enabled=c.families.includes(group.id);
        const Icon=group.icon;
        return <section className={"tq-indicator-card "+(enabled?"enabled":"")} key={group.id}>
          <div className="tq-indicator-card-top"><button type="button" className="tq-indicator-toggle" role="switch" aria-checked={enabled} aria-label={"Activar "+group.title}
             onClick={()=>{const next=enabled?c.families.filter(f=>f!==group.id):[...c.families,group.id];update("families",next)}}>
             <span className={"tq-switch "+(enabled?"on":"")}><span/></span>
             <span className="tq-indicator-symbol"><Icon size={19}/></span>
             <span className="tq-indicator-text"><strong>{group.title}</strong><small>{group.desc}</small></span>
          </button><span className={"tq-indicator-state "+(enabled?"on":"")}>{enabled?"Incluido":"Excluido"}</span></div>
          {enabled&&<div className="tq-indicator-inputs">{group.inputs.map(([key,label,min,max])=><label key={key} className="tq-indicator-field"><span>{label}</span><input type="number" min={min} max={max} step={1}
           value={ranges[key as keyof IndicatorRanges]} onChange={e=>{const v=Math.max(Number(min),Math.min(Number(max),Number(e.target.value)||Number(min)));update("indicator_ranges",{...ranges,[key]:v})}}/></label>)}</div>}
        </section>
      })}
      {invalidRanges&&<div className="tq-one-error tq-indicator-error">Revisa los rangos: los mínimos no pueden ser superiores a los máximos y debe existir una pareja EMA rápida/lenta válida.</div>}
      {!c.families.length&&<div className="tq-one-error tq-indicator-error">Activa al menos un indicador para poder iniciar la exploración.</div>}
      <div className="tq-indicator-engine-note"><ShieldCheck size={16}/> Estos rangos afectan directamente la exploración aleatoria y genética. Las estrategias EMA, RSI y Breakout están disponibles; los demás indicadores se incorporarán conforme se implemente su lógica científica.</div>
    </div>
    <footer className="tq-one-footer"><div><div className="tq-one-ready"><Check size={15}/><strong>{c.families.length} familias seleccionadas</strong></div><p>Configuración guardada por sesión en este navegador.</p></div><button className="btn btn-primary" onClick={()=>setActiveTab("config")}>Volver a Configuración <ArrowRight size={16}/></button></footer>
  </div>}
  <div className="tq-one-footnote"><Sparkles size={14}/> Investigación cuantitativa · Resultados OOS no garantizan rendimiento futuro · Modelado M1/tick pendiente de integración.</div>
 </div>;
}
