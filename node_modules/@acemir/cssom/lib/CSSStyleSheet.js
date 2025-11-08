//.CommonJS
var CSSOM = {
	StyleSheet: require("./StyleSheet").StyleSheet,
	CSSStyleRule: require("./CSSStyleRule").CSSStyleRule
};
var errorUtils = require("./errorUtils").errorUtils;
///CommonJS


/**
 * @constructor
 * @see http://www.w3.org/TR/DOM-Level-2-Style/css.html#CSS-CSSStyleSheet
 */
CSSOM.CSSStyleSheet = function CSSStyleSheet() {
	CSSOM.StyleSheet.call(this);
	this.cssRules = [];
};


CSSOM.CSSStyleSheet.prototype = new CSSOM.StyleSheet();
CSSOM.CSSStyleSheet.prototype.constructor = CSSOM.CSSStyleSheet;


/**
 * Used to insert a new rule into the style sheet. The new rule now becomes part of the cascade.
 *
 *   sheet = new Sheet("body {margin: 0}")
 *   sheet.toString()
 *   -> "body{margin:0;}"
 *   sheet.insertRule("img {border: none}", 0)
 *   -> 0
 *   sheet.toString()
 *   -> "img{border:none;}body{margin:0;}"
 *
 * @param {string} rule
 * @param {number} [index=0]
 * @see http://www.w3.org/TR/DOM-Level-2-Style/css.html#CSS-CSSStyleSheet-insertRule
 * @return {number} The index within the style sheet's rule collection of the newly inserted rule.
 */
CSSOM.CSSStyleSheet.prototype.insertRule = function(rule, index) {
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
	
	// Helper function to find the last index of a specific rule constructor
	function findLastIndexOfConstructor(rules, constructorName) {
		for (var i = rules.length - 1; i >= 0; i--) {
			if (rules[i].constructor.name === constructorName) {
				return i;
			}
		}
		return -1;
	}
	
	// Helper function to find the first index of a rule that's NOT of specified constructors
	function findFirstNonConstructorIndex(rules, constructorNames) {
		for (var i = 0; i < rules.length; i++) {
			if (constructorNames.indexOf(rules[i].constructor.name) === -1) {
				return i;
			}
		}
		return rules.length;
	}
	
	// Validate rule ordering based on CSS specification
	if (cssRule.constructor.name === 'CSSImportRule') {
		// @import rules cannot be inserted after @layer rules that already exist
		// They can only be inserted at the beginning or after other @import rules
		var firstLayerIndex = findFirstNonConstructorIndex(this.cssRules, ['CSSImportRule']);
		if (firstLayerIndex < this.cssRules.length && this.cssRules[firstLayerIndex].constructor.name === 'CSSLayerStatementRule' && index > firstLayerIndex) {
			errorUtils.throwError(this, 'DOMException',
				"Failed to execute 'insertRule' on '" + this.constructor.name + "': Failed to insert the rule.",
				'HierarchyRequestError');
		}
		
		// Also cannot insert after @namespace or other rules
		var firstNonImportIndex = findFirstNonConstructorIndex(this.cssRules, ['CSSImportRule']);
		if (index > firstNonImportIndex && firstNonImportIndex < this.cssRules.length && 
		    this.cssRules[firstNonImportIndex].constructor.name !== 'CSSLayerStatementRule') {
			errorUtils.throwError(this, 'DOMException',
				"Failed to execute 'insertRule' on '" + this.constructor.name + "': Failed to insert the rule.",
				'HierarchyRequestError');
		}
	} else if (cssRule.constructor.name === 'CSSNamespaceRule') {
		// @namespace rules can come after @layer and @import, but before any other rules
		// They cannot come before @import rules
		var firstImportIndex = -1;
		for (var i = 0; i < this.cssRules.length; i++) {
			if (this.cssRules[i].constructor.name === 'CSSImportRule') {
				firstImportIndex = i;
				break;
			}
		}
		var firstNonImportNamespaceIndex = findFirstNonConstructorIndex(this.cssRules, [
			'CSSLayerStatementRule', 
			'CSSImportRule', 
			'CSSNamespaceRule'
		]);
		
		// Cannot insert before @import rules
		if (firstImportIndex !== -1 && index <= firstImportIndex) {
			errorUtils.throwError(this, 'DOMException',
				"Failed to execute 'insertRule' on '" + this.constructor.name + "': Failed to insert the rule.",
				'HierarchyRequestError');
		}
		
		// Cannot insert after other types of rules
		if (index > firstNonImportNamespaceIndex) {
			errorUtils.throwError(this, 'DOMException',
				"Failed to execute 'insertRule' on '" + this.constructor.name + "': Failed to insert the rule.",
				'HierarchyRequestError');
		}
	} else if (cssRule.constructor.name === 'CSSLayerStatementRule') {
		// @layer statement rules can be inserted anywhere before @import and @namespace
		// No additional restrictions beyond what's already handled
	} else {
		// Any other rule cannot be inserted before @import and @namespace
		var firstNonSpecialRuleIndex = findFirstNonConstructorIndex(this.cssRules, [
			'CSSLayerStatementRule',
			'CSSImportRule',
			'CSSNamespaceRule'
		]);
		
		if (index < firstNonSpecialRuleIndex) {
			errorUtils.throwError(this, 'DOMException',
				"Failed to execute 'insertRule' on '" + this.constructor.name + "': Failed to insert the rule.",
				'HierarchyRequestError');
		}
	}
	
	cssRule.__parentStyleSheet = this;
	this.cssRules.splice(index, 0, cssRule);
	return index;
};


/**
 * Used to delete a rule from the style sheet.
 *
 *   sheet = new Sheet("img{border:none} body{margin:0}")
 *   sheet.toString()
 *   -> "img{border:none;}body{margin:0;}"
 *   sheet.deleteRule(0)
 *   sheet.toString()
 *   -> "body{margin:0;}"
 *
 * @param {number} index within the style sheet's rule list of the rule to remove.
 * @see http://www.w3.org/TR/DOM-Level-2-Style/css.html#CSS-CSSStyleSheet-deleteRule
 */
CSSOM.CSSStyleSheet.prototype.deleteRule = function(index) {
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
	if (this.cssRules[index] && this.cssRules[index].constructor.name == "CSSNamespaceRule") {
		var shouldContinue = this.cssRules.every(function (rule) {
			return ['CSSImportRule','CSSLayerStatementRule','CSSNamespaceRule'].indexOf(rule.constructor.name) !== -1
		});
		if (!shouldContinue) {
			errorUtils.throwError(this, 'DOMException', "Failed to execute 'deleteRule' on '" + this.constructor.name + "': Failed to delete rule.", "InvalidStateError");
		}
	}
	this.cssRules.splice(index, 1);
};


/**
 * NON-STANDARD
 * @return {string} serialize stylesheet
 */
CSSOM.CSSStyleSheet.prototype.toString = function() {
	var result = "";
	var rules = this.cssRules;
	for (var i=0; i<rules.length; i++) {
		result += rules[i].cssText + "\n";
	}
	return result;
};


//.CommonJS
exports.CSSStyleSheet = CSSOM.CSSStyleSheet;
CSSOM.parse = require('./parse').parse; // Cannot be included sooner due to the mutual dependency between parse.js and CSSStyleSheet.js
///CommonJS
