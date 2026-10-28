"use client";

import {useMemo,useState} from "react";
import {
  Search,Plus,X,ChartNoAxesCombined,Waves,SlidersHorizontal,Clock3,Check,
  MapPin,ChevronDown,ShieldCheck,Landmark,Activity,CalendarDays,Info
} from "lucide-react";
import type {IndicatorRanges} from "./strategy-configurator";
import {CATALOG_GROUPS,CATALOG_ITEMS,MACRO_GROUPS,MACRO_SERIES,type CatalogKind,type CatalogItem,type MacroSeries} from "./indicator-data";

export type MacroRule={
 condition:"rising"|"falling"|"above"|"below";
 threshold:number;
 min_release_lag_days:number;
};

type Props={
 families:string[];ranges:IndicatorRanges;sourceTimezone:string;
 macroIndicators:string[];macroRules:Record<string,MacroRule>;
 onFamilies:(families:string[])=>void;onRanges:(ranges:IndicatorRanges)=>void;
 onTimezone:(zone:string)=>void;onMacroIndicators:(ids:string[])=>void;
 onMacroRules:(rules:Record<string,MacroRule>)=>void;
};

const PARAMS:Record<string,{name:string;min:number;max:number;unit?:string}>={
 ema_fast:{name:"EMA rápida · periodo",min:2,max:100},
 ema_slow:{name:"EMA lenta · periodo",min:10,max:250},
 rsi_period:{name:"RSI · periodo",min:2,max:60},
 rsi_oversold:{name:"RSI · sobreventa",min:5,max:45},
 breakout_lookback:{name:"Canal · velas",min:5,max:250},
 ...Object.fromEntries(
 ["london_high_sweep","london_low_sweep","asia_high_sweep","asia_low_sweep","previous_day_high_sweep","previous_day_low_sweep"]
 .map(id=>[id+"_buffer",{name:"Barrida mínima",min:0,max:30,unit:"bps"}])
 )
};
const ZONES=[
 ["UTC","UTC · hora universal"],["Europe/London","Europe/London · Reino Unido"],
 ["Europe/Athens","Europe/Athens"],["America/New_York","America/New_York"],
 ["America/Santo_Domingo","America/Santo_Domingo · RD"],["Asia/Tokyo","Asia/Tokyo"]
];
const STATUS:Record<CatalogKind,string>={technical:"Indicadores técnicos",situation:"Situaciones del mercado",macro:"Indicadores macroeconómicos"};
const newRule=():MacroRule=>({condition:"rising",threshold:0,min_release_lag_days:1});
const format=(n:number)=>new Intl.NumberFormat("es-DO",{maximumFractionDigits:0}).format(n);

export function IndicatorCatalog({
 families,ranges,sourceTimezone,macroIndicators,macroRules,
 onFamilies,onRanges,onTimezone,onMacroIndicators,onMacroRules
}:Props){
 const [category,setCategory]=useState<CatalogKind>("technical");
 const [query,setQuery]=useState("");
 const [onlyAvailable,setOnlyAvailable]=useState(false);
 const [expanded,setExpanded]=useState<string[]>([]);
 const selectedItems=CATALOG_ITEMS.filter(item=>item.kind===category&&families.includes(item.id)&&item.enabled);
 const selectedMacro=MACRO_SERIES.filter(item=>macroIndicators.includes(item.id));
 const total=category==="macro"?selectedMacro.length:selectedItems.length;
 const categoryItems=useMemo(()=>CATALOG_ITEMS.filter(i=>i.kind===category),[category]);
 const filtered=useMemo(()=>categoryItems.filter(item=>
  (!onlyAvailable||item.enabled)&&
  (item.name+" "+item.description).toLocaleLowerCase("es").includes(query.toLocaleLowerCase("es").trim())
 ),[categoryItems,query,onlyAvailable]);
 const macroFiltered=useMemo(()=>MACRO_GROUPS.map(group=>({
  ...group,series:group.series.filter(item=>(item.name+" "+group.title).toLocaleLowerCase("es").includes(query.toLocaleLowerCase("es").trim()))
 })).filter(group=>group.series.length),[query]);
 const hasSituation=families.some(id=>CATALOG_ITEMS.some(i=>i.id===id&&i.kind==="situation"&&i.enabled));
 const rangesFor=(prefix:string)=>(["min","step","max"] as const).map(k=>Number(ranges[(prefix+"_"+k) as keyof IndicatorRanges]));
 const paramSpace=CATALOG_ITEMS.filter(i=>i.enabled&&families.includes(i.id)).reduce((sum,i)=>
  sum+i.paramGroups.reduce((product,p)=>{const [from,step,to]=rangesFor(p);return product*Math.max(0,Math.floor((to-from)/Math.max(1,step))+1)},1),0);
 const invalid=Object.entries(PARAMS).some(([name,meta])=>{const [from,step,to]=rangesFor(name);return !Number.isInteger(from)||!Number.isInteger(step)||!Number.isInteger(to)||from>to||from<meta.min||to>meta.max||step<1||step>30});
 function chooseCategory(next:CatalogKind){setCategory(next);setQuery("");setExpanded([])}
 function addItem(item:CatalogItem){if(!item.enabled||families.includes(item.id))return;onFamilies([...families,item.id])}
 function addMacro(item:MacroSeries){if(macroIndicators.includes(item.id))return;onMacroIndicators([...macroIndicators,item.id]);onMacroRules({...macroRules,[item.id]:newRule()})}
 function removeMacro(id:string){onMacroIndicators(macroIndicators.filter(i=>i!==id));const next={...macroRules};delete next[id];onMacroRules(next)}
 function updateRule(id:string,patch:Partial<MacroRule>){onMacroRules({...macroRules,[id]:{...(macroRules[id]||newRule()),...patch}})}
 function updateRange(name:string,key:"min"|"step"|"max",raw:string){const value=Number(raw);if(!Number.isFinite(value))return;onRanges({...ranges,[name+"_"+key]:Math.trunc(value)})}
 function toggleGroup(id:string){setExpanded(current=>current.includes(id)?current.filter(x=>x!==id):[...current,id])}
 return <div className="tq-catalog">
  <div className="tq-library-categories" role="tablist" aria-label="Tipos de indicadores">
   <button role="tab" aria-selected={category==="technical"} onClick={()=>chooseCategory("technical")} className={category==="technical"?"active":""}><ChartNoAxesCombined size={16}/> Técnicos <span>{families.filter(id=>CATALOG_ITEMS.some(i=>i.id===id&&i.kind==="technical")).length}</span></button>
   <button role="tab" aria-selected={category==="situation"} onClick={()=>chooseCategory("situation")} className={category==="situation"?"active":""}><Waves size={16}/> Situaciones del mercado <span>{families.filter(id=>CATALOG_ITEMS.some(i=>i.id===id&&i.kind==="situation")).length}</span></button>
   <button role="tab" aria-selected={category==="macro"} onClick={()=>chooseCategory("macro")} className={category==="macro"?"active":""}><Landmark size={16}/> Indicadores macroeconómicos <span>{macroIndicators.length}</span></button>
  </div>
  <div className="tq-catalog-toolbar">
   <div><div className="tq-catalog-overline">{category==="macro"?"MACROECONOMÍA / VARIABLES EXTERNAS":"ESTRATEGIAS / GENERADOR DE SEÑALES"}</div>
    <h3>{STATUS[category]} <span>{total} seleccionados</span></h3>
    <p>{category==="macro"
      ?"Explora las series macroeconómicas por categoría y prepara sus reglas para una futura integración de datos."
      :"Selecciona indicadores y situaciones por grupos, y configura los parámetros de cada señal."}</p>
   </div>
   <span className="tq-library-count"><SlidersHorizontal size={15}/>{category==="macro"?MACRO_SERIES.length:categoryItems.length} disponibles en el catálogo</span>
  </div>
  <section className="tq-catalog-picker tq-library-browser" aria-label={"Catálogo de "+STATUS[category]}>
   <div className="tq-catalog-picker-top">
    <strong className="tq-picker-title">{category==="macro"?"Variables macroeconómicas":category==="situation"?"Situaciones y patrones de mercado":"Biblioteca de indicadores técnicos"}</strong>
    <span className="tq-library-hint">Selecciona una categoría para expandirla</span>
   </div>
   <label className="tq-catalog-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={category==="macro"?"Buscar VIX, CPI, NFP, Treasury, DXY...":category==="situation"?"Buscar barridas, liquidez, FVG, BOS...":"Buscar RSI, EMA, ADX, volumen..."} aria-label="Buscar en catálogo"/>{query&&<button type="button" className="tq-search-clear" onClick={()=>setQuery("")} aria-label="Limpiar búsqueda"><X size={15}/></button>}</label>
   <div className="tq-grouped-catalog tq-library-groups">
    {category==="macro"?(
     macroFiltered.length?macroFiltered.map(group=>{
      const opened=!!query.trim()||expanded.includes(group.id);
      const added=group.series.filter(item=>macroIndicators.includes(item.id)).length;
      return <section key={group.id} className={"tq-catalog-group "+(opened?"is-expanded":"")}>
       <button type="button" className="tq-group-toggle" onClick={()=>toggleGroup(group.id)} aria-expanded={opened}>
        <Landmark size={16}/><strong>{group.title}</strong><span className="tq-group-meta">{added>0&&<em>{added} agregados</em>}<small>{group.series.length} series</small></span><ChevronDown className={opened?"rotated":""} size={16}/>
       </button>
       {opened&&<div className="tq-macro-grid">{group.series.map(item=><button type="button" key={item.id} disabled={macroIndicators.includes(item.id)} className="tq-macro-option" onClick={()=>addMacro(item)}>
        <span>{item.name}</span><em title={item.frequency==="D"?"Diaria":item.frequency==="W"?"Semanal":item.frequency==="M"?"Mensual":"Trimestral"}>{item.frequency}</em><small>{macroIndicators.includes(item.id)?<Check size={13}/>:<Plus size={13}/>}</small>
       </button>)}</div>}
      </section>;
     }):<p className="tq-catalog-empty">No se encontraron variables con ese término.</p>
    ):(
     CATALOG_GROUPS.filter(group=>filtered.some(item=>item.group===group.id)).map(group=>{
      const items=filtered.filter(item=>item.group===group.id);
      const added=items.filter(item=>families.includes(item.id)).length;
      const opened=!!query.trim()||expanded.includes(group.id);
      return <section key={group.id} className={"tq-catalog-group "+(opened?"is-expanded":"")}>
       <button type="button" className="tq-group-toggle" onClick={()=>toggleGroup(group.id)} aria-expanded={opened}>
        {category==="situation"?<Waves size={16}/>:<ChartNoAxesCombined size={16}/>}
        <strong>{group.title}</strong>
        <span className="tq-group-meta">{added>0&&<em>{added} agregados</em>}<small>{items.length} elementos</small></span>
        <ChevronDown className={opened?"rotated":""} size={16}/>
       </button>
       {opened&&<div className="tq-library-items">{items.map(item=><button type="button" key={item.id}
        className={"tq-catalog-result "+(!item.enabled?"is-pending":"")}
        disabled={!item.enabled||families.includes(item.id)} onClick={()=>addItem(item)}>
        <span className="tq-catalog-result-symbol">{item.kind==="situation"?<Waves size={16}/>:<ChartNoAxesCombined size={16}/>}</span>
        <span><strong>{item.name}</strong><small>{item.description}</small></span>
        <em>{families.includes(item.id)?<><Check size={13}/> Agregado</>:item.enabled?<><Plus size={14}/> Agregar</>:"En desarrollo"}</em>
       </button>)}</div>}
      </section>;
     })
    )}
    {category!=="macro"&&filtered.length===0&&<p className="tq-catalog-empty">No hay elementos que coincidan con tu búsqueda.</p>}
   </div>
   {category!=="macro"
    ?<label className="tq-catalog-show-future"><input type="checkbox" checked={onlyAvailable} onChange={e=>setOnlyAvailable(e.target.checked)}/> Mostrar solo señales implementadas</label>
    :<div className="tq-catalog-macro-explainer"><Info size={15}/> D = diaria · W = semanal · M = mensual · Q = trimestral. Seleccionar una serie prepara su regla; no descarga datos históricos todavía.</div>}
  </section>
  {category!=="macro"&&selectedItems.length>0&&<>
   <div className="tq-parameter-table-head"><span>Indicador / situación</span><span>Parámetro</span><span>Desde</span><span>Pasos</span><span>Hasta</span></div>
   <div className="tq-parameter-table">
    {selectedItems.map(item=><div className="tq-parameter-group" key={item.id}>
     <div className="tq-parameter-name"><button aria-label={"Eliminar "+item.name} onClick={()=>onFamilies(families.filter(x=>x!==item.id))}><X size={16}/></button><div><strong>{item.name}</strong><small>{item.kind==="situation"?"SITUACIÓN":"TÉCNICO"}</small></div></div>
     <div className="tq-parameter-fields">
      {item.paramGroups.map(prefix=>{
       const meta=PARAMS[prefix];if(!meta)return null;
       const values=rangesFor(prefix);
       return <div className="tq-parameter-line" key={prefix}><div className="tq-parameter-desc">{meta.name} {meta.unit&&<small>({meta.unit})</small>}</div>
        {(["min","step","max"] as const).map((field,index)=><label key={field}><span>{field==="min"?"Desde":field==="step"?"Pasos":"Hasta"}</span><input type="number" aria-label={item.name+" "+meta.name+" "+field} min={field==="step"?1:meta.min} max={field==="step"?30:meta.max} value={values[index]} onChange={e=>updateRange(prefix,field,e.target.value)}/></label>)}
       </div>;
      })}
      {item.id==="rsi_reversion"&&<p className="tq-rsi-note">La sobrecompra se calcula como 100 − umbral de sobreventa.</p>}
      {item.kind==="situation"&&<p className="tq-sweep-note">La barrida exige cierre de confirmación y entrada posterior. Una señal por jornada de referencia.</p>}
     </div>
    </div>)}
   </div>
  </>}
  {category==="macro"&&selectedMacro.length>0&&<div className="tq-macro-selected"><div className="tq-macro-rules-heading"><strong>Reglas macro seleccionadas</strong><span>{selectedMacro.length} {selectedMacro.length===1?"variable":"variables"} · pendientes de conexión de datos</span></div>
   <div className="tq-macro-selected-head"><span>Variable macroeconómica</span><span>Frecuencia</span><span>Regla (borrador)</span><span>Retardo mín. (días)</span></div>
   {selectedMacro.map(item=>{const rule=macroRules[item.id]||newRule();return <div className="tq-macro-selected-row" key={item.id}>
    <div className="tq-macro-selected-name"><button onClick={()=>removeMacro(item.id)} title="Quitar serie" aria-label={"Quitar "+item.name}><X size={16}/></button><strong>{item.name}</strong></div>
    <small>{item.frequency}</small>
    <select aria-label={"Regla "+item.name} value={rule.condition} onChange={e=>updateRule(item.id,{condition:e.target.value as MacroRule["condition"]})}>
     <option value="rising">Sube vs dato anterior</option><option value="falling">Baja vs dato anterior</option>
     <option value="above">Valor superior al umbral</option><option value="below">Valor inferior al umbral</option>
    </select>
    <input type="number" aria-label={"Retardo de publicación "+item.name} value={rule.min_release_lag_days} min={0} max={60} onChange={e=>updateRule(item.id,{min_release_lag_days:Math.min(60,Math.max(0,Number(e.target.value)||0))})}/>
    {(rule.condition==="above"||rule.condition==="below")&&<div className="tq-macro-threshold"><label>Umbral <input aria-label={"Umbral "+item.name} type="number" step="any" value={rule.threshold} onChange={e=>updateRule(item.id,{threshold:Number(e.target.value)||0})}/></label></div>}
   </div>})}
  </div>}
  {total===0&&<div className="tq-no-indicators"><SlidersHorizontal size={25}/><strong>{category==="macro"?"No has agregado variables macroeconómicas":"Sin elementos de esta categoría"}</strong><p>{category==="macro"?"Elige las series que quieras estudiar y deja preparadas sus reglas históricas.":"Abre el catálogo para agregar una señal disponible."}</p><button onClick={()=>setOpen(true)}><Plus size={15}/> Agregar {category==="macro"?"variable":"señal"}</button></div>}
  {hasSituation&&category==="situation"&&<div className="tq-catalog-session-box">
   <div className="tq-catalog-session-heading"><Clock3 size={17}/><div><strong>Zona horaria del CSV</strong><p>Necesaria para interpretar Londres, Tokio y PDH/PDL sin anticipar niveles.</p></div></div>
   <label>Zona de origen <select value={sourceTimezone} onChange={e=>onTimezone(e.target.value)}>{ZONES.map(([v,label])=><option key={v} value={v}>{label}</option>)}</select></label>
   <div className="tq-session-hours"><span><MapPin size={14}/> Londres 08:00–16:00 (local)</span><span><MapPin size={14}/> Tokio 09:00–17:00 (local)</span></div>
   <p>Se consideran barridas después del cierre de la sesión: mecha supera el nivel y la vela cierra dentro. Solo M1–H1; la señal se evalúa con velas cerradas y entrada en la apertura siguiente.</p>
  </div>}
  {category==="macro"&&<div className="tq-macro-disclosure"><Info size={18}/><span><strong>Fuente histórica aún no conectada.</strong> Las reglas seleccionadas se guardan en esta sesión, pero no forman parte del backtest. Para ejecutarlas se necesitan series con fecha real de publicación, revisiones históricas y controles de disponibilidad (point-in-time). Los retardo(s) configurados no sustituyen esos datos.</span></div>}
  {category!=="macro"&&<div className="tq-catalog-stats"><span>Espacio de parámetros de señales implementadas (referencial):</span><strong>{format(paramSpace)}</strong></div>}
  {invalid&&<div className="tq-indicator-error" role="alert">Revisa límites y pasos de cada parámetro; el mínimo debe ser menor o igual que el máximo.</div>}
  <div className="tq-catalog-science"><ShieldCheck size={17}/><span>Las señales marcadas como disponibles están implementadas en el motor científico. Las demás son referencias del catálogo, no resultados de backtesting. No se fabricarán datos macroeconómicos.</span></div>
 </div>;
}
