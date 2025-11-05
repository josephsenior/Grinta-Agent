// Trace defineProperty calls for the vitest matchers symbol
const origDefine = Object.defineProperty;
Object.defineProperty = function (obj, prop, descriptor) {
  try {
    const isTarget = (typeof prop === 'symbol' && Symbol.keyFor(prop) === '$$jest-matchers-object') || String(prop).includes('$$jest-matchers-object');
    if (isTarget) {
      try {
        console.error('TRACE-DEFINE: defineProperty called for', String(prop));
        console.error(new Error().stack);
      } catch (e) {
        // ignore
      }
    }
  } catch (e) {
    // ignore
  }
  return origDefine.call(this, obj, prop, descriptor);
};

// Also trace Object.defineProperties (batch)
const origDefineProps = Object.defineProperties;
Object.defineProperties = function (obj, props) {
  try {
    for (const key of Object.keys(props)) {
      if (String(key).includes('$$jest-matchers-object') || (typeof key === 'symbol' && Symbol.keyFor(key) === '$$jest-matchers-object')) {
        console.error('TRACE-DEFINE: defineProperties contains', String(key));
        console.error(new Error().stack);
      }
    }
  } catch (e) {}
  return origDefineProps.call(this, obj, props);
};

console.error('trace-define preloaded');
