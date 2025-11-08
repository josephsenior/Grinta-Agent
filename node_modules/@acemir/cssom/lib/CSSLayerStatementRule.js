//.CommonJS
var CSSOM = {
  CSSRule: require("./CSSRule").CSSRule,
};
///CommonJS

/**
 * @constructor
 * @see https://drafts.csswg.org/css-cascade-5/#csslayerstatementrule
 */
CSSOM.CSSLayerStatementRule = function CSSLayerStatementRule() {
  CSSOM.CSSRule.call(this);
  this.nameList = [];
};

CSSOM.CSSLayerStatementRule.prototype = new CSSOM.CSSRule();
CSSOM.CSSLayerStatementRule.prototype.constructor = CSSOM.CSSLayerStatementRule;
CSSOM.CSSLayerStatementRule.prototype.type = 0;

Object.defineProperties(CSSOM.CSSLayerStatementRule.prototype, {
  cssText: {
    get: function () {
      return "@layer " + this.nameList.join(", ") + ";";
    },
    configurable: true,
    enumerable: true,
  },
});

//.CommonJS
exports.CSSLayerStatementRule = CSSOM.CSSLayerStatementRule;
///CommonJS
