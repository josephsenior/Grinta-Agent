//.CommonJS
var CSSOM = {
	CSSRule: require("./CSSRule").CSSRule
};
///CommonJS


/**
 * @constructor
 * @see https://drafts.csswg.org/css-counter-styles/#the-csscounterstylerule-interface
 */
CSSOM.CSSCounterStyleRule = function CSSCounterStyleRule() {
	CSSOM.CSSRule.call(this);
    this.name = "";
};

CSSOM.CSSCounterStyleRule.prototype = new CSSOM.CSSRule();
CSSOM.CSSCounterStyleRule.prototype.constructor = CSSOM.CSSCounterStyleRule;
CSSOM.CSSCounterStyleRule.prototype.type = 11;

//.CommonJS
exports.CSSCounterStyleRule = CSSOM.CSSCounterStyleRule;
///CommonJS
