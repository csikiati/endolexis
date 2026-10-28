// stage 16: richer lives. What happens privately to each Olvasó, and what the visitor says about them.
// plain: as in stages 8-15. One kind of private event (a jolt with a random colour), four visitor words.
// rich: four kinds of private event, each with its own colour, and eight visitor words about four sides of how a body looks.
const { OL, bodyLook } = require('./engine.js');
const KINDS = [
  { name: 'jolt', hue: 8, rate: 0.004, f: (h) => { h[0] = Math.min(1, h[0] + 0.2); h[1] = Math.max(0, h[1] - 0.25); } },
  { name: 'warmth', hue: 48, rate: 0.002, f: (h) => { h[2] = Math.min(1, h[2] + 0.3); h[1] = Math.min(1, h[1] + 0.15); } },
  { name: 'drain', hue: 228, rate: 0.002, f: (h) => { h[0] = Math.max(0, h[0] - 0.25); h[1] = Math.max(0, h[1] - 0.1); } },
  { name: 'flash', hue: 290, rate: 0.002, f: (h) => { h[3] = Math.min(1, h[3] + 0.5); h[0] = Math.min(1, h[0] + 0.1); } },
];
function setup(rich, hear = 3, feel = 6) { OL.NWORDS = rich ? 8 : 4; OL.HEAR = hear; OL.FEEL = feel; OL.NX = 18 + hear - 3; OL.NY = feel + 2; } // stage 17: the reader's width
// a private event: only the one it happens to sees its colour; returns the kind or null
function privateEvent(e, R, rich) {
  if (!rich) { if (R.next() < 0.004) { const h = Math.floor(R.next() * 6); for (let k = 0; k < 3; k++) e.addColour(OL.HUES[h], 'you'); KINDS[0].f(e.h); return 'jolt'; } return null; }
  for (const K of KINDS) if (R.next() < K.rate) { for (let k = 0; k < 3; k++) e.addColour(K.hue, 'you'); K.f(e.h); return K.name; }
  return null;
}
// rich words are chosen so their sounds stay apart: with three numbers per sound, 'busy' and 'near' would sound almost the same
// the visitor names how one of them looks, compared with how it usually looks
function visitorWord(L, A, R, rich) {
  if (!rich) { if (L[3] > 0.45) return 'busy'; if (L[1] > A[1] + 0.12) return 'restless'; if (L[1] < A[1] - 0.06) return 'calm'; if (L[3] < 0.15) return 'still'; return null; }
  const side = Math.floor(R.next() * 4);
  if (side === 0) return L[1] > A[1] + 0.12 ? 'uneasy' : L[1] < A[1] - 0.06 ? 'easy' : null;
  if (side === 1) return L[3] > 0.45 ? 'doing' : L[3] < 0.15 ? 'lazy' : null;
  if (side === 2) return L[0] > A[0] + 0.08 ? 'large' : L[0] < A[0] - 0.08 ? 'weak' : null;
  return L[2] > A[2] + 0.08 ? 'close' : L[2] < A[2] - 0.08 ? 'apart' : null;
}
module.exports = { KINDS, setup, privateEvent, visitorWord, bodyLook };
