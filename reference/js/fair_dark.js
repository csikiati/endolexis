// NewNeural - the fair darkness test (run with: node fair_dark.js; needs newneural_sim.js beside it)
// World: as world2 (mountain), plus three channels for SEEING ITS OWN BODY (thin when hungry, dry when thirsty, hurt),
// which fade in the dark like all vision; inner senses blurrier (noise 0.3), so the outside matters for self-reading.
// Learner: separate move and voice choices, sharper; the wish to understand itself = error of its own forecast of
// how it will feel 5 steps later (an inside yardstick). Exploration: 14 creatures per setup; confirmation: 30 fresh ones.
const S = require("./newneural_sim.js");
const base = { innerNoise: 0.3, seeSelf: true, strong: true, steps: 20000 };
const SETUPS = { hears: { hearsSelf: true, kappa: 0.15 }, comfort: { hearsSelf: true, kappa: 0 }, deaf: { hearsSelf: false, kappa: 0.15 },
  hears_strong: { hearsSelf: true, kappa: 0.5 }, deaf_strong: { hearsSelf: false, kappa: 0.5 } };
(async () => {
  const out = { explore: {}, confirm: {} };
  for (const [phase, seeds, names] of [["explore", [1, 14], Object.keys(SETUPS)], ["confirm", [101, 130], ["hears_strong", "deaf_strong"]]]) {
    for (const nm of names) {
      const R = [];
      for (let s = seeds[0]; s <= seeds[1]; s++) {
        const r = await S.liveVoice({ n: 1, seed: s, ...base, ...SETUPS[nm] }); const L = r.logs[0]; const st = S.voiceStats(L, base.steps);
        const cl = {}; for (let t = base.steps / 2; t < base.steps; t++) { const lt = L.light[t] < 0.3 ? "dark" : L.light[t] > 0.7 ? "bright" : null; if (!lt) continue; const k = lt + "/" + (L.voiced[t] ? "voice" : "quiet"); (cl[k] = cl[k] || []).push(L.clar[t]); }
        const C = {}; for (const k in cl) C[k] = S.mean(cl[k]);
        R.push({ seed: s, dark: st.dark, bright: st.bright, byHour: st.byHour, err: st.err, clar: C });
      }
      out[phase][nm] = R; console.log(phase, nm, "done");
    }
  }
  require("fs").writeFileSync("results/fair_dark.json", JSON.stringify(out));
})();
