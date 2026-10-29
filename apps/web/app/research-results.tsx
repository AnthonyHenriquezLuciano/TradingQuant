"use client";
import {useMemo,useState} from "react";
import {ArrowLeft,ArrowRight,Bookmark,CalendarDays,ChartNoAxesCombined,CheckCircle2,Clock3,Eye,Filter,FlaskConical,Grid2X2,Info,List,Search,ShieldAlert,SlidersHorizontal,TrendingUp,Wallet} from "lucide-react";
export type TradeRow={number:number;entry_time:string;exit_time:string;entry_price:number;exit_price:number;average_price:number;direction:string;result:string;pnl_usd:number;gross_usd:number;costs_usd:number;r_multiple:number;balance_usd:number;duration_bars:number};
export type MarketBar={time:string;open:number;high:number;low:number;close:number};
export type FundingReport={pass_rate_pct:number;p20_days:number|null;p50_days:number|null;p80_days:number|null;phase_pass_rate_pct:number[];pass_within_day_cap_pct:number;eligible:boolean;simulations:number;successful_paths:number;selected_percentile_days:number|null};
export type QuantCandidate={
 id:string;family:string;params:Record<string,number>;entry_mode?:string;direction?:string;timeframe?:string;accepted:boolean;reasons:string[];optimization_score?:number;
 in_sample:{trades:number;win_rate:number;profit_factor:number|null;expectancy_r:number;max_drawdown_pct:number;net_return_pct:number};
 out_of_sample:{trades:number;win_rate:number;profit_factor:number|null;expectancy_r:number;max_drawdown_pct:number;net_return_pct:number};
 quality_is?:{sharpe:number;dsr:number}|null;quality_oos?:{sharpe:number;dsr:number}|null;
 ledger?:TradeRow[];market_chart?:MarketBar[];estimated_cost_bps?:number;
 funding_evaluation_oos?:FundingReport|null;
 walk_forward?:{pass_rate_pct?:number;median_wfe?:number;eligible?:boolean}|null;
 multiverse?:{score?:number;survival_pct?:number;universes?:number}|null;
};
export type QuantRun={
 id:string;created_at:string;tested:number;accepted:number;candidates:QuantCandidate[];warnings:string[];
 config:{name:string;symbol:string;timeframe:string;initial_deposit:number;optimization_objective?:string;mode:string;funding?:{enabled:boolean}|null};
};
const fmt=(x:number|null|undefined,d=2)=>x==null||!Number.isFinite(x)?"—":x.toLocaleString("es-DO",{minimumFractionDigits:d,maximumFractionDigits:d});
const money=(v:number)=>((v<0)?"−":"")+"$"+fmt(Math.abs(v));
const pct=(v:number|null|undefined)=>v==null?"—":fmt(v,1)+"%";
const title=(c:QuantCandidate)=>c.family.replaceAll("_"," ")+" · "+Object.entries(c.params).map(([k,v])=>k+" "+v).join(" · ");
function Tag({children,kind=""}:{children:React.ReactNode;kind?:string}){return <span className={"tq-r-tag "+kind}>{children}</span>}
function Equity({ledger,height=100}:{ledger:TradeRow[];height?:number}){
 if(!ledger.length)return <div className="tq-r-emptychart">Sin operaciones OOS registradas.</div>;
 const values=[ledger[0].balance_usd-ledger[0].pnl_usd,...ledger.map(t=>t.balance_usd)];
 const min=Math.min(...values),max=Math.max(...values),span=Math.max(.01,max-min);
 const points=values.map((v,i)=>(10+i/Math.max(1,values.length-1)*780)+","+(15+(max-v)/span*100)).join(" ");
 const good=values.at(-1)!>=values[0];
 return <svg role="img" aria-label="Equity realizada sobre operaciones OOS" viewBox="0 0 800 130" preserveAspectRatio="none" style={{width:"100%",height}}>
  <defs><linearGradient id="tqProfitFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={good?"#43c09f":"#df6a68"} stopOpacity=".19"/><stop offset="1" stopColor="transparent"/></linearGradient></defs>
  {[24,64,107].map(y=><line key={y} x1={0} x2={800} y1={y} y2={y} stroke="#44382a" strokeDasharray="3 5" strokeWidth=".8"/>)}
  <polygon points={"10,120 "+points+" 790,120"} fill="url(#tqProfitFill)"/>
  <polyline points={points} fill="none" stroke={good?"#43c09f":"#e36a69"} strokeWidth="2.4" vectorEffect="non-scaling-stroke"/>
 </svg>;
}
function Candles({bars,ledger}:{bars:MarketBar[];ledger:TradeRow[]}){
 if(!bars.length)return <div className="tq-r-emptychart">Sin datos OHLC correspondientes a esta estrategia.</div>;
 const hi=Math.max(...bars.map(x=>x.high)),lo=Math.min(...bars.map(x=>x.low)),range=Math.max(.00001,hi-lo);
 const y=(p:number)=>16+(hi-p)/range*258;
 const x=(i:number)=>(i+.5)*900/bars.length;
 const index=new Map(bars.map((b,i)=>[b.time,i]));
 return <><svg viewBox="0 0 900 300" preserveAspectRatio="none" role="img" aria-label="Últimas velas OHLC reales del tramo OOS" className="tq-r-candles">
 {[70,140,210].map(v=><line key={v} x1={0} x2={900} y1={v} y2={v} stroke="#332a21" strokeWidth=".7"/>)}
 {bars.map((b,i)=>{const up=b.close>=b.open,w=Math.max(1,900/bars.length*.6);return <g key={i}><line x1={x(i)} x2={x(i)} y1={y(b.high)} y2={y(b.low)} stroke={up?"#49bfa1":"#df7473"}/><rect x={x(i)-w/2} y={Math.min(y(b.open),y(b.close))} width={w} height={Math.max(1,Math.abs(y(b.open)-y(b.close)))} fill={up?"#49bfa1":"#df7473"}/></g>})}
 {ledger.map(t=>{const i=index.get(t.exit_time);return i===undefined?null:<circle key={t.number} cx={x(i)} cy={y(t.exit_price)} r={3.5} fill={t.pnl_usd>=0?"#dbb276":"#f0927a"} stroke="#100e0c" strokeWidth="1.2"/>})}
 </svg><div className="tq-r-axis"><span>{bars[0].time.replace("T"," ")}</span><span>{fmt(lo,4)} – {fmt(hi,4)}</span><span>{bars.at(-1)?.time.replace("T"," ")}</span></div></>;
}
function Metric({label,value,sub}:{label:string;value:string;sub?:string}){return <div className="tq-r-metric"><span>{label}</span><strong>{value}</strong>{sub&&<small>{sub}</small>}</div>}
function Calendar({ledger}:{ledger:TradeRow[]}){
 const months=[...new Set(ledger.map(t=>t.exit_time.slice(0,7)))].sort();
 const [offset,setOffset]=useState(0);
 const key=months.length?months[Math.max(0,months.length-offset-1)]:null;
 const date=key?new Date(key+"-01T12:00:00"):new Date();
 const count=new Date(date.getFullYear(),date.getMonth()+1,0).getDate();
 const pad=(date.getDay()+6)%7;
 const totals=new Map<number,{usd:number;trades:number}>();
 for(const t of ledger){if(t.exit_time.slice(0,7)!==key)continue;const d=Number(t.exit_time.slice(8,10)),p=totals.get(d)||{usd:0,trades:0};p.usd+=t.pnl_usd;p.trades++;totals.set(d,p)}
 return <section className="tq-r-panel"><div className="tq-r-sectionhead"><h3><CalendarDays size={18}/> Calendario de operaciones OOS</h3><div className="tq-r-month"><button disabled={offset>=months.length-1} onClick={()=>setOffset(x=>x+1)}>‹</button>{date.toLocaleDateString("es-DO",{month:"long",year:"numeric"})}<button disabled={!offset} onClick={()=>setOffset(x=>x-1)}>›</button></div></div><div className="tq-r-calendar">{["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"].map(t=><div className="tq-r-weekday" key={t}>{t}</div>)}{Array.from({length:pad},(_,i)=><div key={"pad"+i} className="tq-r-day"/>)}
 {Array.from({length:count},(_,i)=>{const t=totals.get(i+1);return <div key={i} className={"tq-r-day "+(t?(t.usd<0?"loss":"win"):"")}><span>{i+1}</span>{t&&<><strong>{money(t.usd)}</strong><small>{t.trades} ops.</small></>}</div>})}</div><div className="tq-r-monthstats"><span>Días con cierres: <b>{totals.size}</b></span><span>Trades: <b>{[...totals.values()].reduce((a,t)=>a+t.trades,0)}</b></span><span>Resultado: <b>{money([...totals.values()].reduce((a,t)=>a+t.usd,0))}</b></span></div></section>;
}
export function ResearchResults({run,onSelect,onEdit}:{run:QuantRun;onSelect:(id:string)=>void;onEdit:()=>void}){
 const [layout,setLayout]=useState<"grid"|"list">("grid"),[search,setSearch]=useState(""),[onlyAccepted,setOnlyAccepted]=useState(false),[win,setWin]=useState(0),[dd,setDd]=useState(100),[sort,setSort]=useState("score");
 const found=useMemo(()=>run.candidates.filter(c=>(!onlyAccepted||c.accepted)&&title(c).toLowerCase().includes(search.toLowerCase())&&c.out_of_sample.win_rate>=win&&c.out_of_sample.max_drawdown_pct<=dd).sort((a,b)=>sort==="sharpe"?(b.quality_oos?.sharpe??-999)-(a.quality_oos?.sharpe??-999):sort==="pnl"?b.out_of_sample.net_return_pct-a.out_of_sample.net_return_pct:sort==="dd"?a.out_of_sample.max_drawdown_pct-b.out_of_sample.max_drawdown_pct:(b.optimization_score??-1e9)-(a.optimization_score??-1e9)),[run.candidates,search,onlyAccepted,win,dd,sort]);
 return <div className="tq-results">
 <div className="tq-r-heading"><div><span className="tq-r-eyebrow">LABORATORIO / EXPLORACIÓN TERMINADA</span><h1>Ranking de resultados</h1><p>{run.config.name} · {run.config.symbol} · {run.config.timeframe.toUpperCase()} · {run.config.mode==="genetic"?"Evolución genética":"Exploración aleatoria"}</p></div><button className="tq-r-secondary" onClick={onEdit}><SlidersHorizontal size={16}/> Modificar configuración</button></div>
 <div className="tq-r-metrics"><Metric label="Progreso" value="100%" sub="Listo"/><Metric label="Probadas" value={String(run.tested)} sub="Evaluaciones reales"/><Metric label="Pasan filtros" value={String(run.accepted)} sub="Candidatos aceptados"/><Metric label="Top candidatos" value={String(run.candidates.length)} sub="Ranking y detalle"/><Metric label="Tiempo" value="—" sub="Sin medición anterior"/></div>
 <div className="tq-r-summary"><Tag>{run.config.symbol}</Tag><Tag>{run.config.timeframe.toUpperCase()}</Tag><Tag>{money(run.config.initial_deposit)}</Tag><span>Orden: {run.config.optimization_objective||"balanced"}</span><span>{run.tested} combinaciones probadas</span></div>
 <section className="tq-r-panel"><div className="tq-r-sectionhead"><div><h2>Ranking de estrategias</h2><p>Ordenado por score IS. Al seleccionar orden OOS, solo cambia la vista, no la selección estadística.</p></div><div className="tq-r-layout"><button className={layout==="grid"?"active":""} onClick={()=>setLayout("grid")} aria-label="Vista tarjetas"><Grid2X2 size={17}/></button><button className={layout==="list"?"active":""} onClick={()=>setLayout("list")} aria-label="Vista lista"><List size={17}/></button></div></div>
 <div className="tq-r-filters"><label><Search size={16}/><input aria-label="Buscar estrategias" placeholder="Buscar reglas…" value={search} onChange={e=>setSearch(e.target.value)}/></label><label>Orden<select value={sort} onChange={e=>setSort(e.target.value)}><option value="score">Score IS</option><option value="sharpe">Sharpe OOS</option><option value="pnl">Retorno OOS</option><option value="dd">Menor DD OOS</option></select></label><label>WR mínimo<input type="number" min={0} max={100} value={win} onChange={e=>setWin(Number(e.target.value))}/></label><label>DD máximo<input type="number" min={0} max={100} value={dd} onChange={e=>setDd(Number(e.target.value))}/></label><label className="tq-r-check"><input type="checkbox" checked={onlyAccepted} onChange={e=>setOnlyAccepted(e.target.checked)}/> Solo aptas</label></div>
 <p className="tq-r-caption">Mostrando {found.length} de {run.candidates.length} candidatos. Ningún resultado se inventa ni se guarda en Mis Algoritmos todavía.</p>
 <div className={layout==="grid"?"tq-r-cardgrid":"tq-r-cardlist"}>{found.map((c,i)=><article className="tq-r-algocard" key={c.id}><div className="tq-r-cardname"><small>#{i+1}</small><strong>{title(c)}</strong></div><div className="tq-r-tags"><Tag>{run.config.symbol}</Tag><Tag>{c.timeframe||run.config.timeframe}</Tag><Tag>{c.entry_mode||"mercado"}</Tag><Tag kind={c.accepted?"good":"warn"}>{c.accepted?"Apta*":"Filtro no superado"}</Tag></div><Equity ledger={c.ledger||[]}/><div className="tq-r-cardstats"><span><b>{fmt(c.quality_oos?.sharpe)}</b>Sharpe</span><span><b>{pct(c.out_of_sample.max_drawdown_pct)}</b>DD</span><span><b>{pct(c.out_of_sample.win_rate)}</b>WR</span><span><b>{fmt(c.out_of_sample.profit_factor)}</b>PF</span><span><b>{c.out_of_sample.trades}</b>Trades</span></div><button className="tq-r-cardaction" onClick={()=>onSelect(c.id)}><Eye size={15}/> Ver detalles <ArrowRight size={15}/></button><button disabled className="tq-r-save"><Bookmark size={14}/> Guardar en Mis Algoritmos · Próximamente</button></article>)}</div>{!found.length&&<div className="tq-r-emptychart">No hay estrategias que cumplan estos filtros. Ajusta los controles.</div>}</section>
 <div className="tq-r-note"><Info size={16}/> Las curvas y las operaciones utilizan el tramo OOS. La simulación de fondeo no equivale a una aprobación real.</div>
 </div>;
}
export function StrategyDetail({run,candidate,onBack}:{run:QuantRun;candidate:QuantCandidate;onBack:()=>void}){
 const [tab,setTab]=useState<"analysis"|"trades"|"funding">("analysis");
 const ledger=candidate.ledger||[],net=ledger.reduce((v,t)=>v+t.pnl_usd,0),gross=ledger.reduce((v,t)=>v+t.gross_usd,0),cost=ledger.reduce((v,t)=>v+t.costs_usd,0);
 const monthly=new Map<string,number>();for(const t of ledger){const m=t.exit_time.slice(0,7);monthly.set(m,(monthly.get(m)||0)+t.pnl_usd)}
 const years=[...new Set([...monthly.keys()].map(s=>s.slice(0,4)))].sort();
 const fund=candidate.funding_evaluation_oos;
 return <div className="tq-results">
 <div className="tq-r-heading"><div><button onClick={onBack} className="tq-r-back"><ArrowLeft size={16}/> Volver al ranking</button><h1>{title(candidate)}</h1><p>{run.config.symbol} · {candidate.timeframe||run.config.timeframe} · Detalle OOS de {run.config.name}</p></div><button disabled className="tq-r-save"><Bookmark size={16}/> Guardar en Mis Algoritmos · Próximamente</button></div>
 <div className="tq-r-tabs">{[["analysis","Análisis y gráficos"],["trades","Lista de trades"],["funding","Fondeo"]].map(([id,label])=><button key={id} className={tab===id?"active":""} onClick={()=>setTab(id as typeof tab)}>{label}</button>)}</div>
 {tab==="analysis"&&<>
 <div className="tq-r-metrics tq-r-stats"><Metric label="P&L Total" value={money(net)} sub="Saldo OOS"/><Metric label="Expectativa" value={ledger.length?money(net/ledger.length):"—"} sub="Por trade"/><Metric label="Win Rate" value={pct(candidate.out_of_sample.win_rate)}/><Metric label="Profit Factor" value={fmt(candidate.out_of_sample.profit_factor)}/><Metric label="Sharpe" value={fmt(candidate.quality_oos?.sharpe)}/><Metric label="Max Drawdown" value={pct(candidate.out_of_sample.max_drawdown_pct)}/><Metric label="DSR" value={fmt(candidate.quality_oos?.dsr,3)}/></div>
 <section className="tq-r-panel"><h3><ChartNoAxesCombined size={17}/> Curva de equity · OOS</h3><Equity ledger={ledger} height={275}/><div className="tq-r-metrics tq-r-stats"><Metric label="Balance inicial" value={money(run.config.initial_deposit)}/><Metric label="Balance final" value={money(run.config.initial_deposit+net)}/><Metric label="Retorno total" value={pct(net/run.config.initial_deposit*100)}/><Metric label="Trades" value={String(ledger.length)}/><Metric label="Mejor trade" value={money(Math.max(0,...ledger.map(t=>t.pnl_usd)))}/><Metric label="Peor trade" value={money(Math.min(0,...ledger.map(t=>t.pnl_usd)))}/></div></section>
 <section className="tq-r-panel"><h3><ChartNoAxesCombined size={17}/> Gráfico de operaciones · OHLC OOS</h3><Candles bars={candidate.market_chart||[]} ledger={ledger}/><p className="tq-r-caption">Las últimas velas proceden del CSV histórico. Los marcadores visibles corresponden a cierres ejecutados dentro de esta muestra; no son operaciones inventadas.</p></section>
 <section className="tq-r-panel"><h3><Wallet size={17}/> Análisis de costes</h3><div className="tq-r-metrics tq-r-stats"><Metric label="PnL Bruto" value={money(gross)}/><Metric label="Costes agregados" value={money(cost)}/><Metric label="PnL Neto" value={money(net)}/><Metric label="Coste aplicado" value={fmt(candidate.estimated_cost_bps,3)+" bps"}/></div><p className="tq-r-caption">La separación exacta de spread, slippage y swaps por operación aún no está disponible; se muestra el coste agregado que el motor aplicó.</p></section>
 <section className="tq-r-panel"><h3><Filter size={17}/> Definición de estrategia</h3><p className="tq-r-caption">Familia: {candidate.family} · Entrada: {candidate.entry_mode||"mercado"} · Dirección: {candidate.direction||"ambas"}.</p><div className="tq-r-tags">{Object.entries(candidate.params).map(([key,value])=><Tag key={key}>{key}: {value}</Tag>)}</div></section>
 <section className="tq-r-panel"><h3>Rendimiento mensual · USD · OOS</h3><div className="tq-r-tablewrap"><table className="tq-r-table"><thead><tr><th>Año</th>{["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"].map(m=><th key={m}>{m}</th>)}<th>YTD</th></tr></thead><tbody>{years.map(y=><tr key={y}><td>{y}</td>{Array.from({length:12},(_,i)=>{const val=monthly.get(y+"-"+String(i+1).padStart(2,"0"));return <td key={i} className={val==null?"":val<0?"negative":"positive"}>{val==null?"—":money(val)}</td>})}<td>{money([...monthly].filter(([k])=>k.startsWith(y)).reduce((s,[,v])=>s+v,0))}</td></tr>)}</tbody></table></div></section>
 <Calendar ledger={ledger}/>
 </>}
 {tab==="trades"&&<section className="tq-r-panel"><h3><List size={17}/> Lista de trades · {ledger.length} operaciones OOS</h3><div className="tq-r-tablewrap"><table className="tq-r-table"><thead><tr>{["#","Entrada","Salida","Lado","Precio de entrada","Precio de salida","Bruto USD","Costes USD","Neto USD","R","Balance","Velas"].map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{ledger.map(t=><tr key={t.number}><td>{t.number}</td><td>{t.entry_time.replace("T"," ")}</td><td>{t.exit_time.replace("T"," ")}</td><td>{t.direction}</td><td>{fmt(t.entry_price,5)}</td><td>{fmt(t.exit_price,5)}</td><td>{money(t.gross_usd)}</td><td>{money(-t.costs_usd)}</td><td className={t.pnl_usd<0?"negative":"positive"}>{money(t.pnl_usd)}</td><td>{fmt(t.r_multiple)}</td><td>{money(t.balance_usd)}</td><td>{t.duration_bars}</td></tr>)}</tbody></table></div>{!ledger.length&&<div className="tq-r-emptychart">Esta ejecución no incluye trazas de trades (podría ser una exploración anterior a la mejora).</div>}</section>}
 {tab==="funding"&&<section className="tq-r-panel"><h3><ShieldAlert size={17}/> Evaluación para cuentas de fondeo</h3>{!fund?<div className="tq-r-emptychart">No hay simulación de fondeo para este resultado. Activa Fondeo en una nueva exploración.</div>:<><div className="tq-r-metrics tq-r-stats"><Metric label="Pass Rate estimado" value={pct(fund.pass_rate_pct)}/><Metric label="P20 de días" value={fmt(fund.p20_days,0)}/><Metric label="P50 de días" value={fmt(fund.p50_days,0)}/><Metric label="P80 de días" value={fmt(fund.p80_days,0)}/><Metric label="Dentro del plazo" value={pct(fund.pass_within_day_cap_pct)}/><Metric label="Rutas exitosas" value={fund.successful_paths+" / "+fund.simulations}/></div><h3>Porcentajes acumulados por fase</h3><div className="tq-r-phasebars">{fund.phase_pass_rate_pct.map((v,i)=><div key={i}><span>Fase {i+1} · {pct(v)}</span><div><span style={{width:Math.max(0,Math.min(100,v))+"%"}}/></div></div>)}</div><div className="tq-r-note"><Info size={16}/> Proxy basado en cierres realizados; no reproduce pérdidas flotantes, margen ni todos los requisitos contractuales. P20/P50/P80 se calculan únicamente entre rutas que aprobaron.</div></>}</section>}
 </div>;
}
