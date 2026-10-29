"use client";
import {useState} from "react";
import {CalendarClock,ChevronDown,Info,Shuffle} from "lucide-react";
export type WalkForwardSettings={
 enabled:boolean;test_fraction:1|2|3|4|6;mode:"pure"|"reopt";
 top_n:number;min_efficiency:number;min_pass_rate_pct:number;min_oos_sharpe:number;
 rolling_windows:number;min_training_bars:number
};
export const DEFAULT_WALK_FORWARD:WalkForwardSettings={
 enabled:false,test_fraction:4,mode:"pure",
 top_n:20,min_efficiency:.5,min_pass_rate_pct:60,min_oos_sharpe:.5,
 rolling_windows:4,min_training_bars:250
};
type Props={value:WalkForwardSettings;onChange:(v:WalkForwardSettings)=>void;periodLabel?:string};
export function WalkForwardConfig({value,onChange,periodLabel}:Props){
 const c={...DEFAULT_WALK_FORWARD,...value};
 const [advanced,setAdvanced]=useState(false);
 const set=(part:Partial<WalkForwardSettings>)=>onChange({...c,...part});
 return <div className="tq-research">
  <div className="tq-research-intro"><span>LABORATORIO / VALIDACIÓN TEMPORAL</span><h2>Walk-Forward — Validación de robustez</h2><p>Valida las estrategias sobre ventanas cronológicas sucesivas para observar deterioro fuera del tramo de ajuste.</p></div>
  <section className="tq-research-card">
   <div className="tq-research-switchrow"><div><strong>Activar Walk-Forward</strong><small>Validación secundaria con ventanas sin solapamiento en evaluación.</small></div><label className="tq-research-switch"><input type="checkbox" checked={c.enabled} onChange={e=>set({enabled:e.target.checked})}/><span/></label></div>
   <div className="tq-wf-period">Periodo seleccionado: <strong>{periodLabel||"Se calculará según las fechas y datos del CSV"}</strong></div>
   <h3>Tamaño de cada ventana de test</h3>
   <div className="tq-choice-row">{([12,8,6,4,3,2] as const).map(n=><button type="button" key={n} className={c.test_fraction===n?"active":""} onClick={()=>set({test_fraction:n})}>1/{n}</button>)}</div>
   <h3>Modo de validación</h3>
   <div className="tq-research-options">
    <button type="button" className={c.mode==="pure"?"active":""} onClick={()=>set({mode:"pure"})}><strong>Validación pura</strong><small>Mantiene exactamente los parámetros del candidato en cada tramo y mide su estabilidad temporal.</small></button>
    <button type="button" className={c.mode==="reopt"?"active":""} onClick={()=>set({mode:"reopt"})}><strong>Re-optimización por ventana</strong><small>Reclasifica, en cada corte, el pool de candidatos usando solo el histórico anterior al nuevo test. Es una re-selección temporal, no evolución genética desde cero.</small></button>
   </div>
   <button className="tq-research-expand" onClick={()=>setAdvanced(v=>!v)}><ChevronDown size={15} className={advanced?"rotated":""}/> Avanzado</button>
   {advanced&&<div className="tq-research-fields">
    <label>Top N estrategias a validar<input type="number" min={1} max={30} value={c.top_n} onChange={e=>set({top_n:Number(e.target.value)})}/></label>
    <label>Ventanas rolling<input type="number" min={2} max={12} value={c.rolling_windows} onChange={e=>set({rolling_windows:Number(e.target.value)})}/></label>
    <label>Mínimo de velas para entrenar<input type="number" min={100} max={100000} step={50} value={c.min_training_bars} onChange={e=>set({min_training_bars:Number(e.target.value)})}/></label>
   </div>}
   <h3>Filtros — solo conserva estrategias que cumplan</h3>
   <div className="tq-research-fields">
    <label>WFE mínimo <span title="Rendimiento OOS dividido por rendimiento IS, con costes. Valores negativos no aprueban.">ⓘ</span><input type="number" min={0} max={3} step={.05} value={c.min_efficiency} onChange={e=>set({min_efficiency:Number(e.target.value)})}/></label>
    <label>Pass Rate mínimo (%) <span title="Fracción de ventanas que cumplen los mínimos configurados.">ⓘ</span><input type="number" min={0} max={100} step={1} value={c.min_pass_rate_pct} onChange={e=>set({min_pass_rate_pct:Number(e.target.value)})}/></label>
    <label>Sharpe OOS mínimo <span title="Sharpe anualizado en retornos realizados para las ventanas de validación.">ⓘ</span><input type="number" min={-5} max={10} step={.1} value={c.min_oos_sharpe} onChange={e=>set({min_oos_sharpe:Number(e.target.value)})}/></label>
   </div>
  </section>
  <div className="tq-research-note"><CalendarClock size={17}/> Los resultados se calculan durante la exploración en tramos de datos históricos, no en segundo plano tras cerrarla. En modo re-optimización se reordena el conjunto previamente generado; no equivale a volver a generar miles de reglas nuevas en cada ventana.</div>
 </div>;
}
