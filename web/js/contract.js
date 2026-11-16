/* Contract clause reader: a line-by-line port of rule_extract() in layer3_engines/engines/c4_compliance.py.
   tools/test_web.mjs checks that it returns the same answers as the Python version on all 11 demo contracts.
   The contracts are synthetic, so this is a demo of the reader. Nothing here feeds a score. */
(function (root) {
  'use strict';
  function section(text, heading) {
    const re = new RegExp('\\b\\d+\\.\\s*' + heading + '\\b([\\s\\S]*?)(?=\\s\\d+\\.\\s+[A-Z][A-Z ,&]{3,}\\s+\\d+\\.\\d|$)');
    const m = re.exec(text);
    return m ? m[1] : '';
  }
  function leadTimeRisk(days) {
    if (days === null) return 1;
    return Math.max(0, Math.min(1, (days - 30) / 60));
  }
  function readContract(rawText) {
    const text = String(rawText || '').split(/\s+/).filter(Boolean).join(' ');
    const fm = section(text, 'FORCE MAJEURE');
    let fmCat, fmRisk;
    if (/FORESEEABLE|do NOT constitute Force Majeure/.test(fm)) { fmCat = 'hormuz_disruption_excluded'; fmRisk = 0; }
    else if (/Supplier considers|without limit|no obligation to re-route/i.test(fm)) { fmCat = 'supplier_discretion_unlimited'; fmRisk = 1; }
    else if (/maximum of \d+ days/i.test(fm)) { fmCat = 'balanced_capped'; fmRisk = 0.5; }
    else if (!fm.trim()) { fmCat = 'missing'; fmRisk = 1; }
    else { fmCat = 'unclassified'; fmRisk = 0.5; }

    const lt = /within (\d+) calendar days/i.exec(text);
    const days = lt ? parseInt(lt[1], 10) : null;

    const late = section(text, 'LATE DELIVERY');
    let penCat, penRisk;
    if (/not be liable for any penalty|estimates only/i.test(late) || !late.trim()) { penCat = 'none'; penRisk = 1; }
    else if (/per week of delay/i.test(late)) { penCat = 'weekly_ld_with_substitute_right'; penRisk = 0; }
    else { penCat = 'ld_after_delay_threshold_low_cap'; penRisk = 0.5; }

    const ex = section(text, 'EXCLUSIVITY');
    const pct = /not less than (\d+)%/.exec(ex);
    const blocks = /shall not qualify an alternative source|sole-source commitment/i.test(ex);
    const ssRisk = (pct || blocks) ? 1 : 0;

    const risks = [fmRisk, leadTimeRisk(days), penRisk, ssRisk];
    return {
      force_majeure: { category: fmCat, risk: fmRisk },
      lead_time: { days: days, risk: leadTimeRisk(days) },
      late_delivery_penalty: { category: penCat, risk: penRisk },
      single_source: { exclusive_share_pct: pct ? parseInt(pct[1], 10) : null, blocks_second_source: blocks, risk: ssRisk },
      contract_risk: Math.round(10000 * risks.reduce(function (a, b) { return a + b; }, 0) / 4) / 10000
    };
  }
  const PLAIN = {
    hormuz_disruption_excluded: 'A Hormuz or airspace disruption does NOT excuse the supplier; it must re-route at its own cost',
    balanced_capped: 'Balanced: obligations pause only while the event lasts, at most 60 days',
    supplier_discretion_unlimited: 'The supplier decides what counts, may suspend without limit and need not re-route',
    missing: 'No force majeure clause found', unclassified: 'Clause found but not recognised',
    weekly_ld_with_substitute_right: 'Damages for every week of delay, and the buyer may buy elsewhere at the supplier\'s cost',
    ld_after_delay_threshold_low_cap: 'Damages only after a long delay, with a low cap',
    none: 'No penalty for late delivery'
  };
  root.PSContract = { read: readContract, plain: function (k) { return PLAIN[k] || k; } };
})(typeof window !== 'undefined' ? window : globalThis);
