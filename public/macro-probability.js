import {loadProbability} from './macro-probability-model.js?v=prob-20261009a';
import {translate as t,numberLocale} from './i18n.js?v=prob-20261009a';
const $=id=>document.getElementById(id);
const STATES={collecting:'Đang thu thập mẫu',awaiting_calibration:'Chờ mẫu hiệu chỉnh',awaiting_test:'Chờ kiểm tra ngoài mẫu',validation_failed:'Chưa vượt kiểm định',validated_holdout:'Đã vượt kiểm tra ngoài mẫu nội bộ'};
let good=null,warning=null,busy=false,calendarId=null;
export function renderProbability(){
  if(!good){$('prob-error').hidden=false;$('prob-error').textContent=t(warning||'Đang xác minh mô hình xác suất…');return;}
  const {data:d,status,pointer,proof,currentMacro}=good,c=d.latest_case,e=d.evaluation;
  const outdated=!!warning||status.outcome==='error'||Date.now()-Date.parse(status.checked_at)>48*3600000||Date.now()-Date.parse(d.current_context.as_of)>48*3600000||!proof.last_successful_source_check_at||Date.now()-Date.parse(proof.last_successful_source_check_at)>48*3600000||Date.now()<Date.parse(status.checked_at)||!d.current_context.eligible||currentMacro.assessment_id!==d.current_context.assessment_id||calendarId&&!d.current_context.parents.calendar.url.includes(calendarId);
  $('prob-content').hidden=false;$('prob-content').dataset.releaseId=d.release_id;
  $('prob-error').hidden=!outdated;$('prob-error').textContent=t(warning||'Giữ mô hình tại ngày gốc; bối cảnh hiện chưa đủ mới.');
  $('prob-state').textContent=t(STATES[e.state]);
  $('prob-context').textContent=`${t('Kịch bản')}: ${d.current_context.regime_id} · ${t('Case đã ghi nhận')}: ${d.cases_count} · ${t('Đã có kết quả')}: ${d.resolved_count}`;
  $('prob-train').textContent=`${e.train_n}/90`;$('prob-calibration').textContent=`${e.calibration_n}/45`;$('prob-test').textContent=`${e.test_n}/45`;
  $('prob-regime-samples').textContent=`${t('Mẫu của kịch bản hiện tại')}: ${e.regime_counts.train}/30 · ${e.regime_counts.calibration}/15 · ${e.regime_counts.test}/15`;
  const date=x=>new Intl.DateTimeFormat(numberLocale(),{timeZone:'UTC',dateStyle:'medium'}).format(new Date(x));
  $('prob-window').textContent=c?`${t('Case đầu kỳ')}: ${c.regime_id} · ${date(c.base_date)} → ${date(c.end_date)} UTC · ${t('Ghi nhận lúc')}: ${new Intl.DateTimeFormat(numberLocale(),{timeZone:$('cal-zone').value,dateStyle:'medium',timeStyle:'short'}).format(new Date(c.issued_at))}`:t('Chưa ghi nhận case đủ điều kiện');
  const canShow=!outdated&&c?.probabilities&&Date.now()<Date.parse(c.end_date)+86400000&&e.state==='validated_holdout';
  for(const k of ['down','flat','up'])$(`prob-${k}`).textContent=canShow?`${(Number(c.probabilities[k])*100).toLocaleString(numberLocale(),{maximumFractionDigits:1})}%`:'—';
  $('prob-note').textContent=t(canShow?'Xác suất của mô hình ECO cho case đã ghi nhận; khả năng dự báo có thể thay đổi.':'Chưa có xác suất đủ kiểm định. Dấu — không phải 0% hoặc 50%; mô hình đang ghi nhận dữ liệu để học.');
  $('prob-validation').textContent=e.test?`Brier: ${e.test.brier} · baseline: ${e.baseline.brier} · log loss: ${e.test.log_loss} · CI95 Δ Brier: [${e.brier_delta_ci95.join(', ')}] · ${e.failures.join(', ')||t('Đạt cổng nội bộ')}`:t('Chưa có kết quả ngoài mẫu; không chuyển nhãn có điều kiện thành phần trăm.');
  $('prob-download').href=pointer.url;$('prob-manifest').href=pointer.manifest.url;
  $('prob-version').textContent=`${d.schema_version} · ${d.release_id}`;
}
export async function refreshProbability(currentCalendar=null){
  calendarId=currentCalendar;if(busy)return;busy=true;
  try{good=await loadProbability();warning=null;}catch(e){warning=e.message;}
  finally{busy=false;renderProbability();}
}
