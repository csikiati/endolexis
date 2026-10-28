// stage 10: caring. With a longer view of what its acts lead to, does it learn to reach toward a trembling one?
const { run, mean } = require('./test9.js');
const conds = JSON.parse(process.argv[2]); const out = {};
for (const [name, o] of conds) { const R = []; for (let seed = +(process.env.S0 || 1); seed <= +(process.env.S1 || 6); seed++) R.push(run({ N: 2, T: 40000, seed, reach: true, contagion: 0.05, ...o }));
  const share = (r, top) => top ? r.reachTopThird / r.anyActTop : r.reachBottomThird / r.anyActBottom;
  out[name] = { reachShareTrembling: mean(R.map(r => share(r, true))), reachShareSteady: mean(R.map(r => share(r, false))), lean: mean(R.map(r => share(r, true) - share(r, false))), selfLean: mean(R.map(r => r.selfReachShareTrembling - r.selfReachShareSteady)), selfLeanRuns: R.filter(r => r.selfReachShareTrembling > r.selfReachShareSteady).length + '/' + R.length, leanRuns: R.filter(r => share(r, true) > share(r, false)).length + '/' + R.length, actTop: mean(R.map(r => r.anyActTop)), actBottom: mean(R.map(r => r.anyActBottom)), distress: mean(R.map(r => r.distress)), seenTremble: mean(R.map(r => r.seenTrembleMean)) };
  console.log(name.padEnd(26), JSON.stringify(out[name], (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v)); require('fs').writeFileSync(process.argv[3], JSON.stringify(out)); }
