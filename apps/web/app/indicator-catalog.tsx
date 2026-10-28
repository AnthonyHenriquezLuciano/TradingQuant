"use client";

import {useMemo,useState} from "react";
import {Search, Plus, X, ChartNoAxesCombined, Waves, SlidersHorizontal, CircleHelp, Clock3, Check, MapPin, ChevronDown, ShieldCheck, Sparkles} from "lucide-react";
import type {IndicatorRanges} from "./strategy-configurator";

type Props={
 families:string[];ranges:IndicatorRanges;sourceTimezone:string;
 onFamilies:(families:string[])=>void;
 onRanges:(ranges:IndicatorRanges)=>void;
 onTimezone:(zone:string)=>void;
};
type Item={id:string;name:string;kind:"technical"|"situation";description:string;enabled:boolean;paramGroups:string[]};
const ITEMS:Item[]=[
 {id:"ema_cross",name:"Cruce EMA",kind:"technical",description:"Cruce de EMA rápida y lenta; seguimiento de tendencia.",enabled:true,paramGroups:["ema_fast","ema_slow"]},
 {id:"rsi_reversion",name:"RSI · reversión",kind:"technical",description:"Cruce de umbrales de sobreventa y sobrecompra simétrica.",enabled:true,paramGroups:["rsi_period","rsi_oversold"]},
 {id:"breakout",name:"Ruptura Donchian",kind:"technical",description:"Ruptura del máximo/mínimo del canal de N velas.",enabled:true,paramGroups:["breakout_lookback"]},
 {id:"london_high_sweep",name:"Barrida del máximo de Londres",kind:"situation",description:"Tras cerrar Londres, rompe su máximo y cierra nuevamente debajo → Short.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"london_low_sweep",name:"Barrida del mínimo de Londres",kind:"situation",description:"Tras cerrar Londres, rompe su mínimo y recupera el nivel → Long.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"asia_high_sweep",name:"Barrida del máximo de Asia",kind:"situation",description:"Tras cerrar Tokio, rompe su máximo y cierra por debajo → Short.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"asia_low_sweep",name:"Barrida del mínimo de Asia",kind:"situation",description:"Tras cerrar Tokio, rompe su mínimo y cierra por encima → Long.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"previous_day_high_sweep",name:"Barrida del máximo del día anterior (PDH)",kind:"situation",description:"Rompe el máximo del último día con datos y cierra debajo → Short.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"previous_day_low_sweep",name:"Barrida del mínimo del día anterior (PDL)",kind:"situation",description:"Rompe el mínimo del último día con datos y cierra encima → Long.",enabled:true,paramGroups:["sweep_buffer"]},
 {id:"adx",name:"ADX",kind:"technical",description:"Fuerza de tendencia. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"macd",name:"MACD",kind:"technical",description:"Convergencia/divergencia. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"bollinger",name:"Bandas de Bollinger",kind:"technical",description:"Volatilidad y desviaciones. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"sma",name:"Cruce SMA / MA",kind:"technical",description:"Cruces de medias simples. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"ema200",name:"EMA 200",kind:"technical",description:"Filtro de tendencia por EMA. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"stochastic",name:"Estocástico",kind:"technical",description:"Oscilador de momentum. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"supertrend",name:"SuperTrend",kind:"technical",description:"Tendencia ATR. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"kama",name:"KAMA",kind:"technical",description:"Media adaptativa. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"vwap",name:"VWAP",kind:"technical",description:"Precio medio ponderado por volumen. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"cci",name:"CCI",kind:"technical",description:"Oscilador Commodity Channel. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"mfi",name:"MFI",kind:"technical",description:"Índice de flujo monetario. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"obv",name:"OBV",kind:"technical",description:"Volumen acumulado. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"ichimoku",name:"Ichimoku",kind:"technical",description:"Nube y tendencia. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"keltner",name:"Canales Keltner",kind:"technical",description:"Bandas de volatilidad. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"rsi_divergence",name:"Divergencia RSI",kind:"situation",description:"Desacuerdo precio/oscilador. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"fvg",name:"Fair Value Gap (FVG)",kind:"situation",description:"Desequilibrios de tres velas. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"bos",name:"Break of Structure (BOS)",kind:"situation",description:"Ruptura estructural de mercado. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"choc",name:"Change of Character (CHoCH)",kind:"situation",description:"Cambio de estructura. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"poc_retest",name:"Retorno al POC",kind:"situation",description:"Revisita al punto de control del volumen. Motor pendiente.",enabled:false,paramGroups:[]},
 {id:"vwap_reclaim",name:"Recuperación de VWAP",kind:"situation",description:"Retorno sobre el VWAP de sesión. Motor pendiente.",enabled:false,paramGroups:[]},
];
const PARAMS:Record<string,{name:string;min:number;max:number;unit?:string}>={
 ema_fast:{name:"EMA rápida · periodo",min:2,max:100},
 ema_slow:{name:"EMA lenta · periodo",min:10,max:250},
 rsi_period:{name:"RSI · periodo",min:2,max:60},
 rsi_oversold:{name:"RSI · sobreventa",min:5,max:45},
 breakout_lookback:{name:"Canal · velas",min:5,max:250},
 sweep_buffer:{name:"Exceso mínimo",min:0,max:30,unit:"bps"},
};
const ZONES=[
 ["UTC","UTC · histórico en hora universal"],
 ["Europe/London","Europe/London · horario británico"],
 ["Europe/Athens","Europe/Athens · GMT+2/+3"],
 ["America/New_York","America/New_York · NY"],
 ["America/Santo_Domingo","America/Santo_Domingo · RD"],
 ["Asia/Tokyo","Asia/Tokyo · Tokio"],
];

export function IndicatorCatalog({families,ranges,sourceTimezone,onFamilies,onRanges,onTimezone}:Props){
 const [open,setOpen]=useState(false);
 const [query,setQuery]=useState("");
 const [kind,setKind]=useState<"technical"|"situation">("technical");
 const [showUnavailable,setShowUnavailable]=useState(false);
 const filtered=useMemo(()=>ITEMS.filter(i=>i.kind===kind&&(showUnavailable||i.enabled)&&
  (i.name+" "+i.description).toLocaleLowerCase("es").includes(query.toLocaleLowerCase("es").trim())),[kind,query,showUnavailable]);
 const chosen=ITEMS.filter(i=>families.includes(i.id)&&i.enabled);
 const anySituation=chosen.some(i=>i.kind==="situation");
 const rangesFor=(prefix:string)=>{
  const keys=["min","step","max"] as const;
  return keys.map(s=>Number(ranges[(prefix+"_"+s) as keyof IndicatorRanges]));
 };
 const size=chosen.reduce((total,item)=>{
  const variants=item.paramGroups.reduce((value,p)=>{
   const [from,step,to]=rangesFor(p);
   return value*Math.max(0,Math.floor((to-from)/Math.max(1,step))+1);
  },1);
  return total+variants;
 },0);
 const hasBad=Object.keys(PARAMS).some(k=>{
  const [a,step,b]=rangesFor(k);
  const meta=PARAMS[k];return !Number.isInteger(a)||!Number.isInteger(step)||!Number.isInteger(b)||a> b||step<1||a<meta.min||b>meta.max;
 })||(ranges.ema_fast_min+8>ranges.ema_slow_max);
 function add(id:string){if(!families.includes(id))onFamilies([...families,id]);setOpen(false);setQuery("")}
 function remove(id:string){onFamilies(families.filter(x=>x!==id))}
 function change(prefix:string,field:"min"|"step"|"max",value:string){
  const v=Number(value);
  if(!Number.isFinite(v))return;
  onRanges({...ranges,[prefix+"_"+field]:Math.trunc(v)});
 }
 return <div className="tq-catalog">
  <div className="tq-catalog-toolbar">
   <div><div className="tq-catalog-overline">ESTRATEGIAS / MOTOR DE SEÑALES</div><h3>Elementos de búsqueda <span>{chosen.length}</span></h3>
    <p>Combina indicadores cuantitativos con situaciones específicas del precio.</p></div>
   <button className="tq-catalog-add" onClick={()=>setOpen(v=>!v)} aria-expanded={open}><Plus size={17}/> Agregar indicador o situación <ChevronDown size={15}/></button>
  </div>
  {open&&<div className="tq-catalog-picker">
   <div className="tq-catalog-picker-top">
    <div className="tq-catalog-category">
     <button className={kind==="technical"?"active":""} onClick={()=>setKind("technical")}><ChartNoAxesCombined size={15}/> Indicadores técnicos</button>
     <button className={kind==="situation"?"active":""} onClick={()=>setKind("situation")}><Waves size={15}/> Situaciones de mercado</button>
    </div>
    <button className="tq-picker-close" onClick={()=>setOpen(false)} aria-label="Cerrar catálogo"><X size={17}/></button>
   </div>
   <label className="tq-catalog-search"><Search size={16}/><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="Buscar por nombre o situación..." aria-label="Buscar indicadores"/></label>
   <div className="tq-catalog-results">
    {filtered.length===0&&<p className="tq-catalog-empty">No se encontraron coincidencias.</p>}
    {filtered.map(item=><button key={item.id} className="tq-catalog-result" disabled={!item.enabled||families.includes(item.id)} onClick={()=>add(item.id)}>
     <span className="tq-catalog-result-symbol">{item.kind==="situation"?<Waves size={16}/>:<ChartNoAxesCombined size={16}/>}</span>
     <span><strong>{item.name}</strong><small>{item.description}</small></span>
     <em>{families.includes(item.id)?"Agregado":item.enabled?<Plus size={17}/>:"En desarrollo"}</em>
    </button>)}
   </div>
   <label className="tq-catalog-show-future"><input type="checkbox" checked={showUnavailable} onChange={e=>setShowUnavailable(e.target.checked)}/> Mostrar indicadores en desarrollo</label>
  </div>}
  {chosen.length?<>
   <div className="tq-parameter-table-head"><span>Indicador / situación</span><span>Parámetro</span><span>Desde</span><span>Pasos</span><span>Hasta</span></div>
   <div className="tq-parameter-table">
    {chosen.map(item=><div className="tq-parameter-group" key={item.id}>
      <div className="tq-parameter-name"><button aria-label={"Quitar "+item.name} title="Quitar" onClick={()=>remove(item.id)}><X size={16}/></button><div><strong>{item.name}</strong><small>{item.kind==="situation"?"SITUACIÓN DE MERCADO":"INDICADOR TÉCNICO"}</small></div></div>
      <div className="tq-parameter-fields">
       {item.paramGroups.map(p=>{
        const meta=PARAMS[p];const [min,step,max]=rangesFor(p);
        return <div className="tq-parameter-line" key={p}>
         <div className="tq-parameter-desc">{meta.name}{meta.unit&&<small>({meta.unit})</small>}</div>
         <label><span>Desde</span><input aria-label={item.name+" "+meta.name+" desde"} type="number" min={meta.min} max={meta.max} step={1} value={min} onChange={e=>change(p,"min",e.target.value)}/></label>
         <label><span>Pasos</span><input aria-label={item.name+" "+meta.name+" pasos"} type="number" min={1} max={30} step={1} value={step} onChange={e=>change(p,"step",e.target.value)}/></label>
         <label><span>Hasta</span><input aria-label={item.name+" "+meta.name+" hasta"} type="number" min={meta.min} max={meta.max} step={1} value={max} onChange={e=>change(p,"max",e.target.value)}/></label>
        </div>;
       })}
       {item.id==="rsi_reversion"&&<p className="tq-rsi-note">La sobrecompra es simétrica: 100 − sobreventa. Ej.: sobreventa 20–35 equivale a sobrecompra 80–65.</p>}
       {item.kind==="situation"&&<p className="tq-sweep-note">Confirmación por cierre de vela; entrada en la apertura siguiente. Una señal por jornada de referencia.</p>}
      </div>
    </div>)}
   </div>
  </>:<div className="tq-no-indicators"><SlidersHorizontal size={25}/><strong>No hay indicadores seleccionados</strong><p>Agrega al menos un indicador técnico o una situación de mercado para la búsqueda.</p><button onClick={()=>setOpen(true)}><Plus size={15}/> Agregar elemento</button></div>}
  {anySituation&&<div className="tq-catalog-session-box">
   <div className="tq-catalog-session-heading"><Clock3 size={17}/><div><strong>Horarios y zona de los datos</strong><p>Para identificar barridas sin anticipar niveles.</p></div></div>
   <label>Zona horaria original del CSV <select value={sourceTimezone} onChange={e=>onTimezone(e.target.value)}>{ZONES.map(([v,name])=><option value={v} key={v}>{name}</option>)}</select></label>
   <div className="tq-session-hours"><span><MapPin size={14}/> Londres: 08:00–16:00 (hora Londres)</span><span><MapPin size={14}/> Tokio: 09:00–17:00 (hora Tokio)</span></div>
   <p>Se considera barrida cuando, después de cerrar la sesión, el precio supera el máximo/mínimo del rango y cierra nuevamente dentro. Solo se buscan señales desde el cierre de la sesión hasta la medianoche local. PDH/PDL utiliza el último día completo disponible. Requiere velas M1–H1 y la zona horaria correcta del archivo; el motor ajusta el horario de verano con zonas IANA.</p>
  </div>}
  <div className="tq-catalog-stats"><span>Espacio de parámetros por familia (referencial):</span><strong>{new Intl.NumberFormat("en-US").format(size)}</strong></div>
  {hasBad&&<div className="tq-indicator-error" role="alert">Revisa los rangos: mínimo ≤ máximo, paso positivo y EMA lenta al menos 8 periodos mayor que EMA rápida.</div>}
  <div className="tq-catalog-science"><ShieldCheck size={17}/> <span>Las selecciones y los incrementos definidos se aplican al generador aleatorio y genético. Los indicadores que aparecen como «En desarrollo» no pueden ejecutarse hasta tener su motor científico.</span></div>
 </div>;
}
