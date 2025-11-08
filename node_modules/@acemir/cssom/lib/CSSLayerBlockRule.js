//.CommonJS
var CSSOM = {
  CSSRule: require("./CSSRule").CSSRule,
  CSSGroupingRule: require("./CSSGroupingRule").CSSGroupingRule,
};
///CommonJS

/**
 * @constructor
 * @see https://drafts.csswg.org/css-cascade-5/#csslayerblockrule
 */
CSSOM.CSSLayerBlockRule = function CSSLayerBlockRule() {
  CSSOM.CSSGroupingRule.call(this);
  this.name = "";
  this.cssRules = [];
};

CSSOM.CSSLayerBlockRule.prototype = new CSSOM.CSSGroupingRule();
CSSOM.CSSLayerBlockRule.prototype.constructor = CSSOM.CSSLayerBlockRule;
CSSOM.CSSLayerBlockRule.prototype.type = 18;

Object.defineProperties(CSSOM.CSSLayerBlockRule.prototype, {
  cssText: {
    get: function () {
      var cssTexts = [];
      for (var i = 0, length = this.cssRules.length; i < length; i++) {
        cssTexts.push(this.cssRules[i].cssText);
      }
      return "@layer " + this.name + (this.name && " ") + "{" + (cssTexts.length ? "\n  " + cssTexts.join("\n  ") : "") + "\n}";
    },
    configurable: true,
    enumerable: true,
  },
});

//.CommonJS
exports.CSSLayerBlockRule = CSSOM.CSSLayerBlockRule;
///CommonJS
