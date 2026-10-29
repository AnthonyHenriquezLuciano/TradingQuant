"use client";
import {useState} from "react";
import {Check,ChevronDown,Clock3,Info,ShieldCheck,SlidersHorizontal,SunMoon} from "lucide-react";

export type SessionKey="all_day"|"sydney"|"tokyo"|"london"|"new_york"|"tokyo_london"|"london_new_york"|"asian";
export type ScheduleSettings={
 sessions:SessionKey[];
 close_before_ny:boolean;
 close_before_weekend:boolean;
 no_friday_entries:boolean;
 avoid_monday_open:boolean;
 avoid_rollover:boolean;
};
export const DEFAULT_SCHEDULE:ScheduleSettings={
 sessions:["all_day"],close_before_ny:false,close_before_weekend:false,
 no_friday_entries:false,avoid_monday_open:false,avoid_rollover:false
};
type Session={id:SessionKey;name:string;start:number;end:number;color:string;short:string};
export const SESSIONS:Session[]=[
 {id:"sydney",name:"Sydney",start:21,end:6,color:"#8950b9",short:"21–06"},
 {id:"tokyo",name:"Tokio",start:0,end:9,color:"#b15d56",short:"00–09"},
 {id:"london",name:"Londres",start:7,end:16,color:"#5373bf",short:"07–16"},
 {id:"new_york",name:"Nueva York",start:12,end:21,color:"#548c79",short:"12–21"},
 {id:"tokyo_london",name:"Overlap Tokio–Londres",start:7,end:9,color:"#b67a45",short:"07–09"},
 {id:"london_new_york",name:"Overlap Londres–NY",start:12,end:16,color:"#ad933e",short:"12–16"},
 {id:"asian",name:"Sesión asiática",start:21,end:9,color:"#b75486",short:"21–09"},
];
const RULES=[
 {id:"close_before_ny",title:"Cerrar antes de NY close",desc:"Desde las 20:00 UTC, cerrar posiciones y bloquear nuevas entradas durante el resto del día."},
 {id:"close_before_weekend",title:"Cerrar antes del fin de semana",desc:"El viernes desde las 19:00 UTC, cerrar posiciones y bloquear nuevas entradas."},
 {id:"no_friday_entries",title:"No abrir trades los viernes",desc:"No abrir operaciones nuevas durante el viernes (00:00–24:00 UTC)."},
 {id:"avoid_monday_open",title:"No operar apertura del lunes",desc:"No abrir nuevas posiciones el lunes hasta las 01:00 UTC."},
 {id:"avoid_rollover",title:"Evitar hora de rollover",desc:"Bloquear nuevas entradas entre 20:55 y 21:10 UTC, también al cruzar de día."},
] as const;
type Props={value:ScheduleSettings;onChange:(v:ScheduleSettings)=>void;sourceTimezone:string;onTimezone:(tz:string)=>void};
const SOURCE_ZONES=[
 ["UTC","UTC"],["Europe/London","Europe/London"],["Europe/Athens","Europe/Athens (UTC+2/+3)"],
 ["America/New_York","America/New_York"],["America/Santo_Domingo","America/Santo_Domingo"],
 ["Asia/Tokyo","Asia/Tokyo"]
];
export function ScheduleConfig({value,onChange,sourceTimezone,onTimezone}:Props){
 const c={...DEFAULT_SCHEDULE,...value};const [details,setDetails]=useState(true);
 const selected:SessionKey[]=c.sessions?.length?c.sessions:["all_day"];
 function choose(id:SessionKey){
  if(id==="all_day"){onChange({...c,sessions:["all_day"]});return;}
  const current=selected.filter(s=>s!=="all_day");
  const next=current.includes(id)?current.filter(s=>s!==id):[...current,id];
  onChange({...c,sessions:next.length?next:["all_day"]});
 }
 return <div className="tq-hours">
  <div className="tq-hours-header"><div><div className="tq-capital-overline">LABORATORIO / CONTROL TEMPORAL</div><h3>Sesiones de trading</h3><p>Selecciona cuándo puede abrir operaciones el algoritmo.</p></div><span className="tq-hours-zone"><Clock3 size={15}/> Horarios UTC fijos</span></div>
  <div className="tq-hours-pills"><button className={selected.includes("all_day")?"active":""} onClick={()=>choose("all_day")}><span className="tq-hour-dot"/> 24 horas</button>{SESSIONS.map(s=><button key={s.id} className={selected.includes(s.id)?"active":""} onClick={()=>choose(s.id)}>{selected.includes(s.id)&&<span className="tq-hour-dot"/>}{s.name}<small>{s.short}</small></button>)}</div>
  <div className="tq-timeline" role="img" aria-label="Sesiones del mercado representadas en un gráfico de 00:00 a 24:00 UTC">
   <div className="tq-timeline-label"/><div className="tq-timeline-hours">{Array.from({length:24},(_,i)=><span key={i} style={{left:(i/24*100)+"%"}}>{String(i).padStart(2,"0")}</span>)}</div>
   {SESSIONS.map(s=><div className={"tq-timeline-row "+(selected.includes("all_day")||selected.includes(s.id)?"highlight":"")} key={s.id}>
    <span className="tq-timeline-name" style={{color:s.color}}>{s.name}</span><div className="tq-timeline-track">
      {(s.end>s.start?[[s.start,s.end]]:[[0,s.end],[s.start,24]]).map(([start,end],j)=>
       <span key={j} className="tq-timeline-bar" style={{left:start/24*100+"%",width:(end-start)/24*100+"%",background:s.color,opacity:selected.includes("all_day")||selected.includes(s.id)?0.9:0.32}}/>)}
    </div></div>)}
   <div className="tq-timeline-foot"><span>00:00</span><span>UTC · 24 horas</span><span>24:00</span></div>
  </div>
  <label className="tq-hours-timezone">Zona horaria del archivo CSV <select value={sourceTimezone} onChange={e=>onTimezone(e.target.value)}>{SOURCE_ZONES.map(([id,name])=><option value={id} key={id}>{name}</option>)}</select></label>
  <div className="tq-hours-notice"><Info size={16}/><p>La cuadrícula sigue <strong>ventanas fijas en UTC</strong>, tal como se muestran, sin desplazarlas automáticamente por el horario de verano de Londres o Nueva York. El motor convierte la zona horaria original del CSV a UTC antes de aplicar estos intervalos. Una sesión seleccionada limita las entradas, pero no cierra operaciones ya abiertas por sí sola.</p></div>
  <div className="tq-hours-restrictions">
   <button className="tq-hours-sectionhead" onClick={()=>setDetails(x=>!x)} aria-expanded={details}><span><ShieldCheck size={17}/> Reglas de cierre y restricciones</span><small>{RULES.filter(r=>c[r.id]).length} activas</small><ChevronDown size={17} className={details?"rotated":""}/></button>
   {details&&<div className="tq-hours-rules">{RULES.map(r=><label className="tq-hours-rule" key={r.id}>
     <input type="checkbox" checked={c[r.id]} onChange={e=>onChange({...c,[r.id]:e.target.checked})}/>
     <span><strong>{r.title}</strong><small>{r.desc}</small></span>
    </label>)}</div>}
  </div>
  <div className="tq-capital-note"><SunMoon size={17}/> El horario se aplica sobre velas históricas con marca temporal conocida. Las salidas forzadas se calculan en la primera apertura disponible después del corte; no se inventa una ejecución si faltan cotizaciones.</div>
 </div>;
}
