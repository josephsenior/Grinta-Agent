const hexToRgb = (h) => {
  h = h.replace("#", "");
  if (h.length === 3) {
    h = h
      .split("")
      .map((c) => c + c)
      .join("");
  }
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
};
const lum = (hex) => {
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255);
  const conv = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const R = conv(r);
  const G = conv(g);
  const B = conv(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
};
const contrast = (a, b) => {
  const L1 = lum(a);
  const L2 = lum(b);
  const bright = Math.max(L1, L2);
  const dim = Math.min(L1, L2);
  return (bright + 0.05) / (dim + 0.05);
};

const tokens = {
  "tertiary-light": "#99A0B6",
  "tertiary-light-oi": "#B7BDC2",
  "tertiary-light-alt": "#9CA3AF",
  basic: "#B1B9D3",
  // updated to improve contrast on dark backgrounds (matches tailwind.config.js)
  tertiary: "#878DA1",
  content: "#F7F8FB",
};
const backgrounds = {
  base: "#0D0D0F",
  "base-secondary": "#222328",
  "grey-985": "#0D0D0F",
};

console.log("Contrast ratios (fg on bg):\n");
for (const [name, fg] of Object.entries(tokens)) {
  for (const [bname, bg] of Object.entries(backgrounds)) {
    console.log(
      `${name} (${fg}) on ${bname} (${bg}) => ${contrast(fg, bg).toFixed(2)}`,
    );
  }
}

console.log("\nSuggested minimums: 4.5:1 for normal text, 3:1 for large text.");

// Quick helper to propose a darker hex by reducing lightness in HSL
const rgbToHex = (r, g, b) =>
  `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
const proposeDarker = (hex, steps = 4) => {
  const [r, g, b] = hexToRgb(hex);
  // convert to HSL
  const R = r / 255;
  const G = g / 255;
  const B = b / 255;
  const max = Math.max(R, G, B);
  const min = Math.min(R, G, B);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case R:
        h = (G - B) / d + (G < B ? 6 : 0);
        break;
      case G:
        h = (B - R) / d + 2;
        break;
      case B:
        h = (R - G) / d + 4;
        break;
    }
    h /= 6;
  } // h,s,l in [0,1]
  // darken by reducing l
  const candidates = [];
  for (let i = 1; i <= steps; i++) {
    const newL = Math.max(0, l - i * 0.06); // reduce 6% per step
    // hsl to rgb
    const hue2rgb = (p, q, t) => {
      if (t < 0) {
        t += 1;
      }
      if (t > 1) {
        t -= 1;
      }
      if (t < 1 / 6) {
        return p + (q - p) * 6 * t;
      }
      if (t < 1 / 2) {
        return q;
      }
      if (t < 2 / 3) {
        return p + (q - p) * (2 / 3 - t) * 6;
      }
      return p;
    };
    let rr;
    let gg;
    let bb;
    if (s === 0) {
      rr = gg = bb = newL;
    } else {
      const q = newL < 0.5 ? newL * (1 + s) : newL + s - newL * s;
      const p = 2 * newL - q;
      rr = hue2rgb(p, q, h + 1 / 3);
      gg = hue2rgb(p, q, h);
      bb = hue2rgb(p, q, h - 1 / 3);
    }
    candidates.push(
      rgbToHex(
        Math.round(rr * 255),
        Math.round(gg * 255),
        Math.round(bb * 255),
      ),
    );
  }
  return candidates;
};

console.log("\nProposed darker candidates for tokens:");
for (const [name, hex] of Object.entries(tokens)) {
  console.log(name, "->", proposeDarker(hex).join(", "));
}
