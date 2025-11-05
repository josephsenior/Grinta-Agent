const Module = require('module');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if (String(request).includes('@vitest/expect') || String(request).includes('vitest')) {
    console.error('TRACE-REQUIRE: loading', request);
    try {
      console.error(new Error().stack);
    } catch (e) {}
  }
  return origLoad.apply(this, arguments);
};
console.error('trace-requires preloaded');
