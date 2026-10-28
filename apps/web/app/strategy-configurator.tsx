"use client";
import {useState} from "react";
import {ArrowLeft,ArrowRight,Activity,BarChart3,Check,ChevronDown,Clock3,Database,Dna,FlaskConical,GitMerge,Layers3,LoaderCircle,LockKeyhole,Play,Settings2,ShieldCheck,Shuffle,Sparkles,TrendingDown,TrendingUp,Wallet,Zap,SlidersHorizontal} from "lucide-react";
import type {LucideIcon} from "lucide-react";
export type AlgoConfig={name:string;dataset_id:string;symbol:string;timeframe:string;timeframes:string[];start_date:string;end_date:string;initial_deposit:number;mode:"random"|"genetic";modeling:"open"|"ohlc"|"m1"|"ticks";sizing:"compound"|"fixed";multi_tf:"individual"|"combined"|"both";generations:number;candidates:number;families:string[];direction:"long"|"short"|"both";risk_pct:number;rr:number;atr_multiplier:number;cost_bps:number;is_ratio:number;min_trades:number;mc_iterations:number;prop_daily_pct:number;prop_max_pct:number};
type Dataset={id:string;filename:string;rows:number;start:string;end:string;timeframe:string;uploaded_at:string};
type Props={config:AlgoConfig;datasetList:Dataset[];loading:boolean;onChange:<K extends keyof AlgoConfig>(key:K,value:AlgoConfig[K])=>void;onUpload:()=>void;onExecute:()=>void;onBack:()=>void};
type Choice={value:string;title:string;desc:string;icon:LucideIcon;disabled?:boolean;tag?:string};
const TF=[["1m","M1"],["5m","M5"],["15m","M15"],["30m","M30"],["1h","H1"],["4h","H4"],["1d","D1"]];
const TABS:[string,string,LucideIcon][]=[["Configuración","Mercado y periodo",Settings2],["Modelado","Precisión de ejecución",Activity],["Dirección","Sentido de las órdenes",TrendingUp],["Sizing","Capital y riesgo",Wallet],["Multi-TF","Contexto temporal",Layers3],["Combinaciones","Motor de búsqueda",Shuffle]];
const SYMBOLS=["XAUUSD","NAS100","US30","SPX500","EURUSD","GBPUSD","USDJPY","USDCAD","AUDUSD","NZDUSD","BTCUSD","ETHUSD","OTRO"];
function ChoiceGrid({value,options,onChange}:{value:string;options:Choice[];onChange:(x:string)=>void}){return <div className="tq-choices">{options.map(o=><button type="button" key={o.value} disabled={o.disabled} className={"tq-choice "+(value===o.value?"selected ":"")+(o.disabled?"disabled":"")} onClick={()=>onChange(o.value)}><span className="tq-choice-icon"><o.icon size={20}/></span><span className="tq-choice-info"><strong>{o.title}</strong><small>{o.desc}</small>{o.tag&&<em>{o.tag}</em>}</span><span className="tq-choice-check">{o.disabled?<LockKeyhole size={15}/>:value===o.value?<Check size={16}/>:null}</span></button>)}</div>}
function Field({title,hint,children}:{title:string;hint?:string;children:React.ReactNode}){return <label className="tq-setting-field"><strong>{title}</strong>{children}{hint&&<small>{hint}</small>}</label>}
function Subhead({number,title,desc}:{number:string;title:string;desc:string}){return <div className="tq-setting-subhead"><span>{number}</span><div><strong>{title}</strong><small>{desc}</small></div></div>}
export function StrategyConfigurator({config:c,datasetList,loading,onChange,onUpload,onExecute,onBack}:Props){
 const [tab,setTab]=useState(0);const [advanced,setAdvanced]=useState(false);
 const update=<K extends keyof AlgoConfig>(key:K,v:AlgoConfig[K])=>onChange(key,v);
 const selectedTfs=(c.timeframes?.length?c.timeframes:[c.timeframe]).filter(x=>TF.some(y=>y[0]===x));
 const invalidMulti=c.multi_tf!=="individual"&&selectedTfs.length<2;
 const invalidPeriod=Boolean(c.start_date&&c.end_date&&c.start_date>c.end_date);
 const canRun=Boolean(c.dataset_id&&c.families.length&&selectedTfs.length&&c.candidates>0&&!invalidPeriod&&!invalidMulti&&!loading);
 const money=(v:number)=>new Intl.NumberFormat("es-DO",{maximumFractionDigits:2}).format(v);
 const selectTF=(x:string)=>{let next=selectedTfs.includes(x)?selectedTfs.filter(v=>v!==x):[...selectedTfs,x];if(!next.length)return;next.sort((a,b)=>TF.findIndex(v=>v[0]===a)-TF.findIndex(v=>v[0]===b));update("timeframes",next);update("timeframe",next[0])};
 const numberField=(label:string,key:keyof AlgoConfig,min:number,max:number,step:number,help?:string)=><Field title={label} hint={help}><input type="number" min={min} max={max} step={step} value={Number(c[key])} onChange={e=>update(key,Math.min(max,Math.max(min,Number(e.target.value)||min)) as never)}/></Field>;
 return <div className="tq-studio">
   <div className="tq-studio-back"><button onClick={onBack}><ArrowLeft size={16}/> Mis sesiones</button><span>/</span><strong>{c.name}</strong></div>
   <div className="tq-studio-top"><div><div className="eyebrow">LABORATORIO <span className="eyebrow-line"/> DISEÑO DE ESTRATEGIAS</div><h1>Configurar algoritmo <Sparkles size={21}/></h1><p>Controla cada variable antes de comenzar la búsqueda cuantitativa.</p></div><span className="tq-studio-saved"><Check size={14}/> GUARDADO LOCAL</span></div>
   <div className="tq-config-tabs" role="tablist" aria-label="Apartados de configuración">{TABS.map(([title,sub,Icon],i)=><button key={title} role="tab" aria-selected={tab===i} className={i===tab?"active":""} onClick={()=>setTab(i)}><span className="tq-config-tab-icon"><Icon size={19}/></span><span><strong>{title}</strong><small>{sub}</small></span><em>{String(i+1).padStart(2,"0")}</em></button>)}</div>
   <div className="tq-config-layout"><section className="tq-config-main">
    <div className="tq-config-head"><div><span className="eyebrow">APARTADO {String(tab+1).padStart(2,"0")} / 06</span><h2>{TABS[tab][0]}</h2><p>{TABS[tab][1]}</p></div><div className="tq-config-head-icon">{(()=>{const I=TABS[tab][2];return <I size={24}/>})()}</div></div>
    <div className="tq-config-body">
      {tab===0&&<>
        <Subhead number="01" title="Mercado" desc="Selecciona el símbolo y el archivo histórico a investigar."/>
        <div className="tq-settings-grid"><Field title="Símbolo"><select value={c.symbol} onChange={e=>update("symbol",e.target.value)}>{SYMBOLS.map(x=><option key={x} value={x}>{x}</option>)}</select></Field><Field title="Datos históricos" hint="El CSV debe corresponder al símbolo elegido."><select value={c.dataset_id} onChange={e=>update("dataset_id",e.target.value)}><option value="">Seleccionar CSV…</option>{datasetList.map(d=><option key={d.id} value={d.id}>{d.filename} · {money(d.rows)} velas</option>)}</select></Field></div>
        <button className="tq-data-link" onClick={onUpload}><Database size={17}/><span>Gestionar datos históricos</span><ArrowRight size={16}/></button>
        <div className="tq-section-rule"/>
        <Subhead number="02" title="Intervalo" desc="Selecciona uno o varios timeframes para explorar."/>
        <div className="tq-timeframe-selector">{TF.map(([x,label])=><button key={x} className={selectedTfs.includes(x)?"active":""} onClick={()=>selectTF(x)} aria-pressed={selectedTfs.includes(x)}>{selectedTfs.includes(x)&&<Check size={13}/>} {label}</button>)}</div>
        <div className="tq-section-rule"/>
        <Subhead number="03" title="Periodo" desc="Fechas inclusivas. Si las dejas vacías, se utiliza todo el histórico."/>
        <div className="tq-settings-grid"><Field title="Desde"><input type="date" value={c.start_date||""} onChange={e=>update("start_date",e.target.value)}/></Field><Field title="Hasta"><input type="date" value={c.end_date||""} onChange={e=>update("end_date",e.target.value)}/></Field></div>
        {invalidPeriod&&<div className="tq-config-warning">La fecha de inicio debe ser anterior a la fecha final.</div>}
        <div className="tq-section-rule"/>
        <Subhead number="04" title="Depósito inicial" desc="Capital de partida para calcular exposición y resultados."/>
        <div className="tq-settings-grid">{numberField("Depósito inicial (USD)","initial_deposit",100,100000000,100)}</div>
        <div className="tq-section-rule"/>
        <Subhead number="05" title="Tipo de exploración" desc="Selecciona cómo se generan y evolucionan los candidatos."/>
        <ChoiceGrid value={c.mode} onChange={x=>update("mode",x as AlgoConfig["mode"])} options={[{value:"random",title:"Exploración aleatoria",desc:"Genera combinaciones aleatorias de indicadores y parámetros, las backtestea y filtra las mejores según las métricas de entrenamiento.",icon:Shuffle,tag:"ESTOCÁSTICO"},{value:"genetic",title:"Evolución genética",desc:"Evoluciona una población mediante crossover, mutación y selección por Sharpe calculado exclusivamente en entrenamiento.",icon:Dna,tag:"EVOLUTIVO"}]}/>
        {c.mode==="genetic"&&<div className="tq-genetic-input">{numberField("Número de generaciones","generations",2,30,1,"El presupuesto de combinaciones se reparte entre generaciones.")}</div>}
      </>}
      {tab===1&&<>
        <Subhead number="01" title="Precisión de modelado" desc="Cuanta más resolución del precio, mayor fidelidad y coste computacional."/>
        <ChoiceGrid value={c.modeling} onChange={x=>update("modeling",x as AlgoConfig["modeling"])} options={[{value:"open",title:"Solo precios de apertura",desc:"Evalúa al abrir cada vela. Más rápido; indicado para estrategias que deciden al cierre de barra. No observa extremos intrabar.",icon:Zap,tag:"RÁPIDO · DISPONIBLE"},{value:"ohlc",title:"OHLC del timeframe",desc:"Usa Open/High/Low/Close. Cuando SL y TP se tocan en la misma vela, se aplica el peor caso (SL primero).",icon:BarChart3,tag:"EQUILIBRADO · DISPONIBLE"},{value:"m1",title:"OHLC en M1",desc:"Requiere velas de un minuto para reconstruir la secuencia de SL/TP dentro de cada barra. Integración M1 pendiente.",icon:Clock3,disabled:true,tag:"REQUIERE DATOS M1"},{value:"ticks",title:"Cada tick (datos reales)",desc:"Requiere ticks auténticos del servidor para verificar la secuencia de ejecución. El volumen transferido depende del histórico.",icon:Activity,disabled:true,tag:"REQUIERE FUENTE DE TICKS"}]}/>
        <div className="tq-config-note"><ShieldCheck size={17}/> M1 y tick están deshabilitados hasta integrar los datos y el reproductor de ejecución. No se sustituyen silenciosamente por OHLC.</div>
      </>}
      {tab===2&&<>
        <Subhead number="01" title="Dirección" desc="Decide si el algoritmo puede abrir compras, ventas o ambas."/>
        <ChoiceGrid value={c.direction} onChange={x=>update("direction",x as AlgoConfig["direction"])} options={[{value:"long",title:"Solo Long",desc:"Solo genera entradas compradoras, buscando vender a mayor precio.",icon:TrendingUp},{value:"short",title:"Solo Short",desc:"Solo genera entradas vendedoras, buscando recomprar a menor precio.",icon:TrendingDown},{value:"both",title:"Long + Short",desc:"Permite ambas direcciones y amplía el espacio de señales exploradas.",icon:GitMerge}]}/>
      </>}
      {tab===3&&<>
        <Subhead number="01" title="Sizing" desc="Determina si el porcentaje de riesgo se calcula sobre el capital actual o el inicial."/>
        <ChoiceGrid value={c.sizing} onChange={x=>update("sizing",x as AlgoConfig["sizing"])} options={[{value:"compound",title:"Compuesto (riesgo % del saldo actual)",desc:"Cada trade arriesga un porcentaje del balance actual. La capitalización puede inflar el PnL del backtest en tendencias fuertes.",icon:TrendingUp,tag:"RIESGO DINÁMICO"},{value:"fixed",title:"Riesgo fijo (% del saldo inicial)",desc:"Cada trade arriesga un porcentaje del depósito inicial, con crecimiento lineal en términos de R y sin interés compuesto.",icon:Wallet,tag:"BASE FIJA"}]}/>
        <div className="tq-config-values"><div><small>Depósito inicial</small><strong>USD {money(c.initial_deposit)}</strong></div><div><small>Riesgo por operación</small><strong>{c.risk_pct}%</strong></div><div><small>Riesgo monetario base</small><strong>USD {money(c.initial_deposit*c.risk_pct/100)}</strong></div></div>
      </>}
      {tab===4&&<>
        <Subhead number="01" title="Multi-TF" desc="Usa cada marco de forma individual o combina contexto HTF con entradas LTF."/>
        <ChoiceGrid value={c.multi_tf} onChange={x=>update("multi_tf",x as AlgoConfig["multi_tf"])} options={[{value:"individual",title:"Individual (cada TF por separado)",desc:"Analiza cada timeframe seleccionado de forma independiente.",icon:Layers3,tag:"ESTÁNDAR"},{value:"combined",title:"Combinado (TF alto filtra, TF bajo entra)",desc:"El timeframe alto aporta un filtro de tendencia calculado con velas completas; el más bajo produce la entrada.",icon:GitMerge,tag:"FILTRO HTF → LTF"},{value:"both",title:"Ambos (Individual + combinado)",desc:"Ejecuta las investigaciones individuales y también el par mayor/menor timeframe.",icon:Shuffle,tag:"DOS ENFOQUES"}]}/>
        {invalidMulti&&<div className="tq-config-warning">Para usar combinado o ambos, selecciona al menos dos intervalos diferentes en Configuración.</div>}
        {c.mode==="genetic"&&<div className="tq-config-note"><Dna size={17}/> La búsqueda genética evoluciona también las combinaciones multi-timeframe y comparte el presupuesto total de evaluaciones.</div>}
      </>}
      {tab===5&&<>
        <Subhead number="01" title="Combinaciones" desc="Presupuesto máximo de candidatos que probará el motor durante la sesión."/>
        <div className="tq-combo-panel"><div><span>COMBINACIONES A EVALUAR</span><strong>{money(c.candidates)}</strong><small>Máximo 2,000 por ejecución de esta versión</small></div><div><input aria-label="Número de combinaciones" type="range" min={10} max={2000} step={10} value={c.candidates} onChange={e=>update("candidates",Number(e.target.value))}/><div className="tq-combo-presets">{[100,500,1000,2000].map(v=><button key={v} className={c.candidates===v?"active":""} onClick={()=>update("candidates",v)}>{money(v)}</button>)}</div><Field title="Cantidad personalizada"><input type="number" min={10} max={2000} value={c.candidates} onChange={e=>update("candidates",Math.min(2000,Math.max(10,Number(e.target.value)||10)))}/></Field></div></div>
        <div className="tq-config-note"><Zap size={17}/> Para evitar tiempos de bloqueo del servidor, se recomienda empezar con 100–500. Los trabajos distribuidos llegarán en otra fase.</div>
        <div className="tq-section-rule"/>
        <Subhead number="02" title="Familias de indicadores" desc="Selecciona qué lógicas participan en la generación de candidatos."/>
        <div className="tq-family-list">{[["ema_cross","Cruces EMA"],["rsi_reversion","Reversión RSI"],["breakout","Ruptura de canal"]].map(([key,label])=><button key={key} className={c.families.includes(key)?"active":""} onClick={()=>{const next=c.families.includes(key)?c.families.filter(x=>x!==key):[...c.families,key];if(next.length)update("families",next)}}><span>{c.families.includes(key)&&<Check size={14}/>}</span>{label}</button>)}</div>
        <div className="tq-section-rule"/>
        <button className="tq-advanced-trigger" onClick={()=>setAdvanced(x=>!x)}><SlidersHorizontal size={18}/><span><strong>Parámetros científicos avanzados</strong><small>Riesgo, costes, validación y Monte Carlo</small></span><ChevronDown size={19} style={{transform:advanced?"rotate(180deg)":undefined}}/></button>
        {advanced&&<div className="tq-settings-grid tq-advanced-fields">
          {numberField("Riesgo por trade (%)","risk_pct",.05,2,.05)}
          {numberField("Ratio TP / SL","rr",.2,5,.1)}
          {numberField("Stop (ATR ×)","atr_multiplier",.5,6,.1)}
          {numberField("Coste round-trip (bps)","cost_bps",0,100,.5)}
          {numberField("Entrenamiento IS (%)","is_ratio",50,85,5)}
          {numberField("Mínimo trades OOS","min_trades",1,100,1)}
          <Field title="Monte Carlo"><select value={c.mc_iterations} onChange={e=>update("mc_iterations",Number(e.target.value))}><option value={100}>100 escenarios</option><option value={500}>500 escenarios</option><option value={1000}>1,000 escenarios</option></select></Field>
          {numberField("Drawdown diario (%)","prop_daily_pct",.5,10,.5)}
          {numberField("Drawdown total (%)","prop_max_pct",1,20,.5)}
        </div>}
      </>}
    </div>
    <footer className="tq-config-footer"><button className="btn tq-secondary-button" onClick={()=>tab===0?onBack():setTab(i=>i-1)}><ArrowLeft size={16}/>{tab===0?"Volver":"Anterior"}</button><span><Check size={14}/> Borrador local</span>{tab===5?<button className="btn btn-primary" disabled={!canRun} onClick={onExecute}>{loading?<LoaderCircle className="spin" size={16}/>:<Play size={16}/>} {loading?"Ejecutando...":"Iniciar exploración"}</button>:<button className="btn btn-primary" onClick={()=>setTab(i=>Math.min(5,i+1))}>Continuar <ArrowRight size={16}/></button>}</footer>
   </section>
   <aside className="tq-config-aside"><div className="tq-aside-box"><div className="tq-aside-label"><FlaskConical size={18}/> RESUMEN DE LA SESIÓN</div><h3>{c.name}</h3><p>Configuración del experimento cuantitativo</p>{[["Símbolo",c.symbol],["Intervalos",selectedTfs.map(x=>TF.find(y=>y[0]===x)?.[1]).join(" · ")],["Depósito","USD "+money(c.initial_deposit)],["Tipo",c.mode==="genetic"?"Genético":"Aleatorio"],["Modelado",c.modeling==="open"?"Solo apertura":"OHLC"],["Dirección",c.direction==="both"?"Long + Short":c.direction==="long"?"Solo Long":"Solo Short"],["Sizing",c.sizing==="fixed"?"Fijo":"Compuesto"],["Multi-TF",c.multi_tf==="individual"?"Individual":c.multi_tf==="combined"?"Combinado":"Ambos"]].map(([k,v])=><div key={k} className="tq-aside-row"><span>{k}</span><strong>{v}</strong></div>)}<div className="tq-aside-count"><small>COMBINACIONES</small><strong>{money(c.candidates)}</strong></div></div>
   <div className="tq-aside-box tq-aside-science"><div className="tq-aside-label"><ShieldCheck size={18}/> CONTROL CIENTÍFICO</div><p>El tramo final queda fuera del entrenamiento. Las métricas no garantizan rentabilidad futura.</p><div className="tq-train-bar"><span style={{width:c.is_ratio+"%"}}/><span style={{width:(100-c.is_ratio)+"%"}}/></div><div className="tq-train-labels"><span>IS {c.is_ratio}%</span><span>OOS {100-c.is_ratio}%</span></div>{!c.dataset_id&&<div className="tq-config-warning">Falta seleccionar un dataset.</div>}{invalidMulti&&<div className="tq-config-warning">Se necesitan dos intervalos.</div>}</div></aside>
   </div>
 </div>;
}
