const CTA_WORDS =
  /order|book|reserve|contact|call|get in touch|enquir|inquir|get started|buy/i;

/**
 * Guarantees every call-to-action button/link actually goes somewhere.
 * Models reliably write real headline copy but are inconsistent about
 * wiring href="#" placeholders through to the real contact/order page —
 * this repairs it deterministically instead of hoping the prompt was
 * followed on every one of N pages.
 */
export function fixCtas(html: string, orderPageHref: string): string {
  let out = html
    .replace(/href="#"/g, `href="${orderPageHref}"`)
    .replace(/href='#'/g, `href='${orderPageHref}'`)
    .replace(/href=""/g, `href="${orderPageHref}"`);

  out = out.replace(
    /<a([^>]*?)href=["']#[^"']*["']([^>]*)>([\s\S]*?)<\/a>/gi,
    (match, before: string, after: string, inner: string) => {
      const text = inner.replace(/<[^>]+>/g, "");
      if (CTA_WORDS.test(text)) {
        return `<a${before}href="${orderPageHref}"${after}>${inner}</a>`;
      }
      return match;
    }
  );

  out = out.replace(
    /<button([^>]*)>([\s\S]*?)<\/button>/gi,
    (match, attrs: string, inner: string) => {
      const plain = inner.replace(/<[^>]+>/g, "");
      const attrsLower = attrs.toLowerCase();
      const alreadyWired =
        attrsLower.includes("onclick") ||
        attrsLower.includes('type="submit"') ||
        attrsLower.includes("type='submit'");
      if (CTA_WORDS.test(plain) && !alreadyWired) {
        return `<button${attrs} onclick="window.location.href='${orderPageHref}'">${inner}</button>`;
      }
      return match;
    }
  );

  return out;
}

/**
 * If the same image src appears more than once on a page (a model
 * shortcut when it runs low on ideas), keep the first use and swap later
 * repeats for a styled gradient panel — matches the "never repeat an
 * image on one page" rule already stated in the design system prompt, as
 * a deterministic backstop rather than hoping it's followed.
 */
export function fixDuplicateImages(html: string): string {
  const seen = new Map<string, number>();
  return html.replace(/<img[^>]*>/gi, (tag) => {
    const match = tag.match(/src=["']([^"']+)["']/i);
    if (!match) return tag;
    const src = match[1];
    const count = (seen.get(src) ?? 0) + 1;
    seen.set(src, count);
    if (count > 1) {
      return '<div aria-hidden="true" style="width:100%;min-height:220px;border-radius:1rem;background:linear-gradient(135deg, rgba(0,0,0,.08), rgba(0,0,0,.22));"></div>';
    }
    return tag;
  });
}

/**
 * Removes breadcrumb bars and any second header <nav> — the injected shared
 * nav is meant to be the ONLY navigation, but models sometimes add a
 * breadcrumb strip or a duplicate mini-nav on inner pages anyway. Keeps the
 * first <nav> (the real header) and any nav living inside the footer.
 */
export function stripBreadcrumbs(html: string): string {
  let out = html.replace(
    /<(nav|div|ol|ul)\b[^>]*(?:breadcrumb|aria-label=["']breadcrumb)[^>]*>[\s\S]*?<\/\1>/gi,
    ""
  );

  const navs = [...out.matchAll(/<nav\b[\s\S]*?<\/nav>/gi)];
  if (navs.length > 1) {
    const footerMatch = out.match(/<footer\b[\s\S]*?<\/footer>/i);
    const footerStart = footerMatch?.index ?? -1;
    const footerEnd = footerMatch ? footerStart + footerMatch[0].length : -1;
    // Walk backwards so earlier match indices stay valid while slicing.
    for (let i = navs.length - 1; i >= 1; i--) {
      const start = navs[i].index ?? -1;
      if (start === -1) continue;
      const insideFooter = footerStart !== -1 && start >= footerStart && start <= footerEnd;
      if (insideFooter) continue;
      out = out.slice(0, start) + out.slice(start + navs[i][0].length);
    }
  }
  return out;
}

/** If AOS's JS never loads (CDN blocked, offline preview) every [data-aos]
 * element stays at opacity 0 and the page looks empty. This reveals anything
 * still hidden 1.5s after load, so scroll animations degrade to "visible"
 * instead of "blank page". */
const AOS_FAILSAFE =
  "<script>window.addEventListener('load',function(){setTimeout(function(){" +
  "document.querySelectorAll('[data-aos]').forEach(function(el){" +
  "var cs=getComputedStyle(el);if(cs.opacity==='0'||cs.visibility==='hidden'){" +
  "el.style.opacity='1';el.style.transform='none';el.style.visibility='visible';}});},1500);});</script>";

export function injectAosFailsafe(html: string): string {
  if (html.includes("</body>")) {
    // replace() without /g swaps only the first occurrence, matching the
    // original tool's count=1 behavior.
    return html.replace("</body>", `${AOS_FAILSAFE}\n</body>`);
  }
  return html + AOS_FAILSAFE;
}

/** Injects a favicon link (used with the client's logo pulled from their
 * profile upload). No-op if the page already declares one. */
export function injectFavicon(html: string, href: string): string {
  if (/rel=["']icon["']/i.test(html)) return html;
  const link = `<link rel="icon" href="${href}">`;
  if (/<\/head>/i.test(html)) {
    return html.replace(/<\/head>/i, `${link}\n</head>`);
  }
  return `${link}\n${html}`;
}
