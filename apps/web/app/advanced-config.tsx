"use client";
import {useState} from "react";
import {ArrowUpRight,ArrowDownRight,Info,Layers3,ShieldCheck,SlidersHorizontal,TrendingUp,TriangleAlert} from "lucide-react";

export type Unit="atr"|"r"|"percent";
export type AdvancedSettings={
 entry_modes:("market"|"stop"|"limit")[];
 stop_lookback:number;order_expiry_bars:number;limit_offset_atr:number;
 fixed_rr_enabled:boolean;fixed_rr:number;
 variable_risk_enabled:boolean;variable_risk_mode:"anti_martingale"|"martingale";
 risk_multiplier:number;risk_max_levels:number;risk_reset_on_win:boolean;
 be_enabled:boolean;be_unit:Unit;be_trigger:number;be_offset_pips:number;pip_size:number;
 trailing_enabled:boolean;trailing_activation_unit:Unit;trailing_activation:number;
 trailing_distance_unit:Unit;trailing_distance:number;
 dca_enabled:boolean;dca_levels:number;dca_size_multiplier:number;
 dca_spacing_unit:Unit;dca_spacing:number;
 pyramid_enabled:boolean;pyramid_levels:number;pyramid_size_multiplier:number;
 pyramid_spacing_unit:Unit;pyramid_spacing:number;
 sl_tp_from_average:boolean;
};
export const DEFAULT_ADVANCED:AdvancedSettings={
 entry_modes:["market"],stop_lookback:5,order_expiry_bars:3,limit_offset_atr:.5,
 fixed_rr_enabled:false,fixed_rr:2,
 variable_risk_enabled:false,variable_risk_mode:"anti_martingale",
 risk_multiplier:1.5,risk_max_levels:5,risk_reset_on_win:true,
 be_enabled:false,be_unit:"atr",be_trigger:1,be_offset_pips:0,pip_size:0,
 trailing_enabled:false,trailing_activation_unit:"atr",trailing_activation:1.5,
 trailing_distance_unit:"atr",trailing_distance:1,
 dca_enabled:false,dca_levels:3,dca_size_multiplier:1,
 dca_spacing_unit:"atr",dca_spacing:1,
 pyramid_enabled:false,pyramid_levels:3,pyramid_size_multiplier:1,
 pyramid_spacing_unit:"atr",pyramid_spacing:1,sl_tp_from_average:true
};
type Props={value:AdvancedSettings;onChange:(next:AdvancedSettings)=>void;currentCapitalBE:boolean;currentCapitalTrailing:boolean};
const options:{id:"market"|"stop"|"limit";name:string;desc:string}[]=[
 {id:"market",name:"Mercado",desc:"Abre en la siguiente apertura de vela después de la señal."},
 {id:"stop",name:"Stop (ruptura)",desc:"Orden al romper el máximo/mínimo confirmado de barras anteriores."},
 {id:"limit",name:"Limit (retroceso)",desc:"Espera un retroceso favorable para entrar. No fuerza una ejecución."}
];
const U=[{value:"atr",label:"ATR"},{value:"r",label:"R (distancia SL)"},{value:"percent",label:"% del precio"}] as const;
function NumberField({label,value,onChange,min=0,max=1000,step=.1,suffix,help}:{
 label:string;value:number;onChange:(v:number)=>void;min?:number;max?:number;step?:number;suffix?:string;help?:string
}){return <label className="tq-adv-field"><span>{label}{help&&<span title={help} className="tq-adv-tip"><Info size={13}/></span>}</span><div><input type="number" min={min} max={max} step={step} value={value} onChange={e=>{const n=Number(e.target.value);if(Number.isFinite(n))onChange(n)}}/>{suffix&&<small>{suffix}</small>}</div></label>}
function UnitField({label,value,onChange}:{label:string;value:Unit;onChange:(v:Unit)=>void}){return <label className="tq-adv-field"><span>{label}</span><select value={value} onChange={e=>onChange(e.target.value as Unit)}>{U.map(u=><option key={u.value} value={u.value}>{u.label}</option>)}</select></label>}
function Switch({checked,onChange}:{checked:boolean;onChange:(v:boolean)=>void}){return <label className="tq-adv-switch"><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)}/><span/></label>}
function Block({title,description,enabled,onToggle,children}:{title:string;description:string;enabled:boolean;onToggle:(v:boolean)=>void;children?:React.ReactNode}){
 return <section className={"tq-adv-block "+(enabled?"is-enabled":"")}><div className="tq-adv-block-top"><div><strong>{title}</strong><p>{description}</p></div><Switch checked={enabled} onChange={onToggle}/></div>{enabled&&children&&<div className="tq-adv-block-details">{children}</div>}</section>
}
export function AdvancedConfig({value,onChange,currentCapitalBE,currentCapitalTrailing}:Props){
 const v={...DEFAULT_ADVANCED,...value};
 const set=(patch:Partial<AdvancedSettings>)=>onChange({...v,...patch});
 const toggleMode=(m:"market"|"stop"|"limit")=>{
  const next=v.entry_modes.includes(m)?v.entry_modes.filter(x=>x!==m):[...v.entry_modes,m];
  if(next.length)set({entry_modes:next});
 };
 const [showInfo,setShowInfo]=useState(false);
 return <div className="tq-advanced">
  <div className="tq-adv-intro"><span>LABORATORIO / MODIFICADORES</span><h2>Modificadores avanzados</h2><p>Ajustes adicionales aplicados sobre el modo de salida elegido. Todos los bloques son opcionales, con configuración y ejecución independientes.</p></div>
  <section className="tq-adv-block is-enabled">
   <div className="tq-adv-block-top"><div><strong>Tipo de entrada</strong><p>Selecciona una o varias formas de entrar. Cuando hay varios modos, el explorador prueba variantes distintas en cada candidato, sin mezclarlas dentro de un mismo trade.</p></div></div>
   <div className="tq-adv-entry-grid">{options.map(o=><label key={o.id} className={"tq-adv-entry "+(v.entry_modes.includes(o.id)?"selected":"")}>
     <input type="checkbox" checked={v.entry_modes.includes(o.id)} onChange={()=>toggleMode(o.id)}/>
     <span><strong>{o.name}</strong><small>{o.desc}</small></span></label>)}</div>
   {v.entry_modes.some(x=>x!=="market")&&<div className="tq-adv-grid">
    {v.entry_modes.includes("stop")&&<NumberField label="Barras previas para ruptura" value={v.stop_lookback} min={2} max={100} step={1} onChange={x=>set({stop_lookback:x})}/>}
    {v.entry_modes.includes("limit")&&<NumberField label="Distancia del retroceso" value={v.limit_offset_atr} min={.1} max={10} step={.1} suffix="× ATR" onChange={x=>set({limit_offset_atr:x})}/>}
    <NumberField label="Caducidad de orden pendiente" value={v.order_expiry_bars} min={1} max={100} step={1} suffix="velas" onChange={x=>set({order_expiry_bars:x})}/>
   </div>}
   <p className="tq-adv-caption">Stop y Limit se ejecutan a partir de la barra posterior a la señal; si se llenan intrabar, el SL/TP se evalúa desde la próxima barra por prudencia.</p>
  </section>
  <Block title="Risk–Reward fijo" description="Sobrescribe el TP del modo de salida seleccionado para que la distancia del TP sea un múltiplo de la distancia inicial del SL." enabled={v.fixed_rr_enabled} onToggle={x=>set({fixed_rr_enabled:x})}>
   <NumberField label="Ratio recompensa/riesgo" value={v.fixed_rr} min={.1} max={20} step={.1} suffix="R" onChange={x=>set({fixed_rr:x})}/>
  </Block>
  <Block title="Riesgo variable (multiplicador)" description="Modifica el presupuesto total de riesgo según la racha de operaciones cerradas. El capital de las entradas adicionales comparte el mismo presupuesto." enabled={v.variable_risk_enabled} onToggle={x=>set({variable_risk_enabled:x})}>
   <div className="tq-adv-grid">
    <label className="tq-adv-field"><span>Modo</span><select value={v.variable_risk_mode} onChange={e=>set({variable_risk_mode:e.target.value as AdvancedSettings["variable_risk_mode"]})}>
     <option value="anti_martingale">Anti-martingala (aumenta tras ganar)</option>
     <option value="martingale">Martingala (aumenta tras perder)</option>
    </select></label>
    <NumberField label="Multiplicador" value={v.risk_multiplier} min={1} max={3} step={.1} onChange={x=>set({risk_multiplier:x})}/>
    <NumberField label="Máximo de niveles" value={v.risk_max_levels} min={1} max={10} step={1} onChange={x=>set({risk_max_levels:x})}/>
    <label className="tq-adv-field tq-adv-inline"><span>Reiniciar al ganar</span><Switch checked={v.risk_reset_on_win} onChange={x=>set({risk_reset_on_win:x})}/></label>
   </div>
   <div className="tq-adv-notice"><TriangleAlert size={15}/> La martingala incrementa rápidamente el riesgo. El motor limita el riesgo acumulado a 2% del capital de referencia por operación compuesta.</div>
  </Block>
  <Block title="Break-even (modificador)" description="Cuando el beneficio alcanza el umbral, mueve el SL hacia la entrada con un offset opcional. Sustituye al break-even básico de Gestión de capital." enabled={v.be_enabled} onToggle={x=>set({be_enabled:x})}>
   {currentCapitalBE&&<p className="tq-adv-conflict">El break-even avanzado tiene prioridad sobre el break-even de Gestión de capital.</p>}
   <div className="tq-adv-grid"><UnitField label="Unidad de activación" value={v.be_unit} onChange={x=>set({be_unit:x})}/>
    <NumberField label="Umbral de beneficio" min={.05} max={20} value={v.be_trigger} onChange={x=>set({be_trigger:x})}/>
    <NumberField label="Offset (pips)" min={0} max={1000} step={.1} value={v.be_offset_pips} onChange={x=>set({be_offset_pips:x})}/>
    {v.be_offset_pips>0&&<NumberField label="Tamaño de pip del símbolo" min={.00000001} max={1000} step={.00001} value={v.pip_size} onChange={x=>set({pip_size:x})} help="Ej.: EURUSD 0.0001, USDJPY 0.01. Verifica la especificación de tu broker."/>}
   </div>
  </Block>
  <Block title="Trailing Stop (modificador)" description="Se activa a partir de un beneficio definido y sigue al precio manteniendo una distancia. Tiene prioridad sobre el trailing básico." enabled={v.trailing_enabled} onToggle={x=>set({trailing_enabled:x})}>
   {currentCapitalTrailing&&<p className="tq-adv-conflict">El trailing avanzado reemplaza al trailing de Gestión de capital.</p>}
   <div className="tq-adv-grid"><div className="tq-adv-mini">
     <strong>Activación</strong><UnitField label="Unidad" value={v.trailing_activation_unit} onChange={x=>set({trailing_activation_unit:x})}/><NumberField label="Valor" value={v.trailing_activation} min={.05} max={20} onChange={x=>set({trailing_activation:x})}/>
    </div><div className="tq-adv-mini"><strong>Distancia trail</strong><UnitField label="Unidad" value={v.trailing_distance_unit} onChange={x=>set({trailing_distance_unit:x})}/><NumberField label="Valor" value={v.trailing_distance} min={.05} max={20} onChange={x=>set({trailing_distance:x})}/></div></div>
  </Block>
  <Block title="Operaciones adicionales (DCA / Pirámide)" description="Incorpora posiciones escalonadas sobre un mismo trade. El DCA promedia en contra; la pirámide agrega a favor. Ambos pueden combinarse bajo un presupuesto único de riesgo." enabled={v.dca_enabled||v.pyramid_enabled} onToggle={x=>set(x?{dca_enabled:true}:{dca_enabled:false,pyramid_enabled:false})}>
   <div className="tq-adv-scaling">
    <div><label className="tq-adv-subtoggle"><Switch checked={v.dca_enabled} onChange={x=>set({dca_enabled:x})}/><strong>Escalera DCA (en contra)</strong></label>
     <p>Añade una pata cada vez que el precio evoluciona en contra del último nivel, sin superar el stop actual.</p>
     {v.dca_enabled&&<div className="tq-adv-grid">
      <NumberField label="Niveles (incluye entrada inicial)" min={2} max={8} step={1} value={v.dca_levels} onChange={x=>set({dca_levels:x})}/>
      <NumberField label="Multiplicador de tamaño" min={.25} max={3} value={v.dca_size_multiplier} onChange={x=>set({dca_size_multiplier:x})}/>
      <UnitField label="Unidad de espaciado" value={v.dca_spacing_unit} onChange={x=>set({dca_spacing_unit:x})}/>
      <NumberField label="Espaciado" min={.1} max={10} value={v.dca_spacing} onChange={x=>set({dca_spacing:x})}/>
     </div>}
    </div>
    <div><label className="tq-adv-subtoggle"><Switch checked={v.pyramid_enabled} onChange={x=>set({pyramid_enabled:x})}/><strong>Escalera pirámide (a favor)</strong></label>
     <p>Añade una pata cuando el precio progresa favorablemente desde el último nivel.</p>
     {v.pyramid_enabled&&<div className="tq-adv-grid">
      <NumberField label="Niveles (incluye entrada inicial)" min={2} max={8} step={1} value={v.pyramid_levels} onChange={x=>set({pyramid_levels:x})}/>
      <NumberField label="Multiplicador de tamaño" min={.25} max={3} value={v.pyramid_size_multiplier} onChange={x=>set({pyramid_size_multiplier:x})}/>
      <UnitField label="Unidad de espaciado" value={v.pyramid_spacing_unit} onChange={x=>set({pyramid_spacing_unit:x})}/>
      <NumberField label="Espaciado" min={.1} max={10} value={v.pyramid_spacing} onChange={x=>set({pyramid_spacing:x})}/>
     </div>}
    </div>
    <label className="tq-adv-subtoggle"><Switch checked={v.sl_tp_from_average} onChange={x=>set({sl_tp_from_average:x})}/><strong>TP desde precio promedio ponderado</strong></label>
    <p>El stop nunca se aleja del nivel inicial para aumentar exposición. El TP puede recalcularse desde el promedio, conservando el SL y la distancia original de riesgo del conjunto.</p>
   </div>
   <div className="tq-adv-notice"><ShieldCheck size={15}/> Se reserva capacidad para todas las patas al abrir el trade. No se permite aumentar la pérdida máxima planificada por encima del presupuesto total de riesgo de la operación.</div>
  </Block>
  <div className="tq-adv-bottom"><button type="button" onClick={()=>setShowInfo(x=>!x)}><Info size={15}/> Metodología y limitaciones</button>{showInfo&&<p>Se emplea OHLC con stop primero en barras ambiguas, señales de vela confirmada, entradas pendientes con caducidad, y actualizaciones de stop al cerrar la vela. No es una emulación exacta de profundidad de mercado, órdenes del broker, latencia ni margen. Los modos DCA/pirámide no duplican la cuenta de operaciones para los límites diarios.</p>}</div>
 </div>;
}
