//.CommonJS
var CSSOM = {
	CSSRule: require("./CSSRule").CSSRule,
	CSSStyleSheet: require("./CSSStyleSheet").CSSStyleSheet
};
///CommonJS


/**
 * @constructor
 * @see https://drafts.csswg.org/cssom/#the-cssnamespacerule-interface
 */
CSSOM.CSSNamespaceRule = function CSSNamespaceRule() {
	CSSOM.CSSRule.call(this);
	this.prefix = "";
	this.namespaceURI = "";
	this.styleSheet = new CSSOM.CSSStyleSheet();
};

CSSOM.CSSNamespaceRule.prototype = new CSSOM.CSSRule();
CSSOM.CSSNamespaceRule.prototype.constructor = CSSOM.CSSNamespaceRule;
CSSOM.CSSNamespaceRule.prototype.type = 10;

Object.defineProperty(CSSOM.CSSNamespaceRule.prototype, "cssText", {
  get: function() {
    return "@namespace" + (this.prefix && " " + this.prefix) + " url(\"" + this.namespaceURI + "\");";
  },
  set: function(cssText) {
    // Reset prefix and namespaceURI
    this.prefix = "";
    this.namespaceURI = "";

    // Remove @namespace and trim
    var text = cssText.trim();
    if (text.indexOf('@namespace') === 0) {
      text = text.slice('@namespace'.length).trim();
    }

    // Remove trailing semicolon if present
    if (text.charAt(text.length - 1) === ';') {
      text = text.slice(0, -1).trim();
    }

    // Regex to match valid namespace syntax:
    // 1. [optional prefix] url("...") or [optional prefix] url('...') or [optional prefix] url() or [optional prefix] url(unquoted)
    // 2. [optional prefix] "..." or [optional prefix] '...'
    // The prefix must be a valid CSS identifier (letters, digits, hyphens, underscores, starting with letter or underscore)
    var re = /^(?:([a-zA-Z_][a-zA-Z0-9_-]*)\s+)?(?:url\(\s*(?:(['"])(.*?)\2\s*|([^)]*?))\s*\)|(['"])(.*?)\5)$/;
    var match = text.match(re);

    if (match) {
      // If prefix is present
      if (match[1]) {
        this.prefix = match[1];
      }
      // If url(...) form with quotes
      if (typeof match[3] !== "undefined") {
        this.namespaceURI = match[3];
      }
      // If url(...) form without quotes
      else if (typeof match[4] !== "undefined") {
        this.namespaceURI = match[4].trim();
      }
      // If quoted string form
      else if (typeof match[6] !== "undefined") {
        this.namespaceURI = match[6];
      }
    } else {
      throw new DOMException("Invalid @namespace rule", "InvalidStateError");
    }
  }
});


//.CommonJS
exports.CSSNamespaceRule = CSSOM.CSSNamespaceRule;
///CommonJS
