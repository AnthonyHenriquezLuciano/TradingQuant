"use client";
import {Info,ShieldCheck} from "lucide-react";
export type QualitySettings={
 min_sharpe:number;max_drawdown_pct:number;min_win_rate_pct:number;min_dsr:number;
 min_trades:number;min_frequency_unit:"auto"|"day"|"week"|"month";
 max_trades_per_day:number;
};
export const DEFAULT_QUALITY:QualitySettings={
 min_sharpe:1.2,max_drawdown_pct:15,min_win_rate_pct:50,min_dsr:0,
 min_trades:0,min_frequency_unit:"auto",max_trades_per_day:0
};
type Props={value:QualitySettings;onChange:(v:QualitySettings)=>void};
export function QualityFilters({value,onChange}:Props){
 const c={...DEFAULT_QUALITY,...value};
 const set=<K extends keyof QualitySettings>(key:K,v:QualitySettings[K])=>onChange({...c,[key]:v});
 const sliders=[
  {key:"min_sharpe" as const,label:"Sharpe Ratio mínimo",max:4,step:.1,display:(v:number)=>v===0?"Off":v.toFixed(1)},
  {key:"max_drawdown_pct" as const,label:"Máx. drawdown",max:100,step:1,display:(v:number)=>v===100?"Sin límite":v.toFixed(0)+"%"},
  {key:"min_win_rate_pct" as const,label:"Win Rate mínimo",max:100,step:1,display:(v:number)=>v===0?"Off":v.toFixed(0)+"%"},
  {key:"min_dsr" as const,label:"DSR mínimo (anti-suerte)",max:1,step:.05,display:(v:number)=>v===0?"Off":v.toFixed(2)}
 ];
 return <div className="tq-research">
  <div className="tq-research-intro"><span>LABORATORIO / SELECCIÓN</span><h2>Filtros de calidad</h2><p>Define las condiciones cuantitativas que debe cumplir cada estrategia para ser considerada candidata robusta.</p></div>
  <section className="tq-research-card">
   {sliders.map(sl=><div className="tq-quality-slider" key={sl.key}><div><label htmlFor={"quality-"+sl.key}>{sl.label}</label><strong>{sl.display(c[sl.key])}</strong></div><input id={"quality-"+sl.key} type="range" min="0" max={sl.max} step={sl.step} value={c[sl.key]} onChange={e=>set(sl.key,Number(e.target.value))}/></div>)}
   <p className="tq-research-help"><Info size={15}/> DSR: probabilidad estimada de que el Sharpe observado supere el máximo esperado por seleccionar entre varios intentos. La aproximación utiliza rendimientos diarios realizados, asimetría, curtosis y el número de candidatos probados. No demuestra por sí sola una ventaja futura.</p>
  </section>
  <section className="tq-research-card"><h3>Frecuencia de operaciones</h3><p>Descarta estrategias con una muestra demasiado pequeña o con una frecuencia superior al límite. «Auto» usa el mínimo general de operaciones configurado en el laboratorio.</p>
   <div className="tq-quality-frequency">
    <label>Mínimo<div><input type="number" min={0} max={50000} step={1} value={c.min_trades||""} placeholder="Auto" onChange={e=>set("min_trades",Math.max(0,Math.min(50000,Number(e.target.value)||0)))}/><select value={c.min_frequency_unit} onChange={e=>set("min_frequency_unit",e.target.value as QualitySettings["min_frequency_unit"])}><option value="auto">Total / auto</option><option value="day">por día</option><option value="week">por semana</option><option value="month">por mes</option></select></div></label>
    <label>Máximo<div><input type="number" min={0} max={10000} step={1} value={c.max_trades_per_day||""} placeholder="Sin tope" onChange={e=>set("max_trades_per_day",Math.max(0,Math.min(10000,Number(e.target.value)||0)))}/><small>por día</small></div></label>
   </div>
   <div className="tq-research-note"><ShieldCheck size={15}/> Los umbrales se calculan sobre la muestra IS al clasificar candidatos y se comprueban nuevamente en OOS al presentar la validación. No se utiliza OOS para seleccionar parámetros.</div>
  </section>
 </div>;
}
