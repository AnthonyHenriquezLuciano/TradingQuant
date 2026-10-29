"use client";
import {useState} from "react";
import {ArrowRight,Check,ChevronDown,Info,LockKeyhole,ShieldCheck,SlidersHorizontal,Target,Wallet} from "lucide-react";
export type Range={from:number;step:number;to:number};
export type CapitalSettings={
 exit_mode:"atr_linked"|"atr_classic"|"percent";
 sl_atr:Range;tp_multiplier:Range;tp_atr:Range;sl_percent:Range;
 breakeven_enabled:boolean;breakeven_r:number;trailing_enabled:boolean;trailing_atr:number;
 max_bars_in_trade:number;max_trades_per_day:number;cooldown_bars:number;stop_after_daily_pct:number;
};
export const DEFAULT_CAPITAL:CapitalSettings={
 exit_mode:"atr_linked",
 sl_atr:{from:.5,step:.1,to:3},tp_multiplier:{from:.5,step:.1,to:2},
 tp_atr:{from:.5,step:.1,to:6},sl_percent:{from:.1,step:.1,to:1.5},
 breakeven_enabled:false,breakeven_r:1,trailing_enabled:false,trailing_atr:1.5,
 max_bars_in_trade:0,max_trades_per_day:0,cooldown_bars:0,stop_after_daily_pct:0
};
type Props={
 value:CapitalSettings;onChange:(v:CapitalSettings)=>void;deposit:number;riskPct:number;
 sizing:"compound"|"fixed";dailyDD:number;totalDD:number;
 onRisk:(n:number)=>void;onSizing:(v:"compound"|"fixed")=>void;
 onDailyDD:(n:number)=>void;onTotalDD:(n:number)=>void;
};
type RangeKey="sl_atr"|"tp_multiplier"|"tp_atr"|"sl_percent";
const RANGES:Record<RangeKey,{label:string;min:number;max:number}>={
 sl_atr:{label:"Stop Loss (× ATR)",min:.1,max:10},tp_multiplier:{label:"Take Profit (× SL)",min:.1,max:10},
 tp_atr:{label:"Take Profit (× ATR)",min:.1,max:12},sl_percent:{label:"SL (% del precio)",min:.05,max:10}
};
const modes=[
 ["atr_linked","ATR + TP multiplicador","SL = ATR × A. TP = distancia del SL × B.",true],
 ["atr_classic","ATR (clásico)","SL = ATR × A. TP = ATR × B, independientes.",true],
 ["percent","Porcentaje","SL como % del precio y TP múltiplo del SL.",true],
 ["fixed_pips","Pips fijos","Requiere precisión de tick y valor de pip por instrumento.",false],
 ["swing","Estructura (Swing)","Requiere pivotes confirmados y SL estructural.",false],
 ["partial","TP parcial","Requiere salida por fracciones de la posición.",false],
 ["smoothed","ATR suavizado","ATR adaptativo con motor específico.",false]
] as const;
function Numeric({label,value,onChange,min,max,step=1}:{label:string;value:number;onChange:(v:number)=>void;min:number;max:number;step?:number}){
 return <label className="tq-risk-number"><span>{label}</span><input type="number" value={value} min={min} max={max} step={step} onChange={e=>{let n=Number(e.target.value);if(Number.isFinite(n))onChange(n)}}/></label>;
}
export function CapitalManagement({value,onChange,deposit,riskPct,sizing,dailyDD,totalDD,onRisk,onSizing,onDailyDD,onTotalDD}:Props){
 const c={...DEFAULT_CAPITAL,...value};
 const [showModes,setShowModes]=useState(false);
 const [expanded,setExpanded]=useState(["exits","risk"]);
 const toggle=(id:string)=>setExpanded(p=>p.includes(id)?p.filter(x=>x!==id):[...p,id]);
 const change=(patch:Partial<CapitalSettings>)=>onChange({...c,...patch});
 const keys:RangeKey[]=c.exit_mode==="atr_classic"?["sl_atr","tp_atr"]:c.exit_mode==="percent"?["sl_percent","tp_multiplier"]:["sl_atr","tp_multiplier"];
 const numComb=keys.reduce((acc,k)=>{let r=c[k];return acc*Math.max(0,Math.floor((r.to-r.from)/Math.max(.0001,r.step)+1e-8)+1)},1);
 const selected=modes.find(m=>m[0]===c.exit_mode);
 const isValid=keys.every(k=>{const r=c[k],b=RANGES[k];return r.from>=b.min&&r.to<=b.max&&r.from<=r.to&&r.step>0;});
 const fmt=(x:number)=>new Intl.NumberFormat("es-DO",{maximumFractionDigits:2}).format(x);
 const rows=(id:string,title:string,sub:string,children:React.ReactNode)=><section className="tq-capital-group"><button type="button" className="tq-capital-group-title" aria-expanded={expanded.includes(id)} onClick={()=>toggle(id)}><span><SlidersHorizontal size={17}/>{title}</span><small>{sub}</small><ChevronDown className={expanded.includes(id)?"rotated":""} size={17}/></button>{expanded.includes(id)&&<div className="tq-capital-group-content">{children}</div>}</section>;
 return <div className="tq-capital-page">
 <div className="tq-capital-intro"><div><div className="tq-capital-overline">GESTIÓN MONETARIA / MOTOR CUANTITATIVO</div><h3>Gestión de capital y salidas</h3><p>Optimiza SL/TP y controla el riesgo de cada estrategia.</p></div><span><ShieldCheck size={15}/> Solo investigación</span></div>
 {rows("exits","Modos de salida","ATR, múltiplos y porcentajes",<>
  <div className="tq-capital-mode-selector"><span>Modo de salida</span><button onClick={()=>setShowModes(x=>!x)}>{selected?.[1]} <ChevronDown size={15}/></button></div>
  {showModes&&<div className="tq-capital-mode-list">{modes.map(([id,name,desc,available])=><button key={id} disabled={!available} onClick={()=>{change({exit_mode:id as CapitalSettings["exit_mode"]});setShowModes(false)}}><span>{available?(c.exit_mode===id?<Check size={16}/>:<Target size={16}/>):<LockKeyhole size={16}/>}</span><span><strong>{name}</strong><small>{desc}</small></span>{!available&&<em>En desarrollo</em>}</button>)}</div>}
  <p className="tq-capital-formula">{selected?.[2]} Los parámetros son rangos optimizables: Desde / Pasos / Hasta.</p>
  <div className="tq-capital-table"><div className="tq-capital-table-heading"><strong>Parámetro</strong><span>Desde</span><span>Pasos</span><span>Hasta</span></div>
  {keys.map(key=><div className="tq-capital-table-row" key={key}><strong>{RANGES[key].label}</strong>{(["from","step","to"] as const).map(field=><label key={field}><span>{field==="from"?"Desde":field==="step"?"Pasos":"Hasta"}</span><input type="number" step={.05} min={field==="step"?.01:RANGES[key].min} max={field==="step"?3:RANGES[key].max} value={c[key][field]} onChange={e=>{const n=Number(e.target.value);if(Number.isFinite(n))change({[key]:{...c[key],[field]:n}} as Partial<CapitalSettings>)}}/></label>)}</div>)}</div>
  {!isValid&&<p className="tq-capital-warning">Los rangos deben tener Desde ≤ Hasta y un paso positivo.</p>}
  <div className="tq-capital-combinations"><span>Combinaciones SL/TP posibles (referencial)</span><strong>{fmt(numComb)}</strong></div>
  <p className="tq-capital-muted">El buscador respeta el presupuesto global de combinaciones. Cada candidato conserva sus parámetros de salida en IS y OOS.</p>
 </>)}
 {rows("dynamic","Gestión dinámica","Breakeven, trailing y tiempo de salida",<>
  <div className="tq-capital-checkrow"><label><input type="checkbox" checked={c.breakeven_enabled} onChange={e=>change({breakeven_enabled:e.target.checked})}/> Breakeven al alcanzar X veces el riesgo inicial</label>{c.breakeven_enabled&&<Numeric label="Activación BE (R)" value={c.breakeven_r} min={.1} max={10} step={.1} onChange={n=>change({breakeven_r:n})}/>}</div>
  <div className="tq-capital-checkrow"><label><input type="checkbox" checked={c.trailing_enabled} onChange={e=>change({trailing_enabled:e.target.checked})}/> Trailing Stop basado en ATR</label>{c.trailing_enabled&&<Numeric label="Distancia (× ATR)" value={c.trailing_atr} min={.1} max={10} step={.1} onChange={n=>change({trailing_atr:n})}/>}</div>
  <Numeric label="Salida por tiempo (barras, 0 = desactivado)" value={c.max_bars_in_trade} min={0} max={1000} step={1} onChange={n=>change({max_bars_in_trade:n})}/>
  <p className="tq-capital-muted">Las actualizaciones de BE y trailing se aplican desde la vela siguiente. Una barrida simultánea SL/TP favorece el SL (peor caso).</p>
 </>)}
 {rows("risk","Tamaño de posición y riesgo","Base fija o compuesta, límites de pérdida",<>
  <div className="tq-capital-risk-grid">
   <Numeric label="Riesgo por trade (%)" value={riskPct} min={.05} max={2} step={.05} onChange={onRisk}/>
   <label className="tq-risk-number"><span>Base de riesgo</span><select value={sizing} onChange={e=>onSizing(e.target.value as "fixed"|"compound")}><option value="fixed">Saldo inicial (fijo)</option><option value="compound">Saldo actual (compuesto)</option></select></label>
   <Numeric label="Drawdown diario (%)" value={dailyDD} min={.5} max={10} step={.5} onChange={onDailyDD}/>
   <Numeric label="Drawdown total (%)" value={totalDD} min={1} max={20} step={.5} onChange={onTotalDD}/>
  </div>
  <div className="tq-capital-figures"><span>Capital base <strong>USD {fmt(deposit)}</strong></span><span>Riesgo inicial <strong>USD {fmt(deposit*riskPct/100)}</strong></span><span>DD diario nominal <strong>USD {fmt(deposit*dailyDD/100)}</strong></span></div>
  <p className="tq-capital-muted">Control en esta versión basado en trades cerrados. No evalúa equity flotante intrabar, margen libre ni reglas particulares de una firma.</p>
 </>)}
 {rows("guards","Límites operativos","Freno por actividad y beneficios diarios",<>
  <div className="tq-capital-risk-grid">
   <Numeric label="Máximo trades/día (0 = sin límite)" value={c.max_trades_per_day} min={0} max={100} step={1} onChange={n=>change({max_trades_per_day:n})}/>
   <Numeric label="Cooldown después de cerrar (barras)" value={c.cooldown_bars} min={0} max={1000} step={1} onChange={n=>change({cooldown_bars:n})}/>
   <Numeric label="Parar por beneficio diario (%) (0 = off)" value={c.stop_after_daily_pct} min={0} max={20} step={.25} onChange={n=>change({stop_after_daily_pct:n})}/>
  </div>
  <p className="tq-capital-muted">Los límites se comprueban sobre saldo realizado; los SL de seguridad siguen activos aunque se alcance un límite.</p>
 </>)}
 <div className="tq-capital-note"><Info size={17}/> Modos de pips, estructura y salida parcial están identificados como pendientes hasta tener una simulación respaldada por datos del instrumento. No se ejecutan de manera aproximada.</div>
 </div>;
}
