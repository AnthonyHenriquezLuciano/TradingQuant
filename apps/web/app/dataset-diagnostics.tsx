"use client";
import {Activity,AlertTriangle,BarChart3,Info,LoaderCircle,RefreshCw} from "lucide-react";

export type AssetDiagnostics={
 dataset_id:string;historical_only:boolean;message:string;warnings:string[];
 timeframes:{timeframe:string;rows:number;days:number;atr_period:number;
 atr_price_units:{p05:number;p25:number;median:number;p75:number;p95:number};
 atr_pct_of_price_median:number;daily_bars_max:number;daily_bars_median:number;
 price_min:number;price_max:number;
 signal_samples:{family:string;max_signals_day:number;median_signals_active_day:number}[];
 }[];
};
type Props={value:AssetDiagnostics|null;loading:boolean;onAnalyze:()=>void;datasetLoaded:boolean;pipSize?:number};
const fmt=(n:number,d=5)=>n.toLocaleString("es-DO",{maximumFractionDigits:d});
export function DatasetDiagnostics({value,loading,onAnalyze,datasetLoaded,pipSize}:Props){
 return <section className="tq-diagnostics">
  <div className="tq-diagnostics-head"><div><h3><Activity size={18}/> Límites históricos del instrumento</h3><p>Calculados exclusivamente del CSV seleccionado: ATR(14), distribución de rangos y frecuencia de señales de referencia.</p></div><button type="button" disabled={!datasetLoaded||loading} onClick={onAnalyze}>{loading?<LoaderCircle size={15} className="spin"/>:<RefreshCw size={15}/>} {loading?"Analizando…":value?"Volver a analizar":"Analizar histórico"}</button></div>
  {!datasetLoaded&&<p className="tq-diagnostics-empty">Importa y selecciona un CSV para consultar el ATR real y detectar ajustes poco útiles. No mostramos valores genéricos como si fueran del activo.</p>}
  {value&&<>
   {value.timeframes.map(tf=><div key={tf.timeframe} className="tq-diagnostics-tf"><div className="tq-diagnostics-meta"><strong>{tf.timeframe.toUpperCase()} · ATR(14)</strong><span>{fmt(tf.rows,0)} velas · {fmt(tf.days,0)} días históricos</span></div>
    <div className="tq-diagnostics-grid">{[
     ["Mínimo frecuente (P5)",tf.atr_price_units.p05],
     ["Cuartil inferior (P25)",tf.atr_price_units.p25],
     ["ATR mediano (P50)",tf.atr_price_units.median],
     ["Cuartil superior (P75)",tf.atr_price_units.p75],
     ["Extremo frecuente (P95)",tf.atr_price_units.p95]
    ].map(([k,v])=><div key={String(k)}><small>{k}</small><strong>{fmt(Number(v))}</strong><span>{pipSize&&pipSize>0?fmt(Number(v)/pipSize,1)+" pips":"unidades de precio"}</span></div>)}</div>
    <p className="tq-diagnostics-hint">Referencia: el 90% central del ATR(14) se observó aproximadamente entre <strong>{fmt(tf.atr_price_units.p05)}</strong> y <strong>{fmt(tf.atr_price_units.p95)}</strong> unidades de precio. ATR mediano ≈ {fmt(tf.atr_pct_of_price_median,3)}% del precio. No es una recomendación automática de SL o TP.</p>
    <div className="tq-diagnostics-meta"><span>Máximo observado: {tf.daily_bars_max} barras por día · Mediana: {fmt(tf.daily_bars_median,0)} barras/día</span></div>
    {tf.signal_samples.length>0&&<div className="tq-diagnostics-signals">{tf.signal_samples.map(sample=><span key={sample.family}><BarChart3 size={13}/> {sample.family}: máximo observado <b>{sample.max_signals_day}</b> señales/día; mediana <b>{fmt(sample.median_signals_active_day,1)}</b> en días activos</span>)}</div>}
   </div>)}
   {value.warnings.length>0&&<div className="tq-diagnostics-warnings">{value.warnings.map((msg,i)=><p key={i}><AlertTriangle size={15}/> {msg}</p>)}</div>}
   <p className="tq-diagnostics-disclaimer"><Info size={14}/> Los percentiles son descriptivos y las señales se muestrean con parámetros de referencia. No establecen máximos absolutos de una estrategia optimizada ni introducen predicción de precios.</p>
  </>}
 </section>;
}
