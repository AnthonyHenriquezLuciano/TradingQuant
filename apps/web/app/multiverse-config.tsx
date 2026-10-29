"use client";
import {useState} from "react";
import {Dices,Info,ShieldCheck,TriangleAlert} from "lucide-react";
export type MultiverseSettings={
 enabled:boolean;universes:50|100|250|500|1000;mix:"balanced"|"conservative"|"stress";
 top_n:number;regimes:1|2|3;validate_fat_tails:boolean;
 min_score:number;max_robust_drawdown_pct:number;
};
export const DEFAULT_MULTIVERSE:MultiverseSettings={
 enabled:false,universes:100,mix:"balanced",top_n:3,regimes:3,
 validate_fat_tails:true,min_score:60,max_robust_drawdown_pct:30
};
type Props={value:MultiverseSettings;onChange:(v:MultiverseSettings)=>void};
export function MultiverseConfig({value,onChange}:Props){
 const c={...DEFAULT_MULTIVERSE,...value};const set=(p:Partial<MultiverseSettings>)=>onChange({...c,...p});
 const [method,setMethod]=useState(false);
 const mixes=[
  {id:"balanced",name:"Balanceado",note:"Histórico 40% · Bootstrap 40% · Estrés de saltos 20%. Diversifica supuestos."},
  {id:"conservative",name:"Conservador",note:"Histórico 50% · Bootstrap 50%. Sin saltos artificiales."},
  {id:"stress",name:"Agresivo",note:"Histórico 20% · Bootstrap 40% · Estrés de saltos 40%. Somete a eventos adversos."}
 ] as const;
 return <div className="tq-research">
  <div className="tq-research-intro"><span>LABORATORIO / ESTRÉS DE MERCADO</span><h2>Multiverso — Robustez sintética</h2><p>Genera trayectorias OHLC sintéticas estadísticamente inspiradas en el mercado histórico y mide si las reglas sobreviven a diferentes escenarios.</p></div>
  <section className="tq-research-card">
   <div className="tq-research-switchrow"><div><strong>Activar pruebas Multiverso</strong><small>Se ejecutarán sobre las mejores estrategias al finalizar la búsqueda, antes de la selección final.</small></div><label className="tq-research-switch"><input type="checkbox" checked={c.enabled} onChange={e=>set({enabled:e.target.checked})}/><span/></label></div>
   <h3>Universos sintéticos por estrategia</h3>
   <div className="tq-choice-row">{([50,100,250,500,1000] as const).map(n=><button type="button" key={n} onClick={()=>set({universes:n})} className={c.universes===n?"active":""}>{n.toLocaleString("es-DO")}</button>)}</div>
   <p className="tq-research-hint">Más universos mejoran la precisión estadística del ensayo, pero incrementan significativamente el cálculo.</p>
   <h3>Mezcla de motores generadores</h3>
   <div className="tq-research-options">{mixes.map(m=><button key={m.id} className={c.mix===m.id?"active":""} onClick={()=>set({mix:m.id})}><strong>{m.name}</strong><small>{m.note}</small></button>)}</div>
   <div className="tq-research-slide"><div><label htmlFor="mv-top">Top-N estrategias a validar</label><strong>{c.top_n}</strong></div><input id="mv-top" type="range" min={1} max={10} step={1} value={c.top_n} onChange={e=>set({top_n:Number(e.target.value)})}/></div>
   <div className="tq-research-slide"><div><label htmlFor="mv-reg">Regímenes estimados</label><strong>{c.regimes}</strong></div><input id="mv-reg" type="range" min={1} max={3} step={1} value={c.regimes} onChange={e=>set({regimes:Number(e.target.value) as 1|2|3})}/></div>
   <p className="tq-research-hint">Se utiliza un modelo de estados ocultos (HMM gaussiano) para estimar regímenes de retornos, cuando la muestra permite un ajuste estable. Un único régimen elimina esa segmentación.</p>
   <div className="tq-research-switchrow tq-research-compact"><div><strong>Validar hechos estilizados</strong><small>Comprueba que el conjunto sintético preserve volatilidad agrupada, colas extremas y distribución de rendimientos del histórico.</small></div><label className="tq-research-switch"><input type="checkbox" checked={c.validate_fat_tails} onChange={e=>set({validate_fat_tails:e.target.checked})}/><span/></label></div>
   <div className="tq-research-fields">
    <label>Score mínimo de robustez (0–100)<input min={0} max={100} type="number" value={c.min_score} onChange={e=>set({min_score:Number(e.target.value)})}/></label>
    <label>Drawdown máximo P95 (%)<input min={1} max={100} type="number" value={c.max_robust_drawdown_pct} onChange={e=>set({max_robust_drawdown_pct:Number(e.target.value)})}/></label>
   </div>
  </section>
  <div className="tq-research-note"><TriangleAlert size={16}/> Los resultados de Multiverso son pruebas de estrés con escenarios hipotéticos, no probabilidades de mercado futuras. El motor no puede declarar haber replicado ticks reales, microestructura, spread dinámico ni toda la estructura de volatilidad del instrumento.</div>
  <button className="tq-research-expand" onClick={()=>setMethod(s=>!s)}><Info size={15}/> Detalles de metodología {method?"−":"+"}</button>
  {method&&<div className="tq-research-note"><Dices size={16}/> Cada escenario conserva precios positivos, continuidad OHLC y volúmenes de rangos históricos; los modos de bootstrap y estrés alteran la secuencia de retornos sin mezclar información OOS en la selección. Los patrones de series sintéticas no garantizan reproducción del proceso de mercado original.</div>}
 </div>;
}
