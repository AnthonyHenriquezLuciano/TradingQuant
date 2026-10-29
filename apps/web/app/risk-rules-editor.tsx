"use client";
import {useState} from "react";
import {Plus,X,ShieldCheck,TrendingDown,TrendingUp,Gauge,Info} from "lucide-react";
export type RiskRules={
 max_daily_gain_pct:number;max_weekly_gain_pct:number;max_monthly_gain_pct:number;max_account_gain_pct:number;
 max_consecutive_wins:number;
 max_daily_loss_pct:number;max_weekly_loss_pct:number;max_monthly_loss_pct:number;max_account_loss_pct:number;
 max_consecutive_losses:number;min_reward_risk_ratio:number;
};
export const DEFAULT_RISK_RULES:RiskRules={
 max_daily_gain_pct:0,max_weekly_gain_pct:0,max_monthly_gain_pct:0,max_account_gain_pct:0,max_consecutive_wins:0,
 max_daily_loss_pct:0,max_weekly_loss_pct:0,max_monthly_loss_pct:0,max_account_loss_pct:0,max_consecutive_losses:0,
 min_reward_risk_ratio:0
};
type Rule={key:keyof RiskRules;label:string;initial:number;max:number;step:number};
const GROUPS:{title:string;icon:typeof Gauge;items:Rule[]}[]=[
 {title:"GANANCIAS",icon:TrendingUp,items:[
  {key:"max_daily_gain_pct",label:"Máx. ganancia diaria (%)",initial:3,max:50,step:.25},
  {key:"max_weekly_gain_pct",label:"Máx. ganancia semanal (%)",initial:6,max:100,step:.25},
  {key:"max_monthly_gain_pct",label:"Máx. ganancia mensual (%)",initial:10,max:100,step:.25},
  {key:"max_account_gain_pct",label:"Máx. ganancia de la cuenta (%)",initial:10,max:200,step:.25},
  {key:"max_consecutive_wins",label:"Máx. ganancias consecutivas",initial:5,max:100,step:1}]},
 {title:"PÉRDIDAS",icon:TrendingDown,items:[
  {key:"max_daily_loss_pct",label:"Máx. pérdida diaria (%)",initial:3,max:50,step:.25},
  {key:"max_weekly_loss_pct",label:"Máx. pérdida semanal (%)",initial:6,max:100,step:.25},
  {key:"max_monthly_loss_pct",label:"Máx. pérdida mensual (%)",initial:8,max:100,step:.25},
  {key:"max_account_loss_pct",label:"Máx. pérdida de la cuenta (%)",initial:10,max:100,step:.25},
  {key:"max_consecutive_losses",label:"Máx. pérdidas consecutivas",initial:3,max:100,step:1}]},
 {title:"OPERATIVA",icon:Gauge,items:[
  {key:"min_reward_risk_ratio",label:"Ratio recompensa/riesgo mínimo",initial:1,max:10,step:.1}]},
];
type Props={rules:RiskRules;onChange:(r:RiskRules)=>void;riskPct:number;onRisk:(n:number)=>void;tradesDay:number;onTradesDay:(n:number)=>void};
export function RiskRulesEditor({rules:on,onChange,riskPct,onRisk,tradesDay,onTradesDay}:Props){
 const r={...DEFAULT_RISK_RULES,...on};
 const [showRisk,setShowRisk]=useState(false);
 const [showTrades,setShowTrades]=useState(false);
 const total=GROUPS.reduce((a,g)=>a+g.items.filter(i=>r[i.key]>0).length,0)+(showRisk?1:0)+(showTrades?1:0);
 return <div className="tq-risk-rules">
   <div className="tq-risk-rules-heading"><span>Agregar regla de riesgo</span><strong>{total} activas</strong></div>
   {GROUPS.map(group=><div className="tq-risk-rule-category" key={group.title}>
    <div className="tq-risk-rule-caption"><group.icon size={14}/>{group.title}</div>
    <div className="tq-risk-rule-chips">{group.items.map(item=><button type="button" key={item.key} className={r[item.key]>0?"selected":""} onClick={()=>onChange({...r,[item.key]:r[item.key]>0?0:item.initial})}>
     {r[item.key]>0?<ShieldCheck size={13}/>:<Plus size={13}/>} {item.label}</button>)}
     {group.title==="OPERATIVA"&&<>
      <button className={showRisk?"selected":""} onClick={()=>setShowRisk(s=>!s)}>{showRisk?<ShieldCheck size={13}/>:<Plus size={13}/>} Riesgo por operación (%)</button>
      <button className={showTrades?"selected":""} onClick={()=>setShowTrades(s=>!s)}>{showTrades?<ShieldCheck size={13}/>:<Plus size={13}/>} Máx. operaciones por día</button>
     </>}</div>
   </div>)}
   {total>0?<div className="tq-risk-rule-selected">
    <div className="tq-risk-rule-selected-header">Reglas configuradas <span>0 = desactivada</span></div>
    {GROUPS.flatMap(g=>g.items).filter(i=>r[i.key]>0).map(item=><div className="tq-risk-rule-selected-row" key={item.key}>
     <span>{item.label}</span><input aria-label={item.label} type="number" min={item.step} max={item.max} step={item.step} value={r[item.key]} onChange={e=>{const value=Number(e.target.value);if(Number.isFinite(value))onChange({...r,[item.key]:Math.max(0,Math.min(item.max,value))})}}/><button aria-label={"Eliminar "+item.label} onClick={()=>onChange({...r,[item.key]:0})}><X size={15}/></button>
    </div>)}
    {showRisk&&<div className="tq-risk-rule-selected-row"><span>Riesgo por operación (%)</span><input aria-label="Riesgo por operación" type="number" min={.05} max={2} step={.05} value={riskPct} onChange={e=>onRisk(Number(e.target.value))}/><button aria-label="Cerrar editor de riesgo" onClick={()=>setShowRisk(false)}><X size={15}/></button></div>}
    {showTrades&&<div className="tq-risk-rule-selected-row"><span>Máx. operaciones por día (0 = sin límite)</span><input aria-label="Máx. operaciones por día" type="number" min={0} max={100} step={1} value={tradesDay} onChange={e=>onTradesDay(Number(e.target.value))}/><button aria-label="Cerrar editor de operaciones" onClick={()=>setShowTrades(false)}><X size={15}/></button></div>}
   </div>:<div className="tq-risk-rules-empty">Agrega reglas de riesgo para filtrar las operaciones y proteger la cuenta.</div>}
   <p className="tq-capital-muted"><Info size={14}/> Las restricciones se evalúan sobre ganancias/pérdidas <strong>realizadas</strong>, no equity flotante. Los topes semanales y mensuales se reinician al cambiar el periodo UTC. Los límites por racha detienen nuevas entradas hasta el día siguiente.</p>
  </div>;
}
