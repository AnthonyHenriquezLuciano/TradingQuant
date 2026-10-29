"use client";
import {useState} from "react";
import {Plus,Trash2,ShieldCheck,Info,ChartColumnIncreasing,Timer,Landmark,Scale,SlidersHorizontal,ChevronDown,TriangleAlert} from "lucide-react";

export type FundingPhase={target_pct:number;max_days:number;min_days:number;min_profit_day_pct:number};
export type FundingSettings={
 enabled:boolean;preset:string;phases:FundingPhase[];
 daily_loss_pct:number;daily_loss_basis:"previous_close"|"initial";
 total_loss_pct:number;total_loss_mode:"static"|"trailing_eod";
 trailing_lock_initial:boolean;
 consistency_mode:"none"|"best_day_total"|"best_day_target";consistency_max_pct:number;
 min_pass_rate_pct:number;pass_day_percentile:10|20|25|50|75|80|90|95;
 max_pass_days_percentile:number;simulations:number;bootstrap_block_days:number;
};
export const DEFAULT_FUNDING:FundingSettings={
 enabled:false,preset:"custom",
 phases:[{target_pct:8,max_days:120,min_days:0,min_profit_day_pct:0},
         {target_pct:5,max_days:120,min_days:0,min_profit_day_pct:0}],
 daily_loss_pct:3,daily_loss_basis:"previous_close",total_loss_pct:10,
 total_loss_mode:"static",trailing_lock_initial:true,
 consistency_mode:"none",consistency_max_pct:50,
 min_pass_rate_pct:0,pass_day_percentile:20,max_pass_days_percentile:0,
 simulations:128,bootstrap_block_days:1,
};
const phase=(target:number,minimum:number,dayProfit=0):FundingPhase=>({
 target_pct:target,max_days:120,min_days:minimum,min_profit_day_pct:dayProfit
});
type Preset={id:string;name:string;notice:string;kind:"verified"|"template";update:Partial<FundingSettings>};
const PRESETS:Preset[]=[
 {id:"ftmo",name:"FTMO 2-Step",kind:"verified",notice:"FTMO 2-Step (10% / 5%, DD 5% diario y 10% total, 4 días): verificar condiciones vigentes y horario CE(S)T.",update:{phases:[phase(10,4),phase(5,4)],daily_loss_pct:5,total_loss_pct:10,total_loss_mode:"static",daily_loss_basis:"previous_close"}},
 {id:"ftmo_swing",name:"FTMO Swing (plantilla)",kind:"template",notice:"Plantilla FTMO Swing: las condiciones de holding y condiciones particulares NO se modelan. Revisar contrato.",update:{phases:[phase(10,4),phase(5,4)],daily_loss_pct:5,total_loss_pct:10}},
 {id:"fundingpips",name:"FundingPips 2-Step Standard",kind:"verified",notice:"Referencia: 8%/5%, pérdida máxima 10% estática; daily puede ser 3% o 5% según producto/add-on. Se propone 5% y 3 días por fase, editable.",update:{phases:[phase(8,3),phase(5,3)],daily_loss_pct:5,total_loss_pct:10,total_loss_mode:"static",daily_loss_basis:"previous_close"}},
 {id:"the5ers",name:"The5ers High Stakes",kind:"verified",notice:"Referencia High Stakes Classic: 10%/5%, pérdida diaria 5%, máxima 10%, 3 días rentables por fase. Otros planes pueden variar.",update:{phases:[phase(10,3,.01),phase(5,3,.01)],daily_loss_pct:5,total_loss_pct:10,total_loss_mode:"static",daily_loss_basis:"previous_close"}},
 {id:"topstep",name:"Topstep Combine 50K",kind:"verified",notice:"Modelo de referencia 50K: target $3,000 (6%), max loss $2,000 (4%) trailing EOD bloqueado en inicial, consistencia 55% del target. Reglas reales miden equity intradía, NO replicada.",update:{phases:[phase(6,0)],daily_loss_pct:0,total_loss_pct:4,total_loss_mode:"trailing_eod",trailing_lock_initial:true,consistency_mode:"best_day_target",consistency_max_pct:55}},
 {id:"fundednext",name:"FundedNext Stellar (plantilla)",kind:"template",notice:"Plantilla ilustrativa editable; verifica el modelo exacto y sus términos en tu cuenta.",update:{phases:[phase(8,0),phase(5,0)],daily_loss_pct:5,total_loss_pct:10}},
 {id:"lucid",name:"Lucid Trader Flex (plantilla)",kind:"template",notice:"Plantilla de demostración editable; no corresponde necesariamente a las reglas actuales de Lucid Trader.",update:{phases:[phase(8,0)],daily_loss_pct:4,total_loss_pct:8}},
 {id:"custom",name:"Personalizado",kind:"template",notice:"Configura todas las reglas para una cuenta específica.",update:{}},
];
type Props={value:FundingSettings;onChange:(v:FundingSettings)=>void;optimizationObjective:string;initialDeposit:number};
const pct=(n:number)=>new Intl.NumberFormat("es-DO",{maximumFractionDigits:2}).format(n);
const HELPS:Record<string,string>={
 phases:"Cada fase comienza con balance reiniciado al depósito inicial. Se consideran hasta tres fases secuenciales.",
 day_profit:"0 significa cualquier día con al menos una operación cerrada, incluso si termina en pérdida. Para exigir un día rentable usa un umbral positivo de ganancia sobre el capital inicial.",
 daily:"Previous close = saldo realizado del cierre previo − % del capital inicial. Inicial = capital inicial − %. Se verifica al cierre del día, no equity intrabar.",
 total:"Estático: límite fijo contra capital inicial. Trailing EOD: máximo histórico del balance realizado al fin de jornada menos % del inicial. Puede bloquearse al saldo inicial.",
 consistency:"Porcentaje máximo de contribución del mejor día. 'Sobre target' eleva el objetivo requerido; 'Sobre beneficio total' solo permite aprobar cuando la concentración cae por debajo del máximo.",
 days:"Se calcula el percentil indicado ENTRE los caminos que consiguieron aprobar. Se publica además la tasa incondicional que aprobó dentro del límite de días para evitar sesgo por supervivencia.",
 passes:"Una tasa mínima de 0% solo mide. Si indicas un porcentaje positivo, un candidato se rechaza cuando su estimación no alcanza ese mínimo.",
};
function Field({label,value,onChange,min=0,max=100,step=.1,suffix="%",help}:{
 label:string;value:number;onChange:(v:number)=>void;min?:number;max?:number;step?:number;suffix?:string;help?:string
}){return <label className="tq-fund-field"><span>{label}{help&&<span className="tq-fund-tooltip" title={help}><Info size={13}/></span>}</span><div><input type="number" min={min} max={max} step={step} value={value} onChange={e=>{let n=Number(e.target.value);if(Number.isFinite(n))onChange(n)}}/><small>{suffix}</small></div></label>}
function SelectField({label,value,onChange,options,help}:{label:string;value:string;onChange:(v:string)=>void;options:{value:string;label:string}[];help?:string}){return <label className="tq-fund-field"><span>{label}{help&&<span className="tq-fund-tooltip" title={help}><Info size={13}/></span>}</span><select value={value} onChange={e=>onChange(e.target.value)}>{options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select></label>}
function Section({title,children,icon:Icon}:{title:string;children:React.ReactNode;icon:typeof ShieldCheck}){return <section className="tq-fund-section"><h4><Icon size={17}/>{title}</h4><div>{children}</div></section>}
export function FundingConfig({value,onChange,optimizationObjective,initialDeposit}:Props){
 const c={...DEFAULT_FUNDING,...value};
 const [details,setDetails]=useState(false);
 const [showModel,setShowModel]=useState(true);
 const set=(patch:Partial<FundingSettings>)=>onChange({...c,...patch});
 const edit=(index:number,patch:Partial<FundingPhase>)=>set({phases:c.phases.map((p,i)=>i===index?{...p,...patch}:p)});
 const preset=PRESETS.find(x=>x.id===c.preset)||PRESETS[PRESETS.length-1];
 const apply=(p:Preset)=>onChange({...DEFAULT_FUNDING,...p.update,enabled:c.enabled,preset:p.id,simulations:c.simulations,bootstrap_block_days:c.bootstrap_block_days,min_pass_rate_pct:c.min_pass_rate_pct,pass_day_percentile:c.pass_day_percentile,max_pass_days_percentile:c.max_pass_days_percentile});
 return <div className="tq-funding">
   <div className="tq-fund-title"><div><span className="tq-fund-eyebrow">LABORATORIO / EVALUACIONES</span><h2>Simulador de fondeo</h2><p>Estima probabilidad de aprobar, tiempo requerido y riesgos por fase mediante Monte Carlo sobre operaciones históricas.</p></div>
    <label className="tq-fund-toggle"><input type="checkbox" checked={c.enabled} onChange={e=>set({enabled:e.target.checked})}/><span>{c.enabled?"Activado":"Desactivado"}</span></label></div>
   {!c.enabled&&<div className="tq-fund-disabled">Activa el simulador para evaluar el comportamiento de cada estrategia frente a reglas de fondeo. La configuración se guarda igualmente.</div>}
   <div className="tq-fund-content">
    <Section title="Presets rápidos" icon={Landmark}>
     <p>Seleccionar un preset rellena las reglas. Todos son editables y no sustituyen los términos actuales de la firma.</p>
     <div className="tq-fund-presets">{PRESETS.map(pr=><button key={pr.id} className={c.preset===pr.id?"active":""} onClick={()=>apply(pr)}>{pr.name}{pr.kind==="template"&&<small>Plantilla</small>}</button>)}</div>
     <div className="tq-fund-preset-note"><Info size={14}/>{preset.notice}</div>
     <p className="tq-fund-mini">Las cantidades se expresan como porcentaje del depósito inicial del backtest (USD {pct(initialDeposit)}). No cambia automáticamente el depósito según la empresa.</p>
    </Section>
    <Section title="Fases de evaluación" icon={ChartColumnIncreasing}>
     <p>Hasta 3 fases. Cada fase reinicia el balance nominal, los límites y el conteo de jornadas.</p>
     <div className="tq-fund-phases">{c.phases.map((ph,i)=><div className="tq-fund-phase" key={i}>
       <div className="tq-fund-phase-title"><strong>Fase {i+1}</strong><span>Target {pct(ph.target_pct)}%</span>{c.phases.length>1&&<button aria-label={"Eliminar fase "+(i+1)} onClick={()=>set({phases:c.phases.filter((_,j)=>j!==i)})}><Trash2 size={15}/></button>}</div>
       <div className="tq-fund-grid">
        <Field label="Objetivo de beneficio" value={ph.target_pct} min={.1} max={50} onChange={v=>edit(i,{target_pct:v})}/>
        <Field label="Máximo de días por fase" suffix="días" value={ph.max_days} min={1} max={730} step={1} onChange={v=>edit(i,{max_days:v})}/>
        <Field label="Días mínimos" suffix="días" min={0} max={365} step={1} value={ph.min_days} onChange={v=>edit(i,{min_days:v})}/>
        <Field label="Ganancia para contar el día" value={ph.min_profit_day_pct} min={0} max={20} step={.01} onChange={v=>edit(i,{min_profit_day_pct:v})} help={HELPS.day_profit}/>
       </div>
      </div>)}</div>
     {c.phases.length<3&&<button className="tq-fund-add" onClick={()=>set({phases:[...c.phases,phase(5,0)]})}><Plus size={15}/> Agregar otra fase</button>}
     <p className="tq-fund-mini">Umbral 0%: cuenta cualquier jornada con operaciones cerradas. Umbral positivo: exige beneficio realizado de al menos ese % del capital inicial.</p>
    </Section>
    <Section title="Límites y tipo de drawdown" icon={ShieldCheck}>
     <div className="tq-fund-grid">
      <Field label="Pérdida máxima diaria" value={c.daily_loss_pct} min={0} max={50} onChange={v=>set({daily_loss_pct:v})} help={HELPS.daily}/>
      <SelectField label="Base del límite diario" value={c.daily_loss_basis} onChange={v=>set({daily_loss_basis:v as FundingSettings["daily_loss_basis"]})} help={HELPS.daily} options={[
       {value:"previous_close",label:"Saldo realizado al cierre previo"}, {value:"initial",label:"Saldo inicial (fijo)"}
      ]}/>
      <Field label="Pérdida máxima total" value={c.total_loss_pct} min={.1} max={50} onChange={v=>set({total_loss_pct:v})} help={HELPS.total}/>
      <SelectField label="Modelo de pérdida total" value={c.total_loss_mode} onChange={v=>set({total_loss_mode:v as FundingSettings["total_loss_mode"]})} help={HELPS.total} options={[
       {value:"static",label:"Estático sobre saldo inicial"},{value:"trailing_eod",label:"Trailing de balance al cierre (EOD)"}
      ]}/>
     </div>
     {c.total_loss_mode==="trailing_eod"&&<label className="tq-fund-check"><input type="checkbox" checked={c.trailing_lock_initial} onChange={e=>set({trailing_lock_initial:e.target.checked})}/> Bloquear el trailing al llegar al saldo inicial (no subir el piso más allá)</label>}
     <div className="tq-fund-warning"><TriangleAlert size={17}/> <span>Drawdown flotante / trailing intradía no está disponible: el motor solo dispone de resultados realizados de operaciones, no de equity tick a tick. Estos filtros son una <strong>aproximación EOD</strong>.</span></div>
    </Section>
    <Section title="Consistencia" icon={Scale}>
     <div className="tq-fund-grid">
      <SelectField label="Regla de concentración de ganancias" value={c.consistency_mode} onChange={v=>set({consistency_mode:v as FundingSettings["consistency_mode"]})} help={HELPS.consistency} options={[
       {value:"none",label:"Sin consistencia"},
       {value:"best_day_total",label:"Mejor día / beneficio total"},
       {value:"best_day_target",label:"Mejor día / objetivo (ajustable)"}
      ]}/>
      {c.consistency_mode!=="none"&&<Field label="Máximo que puede aportar un día" value={c.consistency_max_pct} min={1} max={100} onChange={v=>set({consistency_max_pct:v})}/>}
     </div><p className="tq-fund-mini">En modo objetivo ajustable, el exceso de concentración incrementa la ganancia necesaria para aprobar la fase en vez de rechazar inmediatamente.</p>
    </Section>
    <Section title="Probabilidad y tiempo de aprobación" icon={Timer}>
     <div className="tq-fund-grid">
      <Field label="Tasa mínima de aprobación" help={HELPS.passes} value={c.min_pass_rate_pct} min={0} max={100} onChange={v=>set({min_pass_rate_pct:v})}/>
      <SelectField label="Percentil del tiempo de aprobación" value={String(c.pass_day_percentile)} onChange={v=>set({pass_day_percentile:Number(v) as FundingSettings["pass_day_percentile"]})} help={HELPS.days} options={[10,20,25,50,75,80,90,95].map(x=>({value:String(x),label:"P"+x+" · días acumulados"}))}/>
      <Field label={"Máximo de días en P"+c.pass_day_percentile} value={c.max_pass_days_percentile} suffix="días" min={0} max={2190} step={1} onChange={v=>set({max_pass_days_percentile:v})} help="0 = sin límite temporal. Si el percentil de días de los caminos aprobados supera este máximo, el candidato se rechaza."/>
      <SelectField label="Simulaciones Monte Carlo" value={String(c.simulations)} onChange={v=>set({simulations:Number(v)})} options={[64,128,256,512,1000].map(x=>({value:String(x),label:x.toLocaleString("es-DO")+" simulaciones"}))}/>
      <Field label="Tamaño del bloque bootstrap" value={c.bootstrap_block_days} min={1} max={20} step={1} suffix="días" onChange={v=>set({bootstrap_block_days:v})}/>
     </div>
     <div className="tq-fund-explanation"><strong>Ejemplo del filtro</strong> Si el Pass Rate es 80%, pero el P20 de las trayectorias aprobadas es de 465 días y estableces un máximo P20 de 60 días, <strong>el candidato no aprobará el filtro</strong>. También se informa qué porcentaje de todas las simulaciones aprobó antes del límite.</div>
     <p className="tq-fund-mini">Se mostrarán Pass Rate, P20/P50/P80, promedio de días entre las trayectorias exitosas, aprobación acumulada dentro del plazo, etapas superadas y motivos de fallo.</p>
    </Section>
    <div className="tq-fund-footer"><button onClick={()=>setDetails(s=>!s)}><SlidersHorizontal size={15}/> Metodología y límites <ChevronDown className={details?"rotated":""} size={15}/></button>
     {details&&<p>Las fases se prueban secuencialmente a partir de jornadas históricas remuestreadas (bootstrap por bloques) con capital reiniciado por fase. Cada balance se verifica al final de la jornada. El motor no simula spread variable, swaps, slippage, noticias, margen ni drawdown intrabar. Los percentiles de tiempo se calculan solo entre trayectorias aprobadas: para evitar sesgo de supervivencia se reporta además la tasa incondicional dentro del plazo. Un día se identifica por operaciones cerradas en los datos, no por apertura.</p>}
    </div>
    {optimizationObjective==="funding_pass_rate"&&<div className="tq-fund-opt"><ShieldCheck size={16}/> El objetivo de optimización seleccionado es <strong>Mayor Pass Rate de Fondeo</strong>. También penaliza el tiempo requerido y aplica los filtros mínimos definidos aquí.</div>}
   </div>
 </div>;
}
