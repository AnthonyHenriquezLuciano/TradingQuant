"use client";
import {useState} from "react";
import {CircleHelp,Plus,Trash2,SlidersHorizontal,ShieldAlert,WifiOff} from "lucide-react";
export type CostRow={
 symbol:string;spread_pips:number;commission_roundtrip_usd:number;
 slippage_pips:number;swap_long_usd:number;swap_short_usd:number;
 pip_size:number;contract_size:number;quote_to_usd:number;hold_days_estimate:number;
};
export type CostSettings={
 template:"generic"|"custom";auto_mt5:false;
 selected_symbol:string;use_in_backtest:boolean;
 instruments:CostRow[]
};
export const BASE_COSTS:CostRow[]=[
 {symbol:"XAUUSD",spread_pips:2.5,commission_roundtrip_usd:7,slippage_pips:.5,swap_long_usd:-5,swap_short_usd:2,pip_size:.1,contract_size:100,quote_to_usd:1,hold_days_estimate:0},
 {symbol:"EURUSD",spread_pips:.8,commission_roundtrip_usd:7,slippage_pips:.2,swap_long_usd:-3,swap_short_usd:1,pip_size:.0001,contract_size:100000,quote_to_usd:1,hold_days_estimate:0},
 {symbol:"USDJPY",spread_pips:1.2,commission_roundtrip_usd:7,slippage_pips:.3,swap_long_usd:0,swap_short_usd:0,pip_size:.01,contract_size:100000,quote_to_usd:.0067,hold_days_estimate:0},
 {symbol:"NAS100",spread_pips:1.8,commission_roundtrip_usd:0,slippage_pips:.5,swap_long_usd:0,swap_short_usd:0,pip_size:1,contract_size:1,quote_to_usd:1,hold_days_estimate:0},
 {symbol:"USDCAD",spread_pips:1.5,commission_roundtrip_usd:7,slippage_pips:.3,swap_long_usd:0,swap_short_usd:0,pip_size:.0001,contract_size:100000,quote_to_usd:.73,hold_days_estimate:0}
];
export const DEFAULT_COSTS:CostSettings={template:"generic",auto_mt5:false,selected_symbol:"XAUUSD",use_in_backtest:false,instruments:BASE_COSTS};
type Props={value:CostSettings;onChange:(next:CostSettings)=>void;symbol:string;fallbackBps:number;onFallbackChange:(next:number)=>void};
export function CostsConfig({value,onChange,symbol,fallbackBps,onFallbackChange}:Props){
 const c={...DEFAULT_COSTS,...value};
 const [editing,setEditing]=useState(false);
 const [showHelp,setShowHelp]=useState(false);
 const [newSymbol,setNewSymbol]=useState("");
 const set=(patch:Partial<CostSettings>)=>onChange({...c,...patch});
 const rows=c.instruments||BASE_COSTS;
 const current=rows.find(r=>r.symbol.toUpperCase()===symbol.toUpperCase());
 const fmt=(n:number)=>new Intl.NumberFormat("es-DO",{maximumFractionDigits:4}).format(n);
 const update=(sym:string,key:keyof CostRow,v:string|number)=>{
  set({template:"custom",instruments:rows.map(r=>r.symbol===sym?{...r,[key]:v}:r)});
 };
 return <div className="tq-research">
  <div className="tq-research-intro"><span>LABORATORIO / EJECUCIÓN</span><h2>Costes de trading</h2><p>Plantillas editables de spread, comisión, slippage y swap por instrumento. MT5 permitirá recuperar valores del broker automáticamente más adelante.</p></div>
  <section className="tq-research-card">
   <div className="tq-cost-header">
    <label>Plantilla de costes<select value={c.template} onChange={e=>set({template:e.target.value as CostSettings["template"],instruments:e.target.value==="generic"?BASE_COSTS:rows})}><option value="generic">Genérico (ECN) — ilustrativo</option><option value="custom">Mi catálogo personalizado</option></select></label>
    <button onClick={()=>setEditing(s=>!s)} className="tq-research-expand"><SlidersHorizontal size={15}/> {editing?"Cerrar editor":"Gestionar plantillas"}</button>
    <button title="Información" className="tq-cost-help" onClick={()=>setShowHelp(s=>!s)}><CircleHelp size={16}/></button>
   </div>
   {showHelp&&<p className="tq-research-note">Los valores de ejemplo no representan cotizaciones reales ni condiciones del broker. Para calcular correctamente el coste, ingresa tamaño de pip, contrato y conversión de moneda de cotización a USD. Swap se aproxima por duración media; no reproduce triples swaps ni cambios de tarifa.</p>}
   <div className="tq-research-note"><WifiOff size={16}/> <strong>Sin conexión MT5.</strong> Sincronización automática de especificaciones, spread, comisiones, swap y cotización: <strong>Próximamente.</strong></div>
   <label className="tq-adv-field tq-cost-fallback"><span>Coste genérico round-trip, cuando catálogo está desactivado (bps)</span><input type="number" min={0} max={100} step={.1} value={fallbackBps} onChange={e=>onFallbackChange(Math.max(0,Math.min(100,Number(e.target.value))))}/></label>
   <label className="tq-cost-apply"><input type="checkbox" checked={c.use_in_backtest} onChange={e=>set({use_in_backtest:e.target.checked})}/><span>Aplicar el catálogo al backtest. Desactivado: conserva el coste genérico del laboratorio ({fmt(fallbackBps)} bps por operación).</span></label>
   <div className="tq-cost-table-wrap"><table className="tq-cost-table"><thead><tr><th>Instrumento</th><th>Spread (pips)</th><th>Comisión USD / lote ida y vuelta</th><th>Slippage (pips)</th><th>Swap L USD/lote/día</th><th>Swap S USD/lote/día</th><th></th></tr></thead><tbody>
    {rows.map(r=><tr key={r.symbol}><td><strong>{r.symbol}</strong></td>{(["spread_pips","commission_roundtrip_usd","slippage_pips","swap_long_usd","swap_short_usd"] as const).map(k=><td key={k}>{editing?<input type="number" step={.01} min={k.startsWith("swap")?undefined:0} value={r[k]} onChange={e=>update(r.symbol,k,Number(e.target.value))}/>:fmt(r[k])}</td>)}<td>{editing&&<button title={"Eliminar "+r.symbol} onClick={()=>set({template:"custom",instruments:rows.filter(x=>x.symbol!==r.symbol)})}><Trash2 size={15}/></button>}</td></tr>)}
   </tbody></table></div>
   {editing&&<>
     <div className="tq-cost-add"><input placeholder="Símbolo, ej. GBPUSD" value={newSymbol} onChange={e=>setNewSymbol(e.target.value.toUpperCase().replace(/[^A-Z0-9._-]/g,"").slice(0,24))}/><button disabled={!newSymbol||rows.some(r=>r.symbol===newSymbol)} onClick={()=>{set({template:"custom",instruments:[...rows,{...BASE_COSTS[1],symbol:newSymbol}]});setNewSymbol("")}}><Plus size={15}/> Añadir símbolo</button></div>
     <h3>Especificaciones de contratos (necesarias para convertir a bps)</h3>
     <div className="tq-cost-table-wrap"><table className="tq-cost-table"><thead><tr><th>Instrumento</th><th>Tamaño pip</th><th>Contrato por lote</th><th>1 divisa cotizada en USD</th><th>Días medios de financiación</th></tr></thead><tbody>{rows.map(r=><tr key={r.symbol}><td>{r.symbol}</td>{(["pip_size","contract_size","quote_to_usd","hold_days_estimate"] as const).map(k=><td key={k}><input type="number" step={k==="hold_days_estimate"?.25:".000001"} min={0} value={r[k]} onChange={e=>update(r.symbol,k,Number(e.target.value))}/></td>)}</tr>)}</tbody></table></div>
   </>}
   <div className="tq-research-note"><ShieldAlert size={16}/> Los costes se expresan como estimación de ida/vuelta en puntos básicos sobre el nocional, evaluada a partir del precio de entrada de cada posición. El swap usa días de financiación estimados, no el tiempo real de tenencia por trade. Para instrumentos cuyo pip, contrato o tipo de cambio no conoces, deja desactivado el catálogo y usa costes bps explícitos.</div>
   {!current&&c.use_in_backtest&&<div className="tq-cost-warning">El instrumento {symbol} no está en el catálogo. Añádelo o desactiva la aplicación de costes antes de explorar.</div>}
  </section>
 </div>;
}
