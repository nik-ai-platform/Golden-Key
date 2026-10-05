export function styleAtBreakpoint(element: Element, minWidth: number, property: string): string {
  let value = "";
  for (const sheet of Array.from(document.styleSheets)) {
    for (const rule of Array.from(sheet.cssRules)) {
      const rules = rule instanceof CSSMediaRule && rule.conditionText === `(min-width:${minWidth}px)`
        ? Array.from(rule.cssRules)
        : [];
      for (const child of rules) {
        if (child instanceof CSSStyleRule && !child.selectorText.includes("::") &&
            child.style.getPropertyValue(property) && element.matches(child.selectorText)) {
          value = child.style.getPropertyValue(property) || value;
        }
      }
    }
  }
  return value;
}
