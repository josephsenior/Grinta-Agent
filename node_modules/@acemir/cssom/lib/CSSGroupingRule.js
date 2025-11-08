//.CommonJS
var CSSOM = {
	CSSRule: require("./CSSRule").CSSRule,
	parse: require('./parse').parse
};
var errorUtils = require("./errorUtils").errorUtils;
///CommonJS


/**
 * @constructor
 * @see https://drafts.csswg.org/cssom/#the-cssgroupingrule-interface
 */
CSSOM.CSSGroupingRule = function CSSGroupingRule() {
	CSSOM.CSSRule.call(this);
	this.cssRules = [];
};

CSSOM.CSSGroupingRule.prototype = new CSSOM.CSSRule();
CSSOM.CSSGroupingRule.prototype.constructor = CSSOM.CSSGroupingRule;


/**
 * Used to insert a new CSS rule to a list of CSS rules.
 *
 * @example
 *   cssGroupingRule.cssText
 *   -> "body{margin:0;}"
 *   cssGroupingRule.insertRule("img{border:none;}", 1)
 *   -> 1
 *   cssGroupingRule.cssText
 *   -> "body{margin:0;}img{border:none;}"
 *
 * @param {string} rule
 * @param {number} [index]
 * @see https://www.w3.org/TR/cssom-1/#dom-cssgroupingrule-insertrule
 * @return {number} The index within the grouping rule's collection of the newly inserted rule.
 */
 CSSOM.CSSGroupingRule.prototype.insertRule = function insertRule(rule, index) {
	if (rule === undefined && index === undefined) {
		errorUtils.throwMissingArguments(this, 'insertRule', this.constructor.name);
	}
	if (index === void 0) {
		index = 0;
	}
	index = Number(index);
	if (index < 0) {
		index = 4294967296 + index;
	}
	if (index > this.cssRules.length) {
		errorUtils.throwIndexError(this, 'insertRule', this.constructor.name, index, this.cssRules.length);
	}
	
	var ruleToParse = String(rule);
	var parsedSheet = CSSOM.parse(ruleToParse);
	if (parsedSheet.cssRules.length !== 1) {
		errorUtils.throwParseError(this, 'insertRule', this.constructor.name, ruleToParse, 'SyntaxError');
	}
	var cssRule = parsedSheet.cssRules[0];
	
	// Check for rules that cannot be inserted inside a CSSGroupingRule
	if (cssRule.constructor.name === 'CSSImportRule' || cssRule.constructor.name === 'CSSNamespaceRule') {
		var ruleKeyword = cssRule.constructor.name === 'CSSImportRule' ? '@import' : '@namespace';
		errorUtils.throwError(this, 'DOMException', 
			"Failed to execute 'insertRule' on '" + this.constructor.name + "': " +
			"'" + ruleKeyword + "' rules cannot be inserted inside a group rule.",
			'HierarchyRequestError');
	}
	
	// Check for CSSLayerStatementRule (@layer statement rules)
	if (cssRule.constructor.name === 'CSSLayerStatementRule') {
		errorUtils.throwParseError(this, 'insertRule', this.constructor.name, ruleToParse, 'SyntaxError');
	}
	
	cssRule.__parentRule = this;
	this.cssRules.splice(index, 0, cssRule);
	return index;
};

/**
 * Used to delete a rule from the grouping rule.
 *
 *   cssGroupingRule.cssText
 *   -> "img{border:none;}body{margin:0;}"
 *   cssGroupingRule.deleteRule(0)
 *   cssGroupingRule.cssText
 *   -> "body{margin:0;}"
 *
 * @param {number} index within the grouping rule's rule list of the rule to remove.
 * @see https://www.w3.org/TR/cssom-1/#dom-cssgroupingrule-deleterule
 */
 CSSOM.CSSGroupingRule.prototype.deleteRule = function deleteRule(index) {
	if (index === undefined) {
		errorUtils.throwMissingArguments(this, 'deleteRule', this.constructor.name);
	}
	index = Number(index);
	if (index < 0) {
		index = 4294967296 + index;
	}
	if (index >= this.cssRules.length) {
		errorUtils.throwIndexError(this, 'deleteRule', this.constructor.name, index, this.cssRules.length);
	}
	this.cssRules.splice(index, 1)[0].__parentRule = null;
};

//.CommonJS
exports.CSSGroupingRule = CSSOM.CSSGroupingRule;
///CommonJS
