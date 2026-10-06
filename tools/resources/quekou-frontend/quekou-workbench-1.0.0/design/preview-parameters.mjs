// Review-only utilities. All design values and allowed ranges come from tokens.json.
export function flattenColors(colors) {
  const out={};
  for(const [group,roles] of Object.entries(colors)) {
    if(group==='status') {for(const [kind,pair] of Object.entries(roles)) for(const [role,value] of Object.entries(pair)) out[`status-${kind}${role==='fg'?'':'-'+role}`]=value;}
    else for(const [role,value] of Object.entries(roles)) out[`${group}-${role}`]=value;
  }
  return out;
}
export function hslRgb(h,s,l) {
  s/=100;l/=100;
  const a=s*Math.min(l,1-l);
  const f=n=>{const k=(n+h/30)%12;return l-a*Math.max(-1,Math.min(k-3,9-k,1));};
  return [f(0),f(8),f(4)];
}
export function luminance(rgb) {return rgb.map(v=>v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[0.2126,0.7152,0.0722][i],0);}
export function contrast(a,b) {const x=luminance(a),y=luminance(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);}
function resolveColor(value,common) {
  const ref=value.match(/^var\(--([\w-]+)\)$/);if(ref)return resolveColor(common[ref[1]],common);
  const hsl=value.match(/^hsl\(([\d.]+) ([\d.]+)% ([\d.]+)%\)$/);if(hsl)return hslRgb(...hsl.slice(1).map(Number));
  const mix=value.match(/^color-mix\(in srgb, (var\(--[\w-]+\)) ([\d.]+)%, (var\(--[\w-]+\))\)$/);
  if(mix){const a=resolveColor(mix[1],common),b=resolveColor(mix[3],common),weight=Number(mix[2])/100;return a.map((v,i)=>v*weight+b[i]*(1-weight));}
  throw new Error(`Unsupported contrast reference: ${value}`);
}
export function accentVariants(tokens) {
  const p=tokens.parameterPolicy.accentHue;
  const darkBackgrounds=Object.values(tokens.systems).map(s=>resolveColor(s.colors.dark.surface.hover,tokens.common));
  const variants={brand:{'client-blue':'var(--brand-blue)','client-light-blue':'var(--brand-light-blue)','client-action-text':'var(--brand-action-text)'}};
  for(let h=p.minimum;h<=p.maximum;h+=p.step) {
    let l=p.brandLightness;
    while(contrast(hslRgb(h,p.brandSaturation,l),[1,1,1])<p.minimumButtonContrast)l-=p.lightnessAdjustmentStep;
    let light=p.lightLightness;
    while(darkBackgrounds.some(bg=>contrast(hslRgb(h,p.lightSaturation,light),bg)<p.minimumLightTextContrast))light+=p.lightnessAdjustmentStep;
    variants[h]={'client-blue':`hsl(${h} ${p.brandSaturation}% ${l.toFixed(4)}%)`,'client-light-blue':`hsl(${h} ${p.lightSaturation}% ${light.toFixed(4)}%)`,'client-action-text':`color-mix(in srgb, var(--client-blue) ${(1-p.textInkMix)*100}%, var(--brand-ink))`};
  }
  return variants;
}
